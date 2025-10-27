# Debug Font

A utility to replace all glyph outlines in a TrueType font with simple rectangles matching each glyph's original bounds, while preserving metrics and OpenType features.

## Purpose

Useful for debugging font rendering, layout issues, or testing typography systems without the visual complexity of actual glyphs. Each character becomes a simple rectangle that shows its bounding box, making it easy to visualize spacing, alignment, and metrics issues.

![demo](.github/demo.png?raw=true)

## Features

- ✅ Replaces all glyphs with rectangles matching their original bounds
- ✅ Preserves all glyph metrics (width, left/right sidebearings)
- ✅ Preserves OpenType features (GSUB, GPOS, ligatures, kerning)
- ✅ Preserves variable font axes (rectangles remain static across axes)
- ✅ Replaces all punctuation and symbols (only spaces are skipped)
- ✅ Configurable inset ratio for rectangle sizing
- ✅ Strips hinting for consistency
- ✅ Maintains font validity for rendering

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management.

```bash
# Install dependencies
uv sync
```

## Usage

```bash
# Run with uv (recommended)
uv run python src/debug_font.py
```

### Configuration

Edit the constants at the top of `src/debug_font.py`:

```python
INPUT_FONT = "input-variable.ttf"  # Path to source font
OUTPUT_FONT = "output-debug.ttf"   # Path for output
INSET_RATIO = 0.1                  # Rectangle inset (0.1 = 10% inset from bounds)
```

## Demo

Open `demo.html` in a browser to see an interactive comparison:

The demo shows:
- Side-by-side comparison of original vs debug font
- Variable font axis controls (weight and width sliders)
- Overlay test to prove both fonts occupy identical space
- Live metrics display
- Various text samples including punctuation and symbols

## Requirements

- Python ≥3.9
- fonttools ≥4.60.1

## How It Works

For each glyph in the font:
1. Gets the original glyph's bounding box (xMin, yMin, xMax, yMax)
2. Creates a simple rectangle outline matching those bounds with a 10% inset
3. Replaces the glyph outline with the rectangle
4. Preserves the original glyph's horizontal metrics (width, sidebearings)
5. Removes glyph variation data (rectangles stay static across variable font axes)
6. Keeps all OpenType feature tables intact (GSUB, GPOS, etc.)

The result is a font where every character displays as a rectangle showing its bounding box, but maintains proper spacing, kerning, and variable font axes.

## Notes

- **TrueType only**: This tool only works with TrueType fonts (glyf table). CFF/CFF2 fonts are not supported.
- **Static rectangles**: In variable fonts, rectangles remain the same size across all axis positions to avoid visual distortion.
- **Space characters**: Actual space glyphs are preserved (not replaced with rectangles).
- **Empty glyphs**: Glyphs without outlines (like some punctuation) get a small default rectangle.