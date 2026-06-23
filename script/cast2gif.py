#!/usr/bin/env python3
"""Convert an asciicast (v2) file to an animated GIF.

Tries ``agg`` first (https://github.com/asciinema/agg, best quality).
If ``agg`` is not on PATH, falls back to a pure-Python renderer that needs::

    pip install pyte Pillow

Usage::

    python cast2gif.py demo.cast demo.gif
    python cast2gif.py --fps 20 --speed 2.0 demo.cast demo.gif
    python cast2gif.py --max-duration 30 demo.cast demo.gif
    python cast2gif.py --no-agg demo.cast demo.gif   # force Python renderer
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Tuple


# ---------------------------------------------------------------------------
# Colour tables
# ---------------------------------------------------------------------------

_FG_DEFAULT: Tuple[int, int, int] = (204, 204, 204)
_BG_DEFAULT: Tuple[int, int, int] = (30, 30, 30)

_NAMED: dict = {
    "black":          (  0,   0,   0),
    "red":            (205,  49,  49),
    "green":          ( 13, 188, 121),
    "yellow":         (229, 229,  16),
    "blue":           ( 36, 114, 200),
    "magenta":        (188,  63, 188),
    "cyan":           ( 17, 168, 205),
    "white":          (229, 229, 229),
    "bright_black":   (102, 102, 102),
    "bright_red":     (241,  76,  76),
    "bright_green":   ( 35, 209, 139),
    "bright_yellow":  (245, 245,  67),
    "bright_blue":    ( 59, 142, 234),
    "bright_magenta": (214, 112, 214),
    "bright_cyan":    ( 41, 184, 219),
    "bright_white":   (229, 229, 229),
}


def _build_256_table() -> List[Tuple[int, int, int]]:
    # Indices 0-15: standard + high-intensity (xterm defaults)
    table: List[Tuple[int, int, int]] = [
        (  0,   0,   0), (128,   0,   0), (  0, 128,   0), (128, 128,   0),
        (  0,   0, 128), (128,   0, 128), (  0, 128, 128), (192, 192, 192),
        (128, 128, 128), (255,   0,   0), (  0, 255,   0), (255, 255,   0),
        (  0,   0, 255), (255,   0, 255), (  0, 255, 255), (255, 255, 255),
    ]

    def _c(v: int) -> int:
        return 0 if v == 0 else 55 + v * 40

    # Indices 16-231: 6×6×6 colour cube
    for r in range(6):
        for g in range(6):
            for b in range(6):
                table.append((_c(r), _c(g), _c(b)))

    # Indices 232-255: grayscale ramp
    for i in range(24):
        v = 8 + i * 10
        table.append((v, v, v))

    return table


_TABLE_256 = _build_256_table()


def _resolve_color(color: Any, is_fg: bool) -> Tuple[int, int, int]:
    """Convert a pyte colour value to an (R, G, B) tuple."""
    default = _FG_DEFAULT if is_fg else _BG_DEFAULT

    # pyte true-colour: already an (r, g, b) tuple/list
    if isinstance(color, (tuple, list)) and len(color) == 3:
        return int(color[0]), int(color[1]), int(color[2])

    # pyte 256-colour: integer index
    if isinstance(color, int):
        return _TABLE_256[color] if 0 <= color < 256 else default

    s = str(color)
    if s == "default":
        return default
    if s in _NAMED:
        return _NAMED[s]

    # 256-colour index stored as a decimal string
    try:
        idx = int(s)
        return _TABLE_256[idx] if 0 <= idx < 256 else default
    except ValueError:
        pass

    # True colour stored as a 6-hex-char string (no leading #)
    if len(s) == 6:
        try:
            return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        except ValueError:
            pass

    return default


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

def _find_font(size: int) -> Tuple[Any, int, int]:
    """Return (font, cell_width, cell_height) using the best available font."""
    from PIL import ImageFont  # type: ignore[import]

    candidates = [
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        # macOS
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Courier New.ttf",
    ]

    for path in candidates:
        try:
            font = ImageFont.truetype(path, size)
            try:
                bbox = font.getbbox("W")
                cw, ch = bbox[2] - bbox[0], bbox[3] - bbox[1] + 2
            except AttributeError:
                cw, ch = font.getsize("W")  # type: ignore[attr-defined]
                ch += 2
            return font, cw, ch
        except (OSError, IOError):
            pass

    # Pillow built-in bitmap font (6×11 px per glyph)
    return ImageFont.load_default(), 6, 12


# ---------------------------------------------------------------------------
# Screen renderer
# ---------------------------------------------------------------------------

def _render_screen(screen: Any, font: Any, cell_w: int, cell_h: int,
                   padding: int = 6) -> Any:
    """Render a pyte Screen to a PIL RGB Image."""
    from PIL import Image, ImageDraw  # type: ignore[import]

    img_w = screen.columns * cell_w + 2 * padding
    img_h = screen.lines * cell_h + 2 * padding
    img = Image.new("RGB", (img_w, img_h), _BG_DEFAULT)
    draw = ImageDraw.Draw(img)

    for row_idx in range(screen.lines):
        row = screen.buffer[row_idx]
        for col_idx in range(screen.columns):
            cell = row[col_idx]
            char: str = cell.data

            fg = _resolve_color(cell.fg, True)
            bg = _resolve_color(cell.bg, False)
            if cell.reverse:
                fg, bg = bg, fg

            x = padding + col_idx * cell_w
            y = padding + row_idx * cell_h

            if bg != _BG_DEFAULT:
                draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], fill=bg)

            if char and char != " ":
                draw.text((x, y), char, fill=fg, font=font)

    return img


# ---------------------------------------------------------------------------
# Python renderer
# ---------------------------------------------------------------------------

def _python_render(cast_path: str, gif_path: str, fps: float, speed: float,
                   max_dur: float, font_size: int) -> None:
    try:
        import pyte  # type: ignore[import]
    except ImportError:
        sys.exit("error: pyte not found — install with:  pip install pyte Pillow\n"
                 "Or install agg: https://github.com/asciinema/agg")

    try:
        from PIL import Image  # type: ignore[import]
    except ImportError:
        sys.exit("error: Pillow not found — install with:  pip install pyte Pillow")

    with open(cast_path, encoding="utf-8") as f:
        header = json.loads(f.readline())
        events = [json.loads(ln) for ln in f if ln.strip()]

    cols: int = int(header.get("width", 80))
    rows: int = int(header.get("height", 24))

    output_events = [(float(t), str(d)) for t, typ, d in events if typ == "o"]
    if not output_events:
        sys.exit("error: no output events found in cast file")

    total = output_events[-1][0] / speed
    if max_dur > 0:
        total = min(total, max_dur)

    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)
    font, cell_w, cell_h = _find_font(font_size)
    frame_ms = max(int(1000 / fps), 20)

    frames: List[Any] = []
    event_idx = 0
    frame_time = 0.0

    while frame_time <= total + 1e-9:
        # Feed all events whose scaled timestamp falls within this frame
        while event_idx < len(output_events):
            t, data = output_events[event_idx]
            if t / speed <= frame_time + 1e-9:
                stream.feed(data)
                event_idx += 1
            else:
                break
        frames.append(_render_screen(screen, font, cell_w, cell_h))
        frame_time += 1.0 / fps

    if not frames:
        sys.exit("error: no frames were generated")

    print(f"Rendering {len(frames)} frames at {fps:.0f} fps …", flush=True)

    # Quantize to a shared palette derived from the first frame for GIF compatibility
    first_p = frames[0].convert("P", palette=Image.ADAPTIVE, colors=255)
    p_frames = [frames[0].quantize(palette=first_p)]
    for frame in frames[1:]:
        p_frames.append(frame.quantize(palette=first_p))

    p_frames[0].save(
        gif_path,
        format="GIF",
        save_all=True,
        append_images=p_frames[1:],
        duration=frame_ms,
        loop=0,
        optimize=False,
    )

    size_kb = Path(gif_path).stat().st_size // 1024
    print(f"Saved {gif_path}  ({len(frames)} frames, {total:.1f}s, {size_kb} KB)")


# ---------------------------------------------------------------------------
# agg wrapper (preferred when available)
# ---------------------------------------------------------------------------

def _try_agg(cast_path: str, gif_path: str, speed: float, theme: str) -> bool:
    """Run agg and return True if it succeeded, False if agg is not installed."""
    agg = shutil.which("agg")
    if not agg:
        return False
    cmd = [agg, "--speed", str(speed)]
    if theme:
        cmd += ["--theme", theme]
    cmd += [cast_path, gif_path]
    subprocess.run(cmd, check=True)  # nosec
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse arguments and run the converter."""
    parser = argparse.ArgumentParser(
        description="Convert an asciicast (.cast) file to an animated GIF.",
        epilog=(
            "Renderer priority:\n"
            "  1. agg  (https://github.com/asciinema/agg, best quality)\n"
            "  2. Python fallback — requires:  pip install pyte Pillow\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Input asciicast file (.cast)")
    parser.add_argument("output", help="Output GIF file (.gif)")
    parser.add_argument(
        "--fps", type=float, default=15.0, metavar="N",
        help="Frames per second for the Python renderer (default: 15)",
    )
    parser.add_argument(
        "--speed", type=float, default=1.0, metavar="X",
        help="Playback speed multiplier (default: 1.0)",
    )
    parser.add_argument(
        "--max-duration", type=float, default=0.0, metavar="SECONDS",
        help="Trim output to at most SECONDS (0 = no limit, default: 0)",
    )
    parser.add_argument(
        "--theme", default="", metavar="NAME",
        help="Colour theme passed to agg (e.g. monokai, solarized-dark)",
    )
    parser.add_argument(
        "--font-size", type=int, default=14, metavar="PX",
        help="Font size in pixels for the Python renderer (default: 14)",
    )
    parser.add_argument(
        "--no-agg", action="store_true",
        help="Skip agg even if available and use the Python renderer",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        sys.exit(f"error: file not found: {args.input}")

    if not args.no_agg and _try_agg(args.input, args.output, args.speed, args.theme):
        size_kb = Path(args.output).stat().st_size // 1024
        print(f"Saved {args.output}  (via agg, {size_kb} KB)")
        return

    _python_render(
        args.input,
        args.output,
        args.fps,
        args.speed,
        args.max_duration,
        args.font_size,
    )


if __name__ == "__main__":
    main()
