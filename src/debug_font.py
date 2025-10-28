#!/usr/bin/env python3
"""
Debug Font Generator

Replaces all visible glyphs with rectangle outlines while preserving:
- Advance widths and side bearings
- Kerning and GSUB ligatures
- Variable font axes (fvar + avar)
- Controlled gvar deltas for width scaling
"""
import argparse
import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.ttLib.tables.TupleVariation import TupleVariation

# Rectangle width rules (as % of advance width)
# These ratios leave horizontal padding to visualize side bearings
DEFAULT_WIDTH_RATIO = 0.80  # 80% at default weight (10% padding each side)
MIN_WEIGHT_RATIO = 0.60     # 60% at minimum weight (20% padding each side)
MAX_WEIGHT_RATIO = 0.95     # 95% at maximum weight (2.5% padding each side)

# Glyphs to skip
SKIP_GLYPHS = {'.notdef', 'space', 'uni0020', 'nbsp', 'uni00A0'}


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Replace all visible glyphs with rectangle outlines for debugging.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.ttf                     # Output: input-DEBUG.ttf
  %(prog)s font.ttf -o debug.ttf         # Output: debug.ttf
  %(prog)s MyFont.ttf                    # Output: MyFont-DEBUG.ttf
        """
    )
    
    parser.add_argument(
        'input',
        nargs='?',
        default='input.ttf',
        help='Input font file (default: input.ttf)'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output',
        help='Output font file (default: {input_basename}-DEBUG.ttf)'
    )
    
    return parser.parse_args()


def generate_output_filename(input_path):
    """Generate default output filename: {input_basename}-DEBUG.ttf"""
    basename = os.path.splitext(os.path.basename(input_path))[0]
    return f"{basename}-DEBUG.ttf"


def validate_font(font):
    """Validate that the font is a supported TrueType font."""
    if "glyf" not in font:
        raise ValueError(
            "This script only supports TrueType fonts (glyf table). "
            "CFF/CFF2 fonts are not supported."
        )


def calculate_rectangle_height(font, glyph, glyph_name):
    """Calculate rectangle height from glyph bounds or typo metrics.
    
    Args:
        font: TTFont object
        glyph: Glyph object
        glyph_name: Name of the glyph
        
    Returns:
        tuple: (yMin, yMax) for the rectangle
    """
    # Try to use glyph's bounding box height if available
    if hasattr(glyph, 'yMin') and hasattr(glyph, 'yMax'):
        return glyph.yMin, glyph.yMax
    
    # Otherwise use 70% of typographic height
    os2 = font.get('OS/2')
    if os2:
        # Get full typographic height (e.g., ~2048 units for 1000 UPM fonts)
        typo_height = os2.sTypoAscender - os2.sTypoDescender
        
        # Use 70% to avoid overly tall rectangles that would overlap
        # (e.g., 2048 * 0.70 = ~1434 units)
        height = int(typo_height * 0.70)
        
        # Distribute height around baseline with typical text proportions:
        # - 25% below baseline (descenders)
        # - 75% above baseline (x-height + ascenders)
        # Example: if height=700, then yMin=-175, yMax=525
        yMin = int(-height * 0.25)
        yMax = int(height * 0.75)
        return yMin, yMax
    
    # Fallback: 700 units tall, sitting on baseline
    # Used when font has no OS/2 table and glyph has no bounds
    return 0, 700


def create_rectangle_glyph(glyph_set, advance_width, yMin, yMax, lsb):
    """Create a rectangle outline at default weight (80% of advance width).
    
    Args:
        glyph_set: The font's glyph set
        advance_width: The glyph's advance width
        yMin, yMax: Vertical bounds for the rectangle
        lsb: Left side bearing
        
    Returns:
        Glyph object with 4-point clockwise contour
    """
    pen = TTGlyphPen(glyph_set)
    
    # Calculate rectangle width: 80% of advance width at default
    rect_width = int(advance_width * DEFAULT_WIDTH_RATIO)
    
    # Center the rectangle horizontally in the advance width
    x_offset = (advance_width - rect_width) // 2
    
    xMin = x_offset
    xMax = x_offset + rect_width
    
    # Draw clockwise: bottom-left, bottom-right, top-right, top-left
    pen.moveTo((xMin, yMin))
    pen.lineTo((xMax, yMin))
    pen.lineTo((xMax, yMax))
    pen.lineTo((xMin, yMax))
    pen.closePath()
    
    return pen.glyph()


def build_gvar_deltas(font, advance_width, yMin, yMax):
    """Build gvar TupleVariation deltas for rectangle scaling.
    
    Rectangles scale from 60% (min wght) to 95% (max wght) of advance width.
    
    Args:
        font: TTFont object
        advance_width: The glyph's advance width
        yMin, yMax: Vertical bounds (no Y deltas)
        
    Returns:
        list: List of TupleVariation objects for gvar
    """
    fvar = font.get('fvar')
    if not fvar:
        return []
    
    # Find wght axis
    wght_axis = None
    for axis in fvar.axes:
        if axis.axisTag == 'wght':
            wght_axis = axis
            break
    
    if not wght_axis:
        return []
    
    variations = []
    
    # Calculate default rectangle width (80% of advance)
    default_width = int(advance_width * DEFAULT_WIDTH_RATIO)
    x_offset = (advance_width - default_width) // 2
    
    # At minimum weight: 60% width
    min_width = int(advance_width * MIN_WEIGHT_RATIO)
    min_x_offset = (advance_width - min_width) // 2
    
    # Delta from default (80%) to minimum (60%)
    delta_min_left_x = min_x_offset - x_offset
    delta_min_right_x = (min_x_offset + min_width) - (x_offset + default_width)
    
    # 4 contour points + 4 phantom points (for metrics)
    # Phantom points: left side bearing, right side bearing, top, bottom
    coordinates_min = [
        (delta_min_left_x, 0),   # point 0: bottom-left
        (delta_min_right_x, 0),  # point 1: bottom-right
        (delta_min_right_x, 0),  # point 2: top-right
        (delta_min_left_x, 0),   # point 3: top-left
        (0, 0),                  # phantom point: left side bearing
        (0, 0),                  # phantom point: right side bearing
        (0, 0),                  # phantom point: top
        (0, 0),                  # phantom point: bottom
    ]
    
    # Axes use normalized coordinates: -1 (min) to 0 (default) to 1 (max)
    # TupleVariation format: (start, peak, end)
    # (-1.0, -1.0, 0.0) means: active from min to default, peaks at min
    min_variation = TupleVariation(
        axes={'wght': (-1.0, -1.0, 0.0)},
        coordinates=coordinates_min
    )
    variations.append(min_variation)
    
    # At maximum weight: 95% width
    max_width = int(advance_width * MAX_WEIGHT_RATIO)
    max_x_offset = (advance_width - max_width) // 2
    
    # Delta from default (80%) to maximum (95%)
    delta_max_left_x = max_x_offset - x_offset
    delta_max_right_x = (max_x_offset + max_width) - (x_offset + default_width)
    
    coordinates_max = [
        (delta_max_left_x, 0),   # point 0: bottom-left
        (delta_max_right_x, 0),  # point 1: bottom-right
        (delta_max_right_x, 0),  # point 2: top-right
        (delta_max_left_x, 0),   # point 3: top-left
        (0, 0),                  # phantom point: left side bearing
        (0, 0),                  # phantom point: right side bearing
        (0, 0),                  # phantom point: top
        (0, 0),                  # phantom point: bottom
    ]
    
    # (0.0, 1.0, 1.0) means: active from default to max, peaks at max
    max_variation = TupleVariation(
        axes={'wght': (0.0, 1.0, 1.0)},
        coordinates=coordinates_max
    )
    variations.append(max_variation)
    
    return variations


def process_glyph(glyph_name, font, glyf_table, hmtx_table, glyph_set, gvar_table, fvar_table):
    """Process a single glyph: replace with rectangle and build gvar deltas.
    
    Returns:
        bool: True if glyph was replaced, False if skipped
    """
    # Skip specified glyphs
    if glyph_name in SKIP_GLYPHS:
        # Still remove their gvar data if present
        if gvar_table and glyph_name in gvar_table.variations:
            del gvar_table.variations[glyph_name]
        return False

    # Get original glyph
    original_glyph = glyf_table[glyph_name]
    
    # Store original metrics
    advance_width, lsb = hmtx_table[glyph_name]

    # Calculate rectangle height
    yMin, yMax = calculate_rectangle_height(font, original_glyph, glyph_name)
    
    # Create rectangle at default weight (80% of advance width)
    rect_glyph = create_rectangle_glyph(glyph_set, advance_width, yMin, yMax, lsb)

    # Create a new glyph by copying the rectangle's structure
    new_glyph = Glyph()
    new_glyph.numberOfContours = rect_glyph.numberOfContours
    
    # Copy the rectangle outline data (simple glyph with 4 points)
    new_glyph.coordinates = rect_glyph.coordinates.copy()
    new_glyph.endPtsOfContours = rect_glyph.endPtsOfContours[:]
    new_glyph.flags = rect_glyph.flags[:]
    
    # No hinting instructions for debug glyphs
    new_glyph.program = Program()  # Empty program
    
    # Replace the glyph
    glyf_table[glyph_name] = new_glyph

    # Restore original advance width and lsb
    hmtx_table[glyph_name] = (advance_width, lsb)

    # Build gvar deltas for this rectangle
    if gvar_table and fvar_table:
        variations = build_gvar_deltas(font, advance_width, yMin, yMax)
        if variations:
            gvar_table.variations[glyph_name] = variations
    
    return True


def print_summary(output_path, total_glyphs, replaced_count, skipped_count, fvar_table, gvar_table):
    """Print a summary of the font processing."""
    print(f"✅ Debug font created: {output_path}")
    print(f"\n📊 Summary:")
    print(f"  • Total glyphs: {total_glyphs}")
    print(f"  • Replaced with rectangles: {replaced_count}")
    print(f"  • Skipped (.notdef + spaces): {skipped_count}")
    print(f"  • Rectangle width rules:")
    print(f"    - Default weight: {int(DEFAULT_WIDTH_RATIO*100)}% of advance width")
    print(f"    - Minimum weight: {int(MIN_WEIGHT_RATIO*100)}% of advance width")
    print(f"    - Maximum weight: {int(MAX_WEIGHT_RATIO*100)}% of advance width")
    
    # Check for variable font
    if fvar_table:
        axes = fvar_table.axes
        print(f"  • Variable font axes preserved: {len(axes)}")
        for axis in axes:
            print(f"    - {axis.axisTag}: {axis.minValue}-{axis.maxValue} (default: {axis.defaultValue})")
        if gvar_table:
            variation_count = len(gvar_table.variations)
            print(f"  • Glyph variations: {variation_count} glyphs with controlled width deltas")
            print(f"    ✅ Rectangles scale wider/narrower based on wght axis")
    else:
        print(f"  • Font type: Static")


def process_font(input_path, output_path):
    """Main font processing function.
    
    Args:
        input_path: Path to input font file
        output_path: Path to output font file
    """
    # Load font
    font = TTFont(input_path)
    
    # Validate font type
    validate_font(font)
    
    # Get font tables
    glyf_table = font["glyf"]
    hmtx_table = font["hmtx"]
    glyph_set = font.getGlyphSet()
    gvar_table = font.get("gvar")
    fvar_table = font.get("fvar")
    
    # Track replacements
    replaced_count = 0
    skipped_count = 0
    total_glyphs = len(font.getGlyphOrder())
    
    # Clear existing gvar variations - we'll rebuild with our controlled deltas
    if gvar_table:
        gvar_table.variations = {}

    # Process all glyphs
    for glyph_name in font.getGlyphOrder():
        if process_glyph(glyph_name, font, glyf_table, hmtx_table, glyph_set, gvar_table, fvar_table):
            replaced_count += 1
        else:
            skipped_count += 1
    
    # Save the debug font (fontTools will recalculate bounds automatically)
    font.save(output_path)
    
    # Print summary
    print_summary(output_path, total_glyphs, replaced_count, skipped_count, fvar_table, gvar_table)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input font file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    
    # Determine output filename
    output_path = args.output if args.output else generate_output_filename(args.input)
    
    try:
        process_font(args.input, output_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
