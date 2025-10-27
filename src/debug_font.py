#!/usr/bin/env python3
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.ttLib.tables.ttProgram import Program

# ---------- CONFIG ----------
INPUT_FONT = "input-variable.ttf"
OUTPUT_FONT = "output-debug.ttf"
INSET_RATIO = 0.01  # Inset as a ratio of glyph bounds (0.01 = 1% inset)
# ----------------------------


def calculate_rectangle_coords(xMin, yMin, xMax, yMax):
    """Calculate rectangle coordinates with inset.
    
    Returns:
        List of (x, y) tuples for the 4 corners
    """
    width = xMax - xMin
    height = yMax - yMin
    
    inset_x = width * INSET_RATIO
    inset_y = height * INSET_RATIO
    
    x0 = xMin + inset_x
    y0 = yMin + inset_y
    x1 = xMax - inset_x
    y1 = yMax - inset_y
    
    # Return coords in order: bottom-left, bottom-right, top-right, top-left
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def create_square_glyph(glyph_set, xMin, yMin, xMax, yMax):
    """Create a simple square outline that fits the original glyph bounds.
    
    Args:
        glyph_set: The font's glyph set
        xMin, yMin, xMax, yMax: Bounding box of the original glyph
    """
    pen = TTGlyphPen(glyph_set)
    
    coords = calculate_rectangle_coords(xMin, yMin, xMax, yMax)
    
    # Draw a rectangle matching the original glyph's proportions
    pen.moveTo(coords[0])
    pen.lineTo(coords[1])
    pen.lineTo(coords[2])
    pen.lineTo(coords[3])
    pen.closePath()
    
    return pen.glyph()


def main():
    """Replace all glyph outlines with squares while preserving metrics and OpenType features."""
    font = TTFont(INPUT_FONT)
    
    # Check font type
    if "glyf" not in font:
        raise ValueError(
            "This script only supports TrueType fonts (glyf table). "
            "CFF/CFF2 fonts are not supported."
        )
    
    glyf_table = font["glyf"]
    hmtx_table = font["hmtx"]
    glyph_set = font.getGlyphSet()

    # Get variation data if it exists
    gvar_table = font.get("gvar")
    fvar_table = font.get("fvar")
    axes = fvar_table.axes if fvar_table else []
    
    # Track replacements
    replaced_count = 0
    skipped_count = 0
    total_glyphs = len(font.getGlyphOrder())
    
    # No variation pre-calculation needed - rectangles will be static across all axes

    # Replace all glyphs with rectangles matching their bounds
    for glyphName in font.getGlyphOrder():
        
        # Skip space and .notdef characters (but replace everything else)
        if glyphName in ('space', 'uni0020', 'u0020', 'nbsp', 'uni00A0', 'u00A0', '.notdef'):
            skipped_count += 1
            continue

        # Get original glyph
        original_glyph = glyf_table[glyphName]
        
        # Store original metrics
        width, lsb = hmtx_table[glyphName]

        # Get glyph bounds
        if hasattr(original_glyph, 'xMin'):
            xMin, yMin, xMax, yMax = (
                original_glyph.xMin,
                original_glyph.yMin,
                original_glyph.xMax,
                original_glyph.yMax
            )
        else:
            # Empty glyph (like spaces or combining marks) - create a small default rectangle
            # Use a small rectangle based on the glyph's advance width
            xMin = lsb if lsb > 0 else 50
            yMin = 0
            xMax = xMin + min(width - lsb if width > lsb else width, 100) if width > 0 else xMin + 100
            yMax = 200  # Default height
        
        # Create a rectangle matching this glyph's bounds
        square_glyph = create_square_glyph(glyph_set, xMin, yMin, xMax, yMax)

        # Create a new glyph by copying the square's structure
        new_glyph = Glyph()
        new_glyph.numberOfContours = square_glyph.numberOfContours
        
        # Copy the square outline data (simple glyph)
        new_glyph.coordinates = square_glyph.coordinates.copy()
        new_glyph.endPtsOfContours = square_glyph.endPtsOfContours[:]
        new_glyph.flags = square_glyph.flags[:]
        
        # No hinting instructions for debug glyphs
        # (hinting is geometry-specific and would cause issues)
        new_glyph.program = Program()  # Empty program (no hinting)
        
        # Replace the glyph
        glyf_table[glyphName] = new_glyph

        # Restore original width/lsb so metrics are unchanged
        hmtx_table[glyphName] = (width, lsb)

        # Remove glyph variation data - rectangles will be static across all axes
        # (variation deltas are point-count specific and would cause skewing)
        if gvar_table and glyphName in gvar_table.variations:
            del gvar_table.variations[glyphName]
        
        replaced_count += 1
    
    # Save the debug font (fontTools will recalculate bounds automatically)
    font.save(OUTPUT_FONT)
    
    # Print summary
    print(f"✅ Debug font created: {OUTPUT_FONT}")
    print(f"\n📊 Summary:")
    print(f"  • Total glyphs: {total_glyphs}")
    print(f"  • Replaced with rectangles: {replaced_count}")
    print(f"  • Skipped (spaces only): {skipped_count}")
    print(f"  • Rectangle sizing: Matches original glyph bounds with {int(INSET_RATIO*100)}% inset")
    print(f"  • Original metrics preserved: ✓")
    print(f"  • Hinting: Stripped for consistency")
    
    # Check for variable font
    if "fvar" in font:
        axes = font["fvar"].axes
        print(f"  • Variable font axes preserved: {len(axes)}")
        for axis in axes:
            print(f"    - {axis.axisTag}: {axis.minValue}-{axis.maxValue}")
        if gvar_table:
            print(f"  • Glyph variations: Removed (rectangles stay same size across all axes)")
    else:
        print(f"  • Font type: Static")


if __name__ == "__main__":
    main()
