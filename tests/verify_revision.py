from __future__ import annotations

import importlib.util
from io import BytesIO
from pathlib import Path
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
TICKER_PATH = ROOT / "custom_components" / "ipixel_color" / "ticker.py"
SPEC = importlib.util.spec_from_file_location("ipixel_ticker", TICKER_PATH)
assert SPEC is not None and SPEC.loader is not None
TICKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TICKER)


class RevisionTests(unittest.TestCase):
    def test_large_ticker_preserves_fixed_header(self) -> None:
        payload = TICKER.render_ticker_gif(
            "FLIGHTS",
            "TUS TO PHX | ALT 12.3K FT",
        )
        image = Image.open(BytesIO(payload))
        frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]

        self.assertEqual((32, 32), image.size)
        self.assertGreater(len(frames), 1)
        self.assertLessEqual(len(frames), 32)

        fixed_header = frames[0].crop((0, 0, 32, 11)).tobytes()
        for frame in frames[1:]:
            self.assertEqual(fixed_header, frame.crop((0, 0, 32, 11)).tobytes())

        self.assertEqual(8, TICKER.HEADER_FONT_SIZE)
        self.assertEqual(14, TICKER.TICKER_FONT_SIZE)

    def test_only_cat_tail_pixels_move(self) -> None:
        with Image.open(ROOT / "assets" / "cat-nap-32.gif") as image:
            size = image.size
            frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]

        self.assertEqual((32, 32), size)
        self.assertEqual(3, len(frames))

        tail_mask = Image.new("L", size, 0)
        ImageDraw.Draw(tail_mask).polygon(
            ((0, 15), (3, 14), (7, 15), (10, 19), (8, 24), (5, 27), (1, 26), (0, 23)),
            fill=255,
        )
        outside_tail = Image.eval(tail_mask, lambda pixel: 255 - pixel).convert("RGB")

        wag = ImageChops.difference(frames[0], frames[1])
        returned = ImageChops.difference(frames[0], frames[2])
        self.assertIsNotNone(wag.getbbox())
        self.assertIsNone(returned.getbbox())
        self.assertIsNone(ImageChops.multiply(wag, outside_tail).getbbox())


if __name__ == "__main__":
    unittest.main()
