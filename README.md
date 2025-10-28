# Debug Font

A utility to replace all glyph outlines in a TrueType font with simple rectangles matching each glyph's original bounds, while preserving metrics and OpenType features.

## Purpose

Useful for debugging font rendering, layout issues, or testing typography systems without the visual complexity of actual glyphs. Each character becomes a simple rectangle that shows its bounding box, making it easy to visualize spacing, alignment, and metrics issues.

![demo](.github/demo.png?raw=true)

## Features

- ✅ Replaces all glyphs with rectangle outlines
- ✅ Preserves advance widths, side bearings, and kerning
- ✅ Preserves OpenType features (GSUB ligatures, GPOS)
- ✅ Preserves variable font axes (fvar + avar)
- ✅ Rectangle width scales with wght axis (60% → 80% → 95%)
- ✅ Controlled gvar deltas for smooth width variation
- ✅ Strips hinting instructions
- ✅ Skips .notdef and space glyphs only

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management.

```bash
# Install dependencies
uv sync
```

## Usage

```bash
# Process font with default output name
uv run python src/debug_font.py input.ttf

# Specify custom output name
uv run python src/debug_font.py input.ttf -o custom-output.ttf

# Show help
uv run python src/debug_font.py --help
```

Default output: `{input_basename}-DEBUG.ttf`

## Demo

Open `demo.html` in a browser for interactive comparison:

- Side-by-side font comparison with live axis controls
- No-layout-shift test with visual alignment guides
- Overlay mode: see debug rectangles overlaid on original text
- Variable font controls (wght, wdth, font-size)
- Live metrics display

Remember to update the font file imports in `demo.html` if you use non-default names.

## Requirements

- Python ≥3.9
- fonttools ≥4.60.1

## How It Works

For each glyph:
1. Calculate rectangle height from original glyph bounds or 70% of typo metrics
2. Create 4-point clockwise rectangle at 80% of advance width (default)
3. Replace glyph outline, preserve advance width and side bearings
4. Build new gvar deltas for width scaling:
   - Min wght: 60% width
   - Default: 80% width
   - Max wght: 95% width
5. Clear hinting instructions
6. Keep all OpenType tables intact (GSUB, GPOS, kern, fvar, avar)

Result: Rectangles show glyph metrics with proper spacing, kerning, and smooth variable width scaling.
