"""Safe remote-media loading for iPIXEL displays."""
from __future__ import annotations

import ipaddress
import socket
import time
from io import BytesIO
from urllib.parse import urlsplit

from aiohttp import ClientTimeout
from PIL import Image

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024
MAX_FRAMES = 32
MAX_TOTAL_PIXELS = 16_000_000
MAX_LOOP_DURATION_MS = 20_000
CACHE_SECONDS = 60 * 60
ALLOWED_CONTENT_TYPES = {
    "image/gif": ".gif",
    "image/png": ".png",
}
BLOCKED_HOST_SUFFIXES = (".local", ".lan", ".internal", ".home", ".arpa")
CACHE_KEY = "_media_download_cache"


def _validate_ip(address: str) -> None:
    """Reject loopback, private, link-local, reserved, and unspecified IPs."""
    parsed = ipaddress.ip_address(address)
    if not parsed.is_global:
        raise HomeAssistantError("The media URL must resolve to a public internet address")


async def _validate_remote_url(hass: HomeAssistant, url: str) -> None:
    """Allow HTTPS public-internet URLs only."""
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise HomeAssistantError("The iPIXEL media URL must use HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise HomeAssistantError("The iPIXEL media URL is invalid")

    host = parsed.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise HomeAssistantError("Local and private hostnames are not allowed")

    try:
        _validate_ip(host)
        return
    except ValueError:
        pass

    def _resolve() -> set[str]:
        return {
            item[4][0]
            for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }

    try:
        addresses = await hass.async_add_executor_job(_resolve)
    except OSError as err:
        raise HomeAssistantError("The iPIXEL media hostname could not be resolved") from err

    if not addresses:
        raise HomeAssistantError("The iPIXEL media hostname did not resolve")
    for address in addresses:
        _validate_ip(address)


def _validate_image(data: bytes, expected_extension: str) -> None:
    """Apply conservative size, frame-count, and duration limits."""
    try:
        with Image.open(BytesIO(data)) as image:
            actual_extension = ".gif" if image.format == "GIF" else ".png" if image.format == "PNG" else None
            if actual_extension != expected_extension:
                raise HomeAssistantError("The downloaded file does not match its declared image type")

            frame_count = getattr(image, "n_frames", 1)
            if frame_count < 1 or frame_count > MAX_FRAMES:
                raise HomeAssistantError(f"Animated media must contain 1-{MAX_FRAMES} frames")

            total_pixels = image.width * image.height * frame_count
            if total_pixels > MAX_TOTAL_PIXELS:
                raise HomeAssistantError("The image is too large to process safely")

            duration = 0
            for frame_index in range(frame_count):
                image.seek(frame_index)
                duration += int(image.info.get("duration", 100))
            if duration > MAX_LOOP_DURATION_MS:
                raise HomeAssistantError("The animation loop must be 20 seconds or shorter")
    except HomeAssistantError:
        raise
    except Exception as err:
        raise HomeAssistantError("The downloaded file is not a valid PNG or GIF") from err


async def async_download_media(hass: HomeAssistant, url: str) -> tuple[bytes, str]:
    """Download and validate a small public PNG or GIF with an in-memory cache."""
    cache = hass.data.setdefault(CACHE_KEY, {})
    cached = cache.get(url)
    now = time.monotonic()
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1], cached[2]

    await _validate_remote_url(hass, url)

    session = async_get_clientsession(hass)
    try:
        async with session.get(
            url,
            allow_redirects=False,
            timeout=ClientTimeout(total=10),
            headers={"Accept": "image/gif,image/png"},
        ) as response:
            if 300 <= response.status < 400:
                raise HomeAssistantError("Redirecting media URLs are not allowed")
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            extension = ALLOWED_CONTENT_TYPES.get(content_type)
            if extension is None:
                raise HomeAssistantError("Only GIF and PNG media are supported")

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                raise HomeAssistantError("The media file exceeds the 2 MB limit")

            chunks: list[bytes] = []
            downloaded = 0
            async for chunk in response.content.iter_chunked(64 * 1024):
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_BYTES:
                    raise HomeAssistantError("The media file exceeds the 2 MB limit")
                chunks.append(chunk)
    except HomeAssistantError:
        raise
    except Exception as err:
        raise HomeAssistantError("The iPIXEL media download failed") from err

    data = b"".join(chunks)
    _validate_image(data, extension)
    cache[url] = (now, data, extension)
    return data, extension
