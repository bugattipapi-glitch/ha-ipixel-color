"""Safe watched-team feed polling and Home Assistant event emission."""
from __future__ import annotations

import json
import time
from typing import Any

from aiohttp import ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .media import async_validate_remote_url
from .sports_state import SportsScoreTracker

EVENT_TEAM_PREGAME = "ipixel_team_pregame"
EVENT_TEAM_SCORE = "ipixel_team_score"
MAX_FEED_BYTES = 128 * 1024
TRACKER_KEY = "_ipixel_sports_score_tracker"
ALLOWED_KEYS = {"texas", "arizona", "packers"}


def _validate_game(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or raw.get("key") not in ALLOWED_KEYS:
        return None
    required_strings = (
        "eventId", "startsAt", "team", "abbreviation", "opponent",
        "opponentAbbreviation", "homeAway", "state", "detail",
    )
    if any(not isinstance(raw.get(field), str) for field in required_strings):
        return None
    try:
        score = max(0, int(raw.get("score", 0)))
        opponent_score = max(0, int(raw.get("opponentScore", 0)))
    except (TypeError, ValueError):
        return None
    return {
        "key": raw["key"],
        "eventId": raw["eventId"][:64],
        "startsAt": raw["startsAt"][:40],
        "team": raw["team"][:12],
        "abbreviation": raw["abbreviation"][:8],
        "opponent": raw["opponent"][:48],
        "opponentAbbreviation": raw["opponentAbbreviation"][:12],
        "homeAway": raw["homeAway"] if raw["homeAway"] in {"home", "away"} else "home",
        "score": score,
        "opponentScore": opponent_score,
        "state": raw["state"] if raw["state"] in {"pre", "in", "post"} else "pre",
        "detail": raw["detail"][:80],
        "live": bool(raw.get("live")),
        "completed": bool(raw.get("completed")),
    }


async def async_fetch_team_games(hass: HomeAssistant, url: str) -> list[dict[str, Any]]:
    """Download and validate the small sanitized watched-team JSON feed."""
    await async_validate_remote_url(hass, url)
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            url,
            allow_redirects=False,
            timeout=ClientTimeout(total=10),
            headers={"Accept": "application/json"},
        ) as response:
            if 300 <= response.status < 400:
                raise HomeAssistantError("Redirecting sports-feed URLs are not allowed")
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if content_type != "application/json":
                raise HomeAssistantError("The sports feed must return JSON")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_FEED_BYTES:
                raise HomeAssistantError("The sports feed is too large")
            body = await response.content.read(MAX_FEED_BYTES + 1)
            if len(body) > MAX_FEED_BYTES:
                raise HomeAssistantError("The sports feed is too large")
    except HomeAssistantError:
        raise
    except Exception as err:
        raise HomeAssistantError("The watched-team sports feed is unavailable") from err

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise HomeAssistantError("The sports feed returned invalid JSON") from err
    raw_games = payload.get("games", []) if isinstance(payload, dict) else []
    if not isinstance(raw_games, list) or len(raw_games) > 3:
        raise HomeAssistantError("The sports feed has an invalid games list")
    return [game for raw in raw_games if (game := _validate_game(raw)) is not None]


async def async_poll_team_feed(hass: HomeAssistant, url: str, mode: str) -> None:
    """Poll the watched-team feed and emit only internal, sanitized events."""
    games = await async_fetch_team_games(hass, url)
    if mode == "pregame":
        pregame = [game for game in games if game["state"] == "pre"]
        if pregame:
            hass.bus.async_fire(EVENT_TEAM_PREGAME, {"games": pregame})
        return

    tracker = hass.data.setdefault(TRACKER_KEY, SportsScoreTracker())
    for event in tracker.update(games, time.monotonic()):
        hass.bus.async_fire(EVENT_TEAM_SCORE, event)
