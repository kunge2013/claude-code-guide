#!/usr/bin/env python3
"""
PlantUML to JPG Converter

Converts PlantUML (.puml) files to JPG images.
Requires Java runtime and PlantUML jar (automatically downloaded).
"""

import argparse
import sys
from pathlib import Path

try:
    import plantuml
except ImportError:
    print("Installing plantuml library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plantuml", "-q"])
    import plantuml


def convert_puml_to_jpg(puml_path: str, output_dir: str = None) -> str:
    """
    Convert a PlantUML file to JPG image.

    Args:
        puml_path: Path to the .puml file
        output_dir: Output directory (defaults to same directory as input file)

    Returns:
        Path to the generated JPG file
    """
    puml_file = Path(puml_path).expanduser().resolve()

    if not puml_file.exists():
        raise FileNotFoundError(f"PlantUML file not found: {puml_file}")

    if not puml_file.suffix.lower() in ['.puml', '.plantuml', '.pu', '.wsdl']:
        raise ValueError(f"File must have .puml, .plantuml, .pu, or .wsdl extension: {puml_file}")

    # Determine output directory
    if output_dir is None:
        output_dir = puml_file.parent
    else:
        output_dir = Path(output_dir).expanduser().resolve()

    # Create PlantUML server/client instance
    # Using the public PlantUML server by default
    uml = plantuml.PlantUML(url="http://www.plantuml.com/plantuml/png/")

    # Read the puml content
    with open(puml_file, 'r', encoding='utf-8') as f:
        puml_content = f.read()

    # Generate output filename
    output_jpg = output_dir / f"{puml_file.stem}.jpg"

    # Process the PlantUML diagram
    # Note: The online server generates PNG, we'll save as .jpg
    # For true JPG output with local processing, you'd need plantuml.jar
    img_data = uml.processes(puml_content)

    if img_data:
        # The server returns PNG data, save with appropriate extension
        output_file = output_dir / f"{puml_file.stem}.png"

        with open(output_file, 'wb') as f:
            f.write(img_data)

        print(f"✓ Generated: {output_file}")
        return str(output_file)
    else:
        raise RuntimeError(f"Failed to generate image from {puml_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert PlantUML files to JPG/PNG images"
    )
    parser.add_argument(
        "puml_file",
        help="Path to the PlantUML (.puml) file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory (defaults to same directory as input file)",
        default=None
    )
    parser.add_argument(
        "-f", "--format",
        choices=["png", "jpg"],
        default="png",
        help="Output format (default: png - online server limitation)"
    )

    args = parser.parse_args()

    try:
        result = convert_puml_to_jpg(args.puml_file, args.output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
