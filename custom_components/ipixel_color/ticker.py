"""Small fixed-header ticker renderer for 32x32 iPIXEL displays."""
from __future__ import annotations

from io import BytesIO
from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DISPLAY_SIZE = 32
MAX_FRAMES = 32
FONT_PATH = Path(__file__).parent / "fonts" / "5x5.ttf"


def _rgb(value: str) -> tuple[int, int, int]:
    """Convert a six-character RGB hex value to a tuple."""
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    """Return rendered text width without relying on deprecated Pillow APIs."""
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def render_ticker_gif(
    header: str,
    ticker: str,
    *,
    header_color: str = "50ffa0",
    ticker_color: str = "ffc040",
    background_color: str = "02061e",
    frame_duration: int = 140,
) -> bytes:
    """Render a fixed one-line header and a looping lower-band ticker."""
    header = " ".join(header.upper().split())[:12]
    ticker = " ".join(ticker.upper().split())[:160]
    if not header or not ticker:
        raise ValueError("Ticker header and text must not be empty")

    header_font = ImageFont.truetype(str(FONT_PATH), 8)
    ticker_font = ImageFont.truetype(str(FONT_PATH), 7)
    background = _rgb(background_color)
    header_rgb = _rgb(header_color)
    ticker_rgb = _rgb(ticker_color)

    measuring = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    header_width = _text_width(measuring, header, header_font)
    ticker_width = _text_width(measuring, ticker, ticker_font)
    travel = DISPLAY_SIZE + ticker_width + 8
    frame_count = 1 if ticker_width <= DISPLAY_SIZE - 2 else MAX_FRAMES
    step = 0 if frame_count == 1 else max(1, ceil(travel / (frame_count - 1)))

    frames: list[Image.Image] = []
    for index in range(frame_count):
        frame = Image.new("RGB", (DISPLAY_SIZE, DISPLAY_SIZE), background)
        draw = ImageDraw.Draw(frame)
        draw.text(
            ((DISPLAY_SIZE - header_width) // 2, 0),
            header,
            fill=header_rgb,
            font=header_font,
        )
        draw.line((1, 10, 30, 10), fill=header_rgb)
        ticker_x = (DISPLAY_SIZE - ticker_width) // 2 if frame_count == 1 else DISPLAY_SIZE - index * step
        draw.text((ticker_x, 15), ticker, fill=ticker_rgb, font=ticker_font)
        frames.append(frame)

    palette_source = Image.new("RGB", (DISPLAY_SIZE * len(frames), DISPLAY_SIZE))
    for index, frame in enumerate(frames):
        palette_source.paste(frame, (DISPLAY_SIZE * index, 0))
    palette = palette_source.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]

    output = BytesIO()
    indexed[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=indexed[1:],
        duration=frame_duration,
        loop=0,
        disposal=2,
        optimize=False,
    )
    return output.getvalue()
