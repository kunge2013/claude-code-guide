---
name: puml2jpg
description: This skill converts PlantUML (.puml) diagram files to image formats (JPG/PNG). Use this skill when the user provides a .puml file path and requests conversion to an image, or when the user wants to visualize PlantUML diagrams. The skill automatically places the generated image in the same directory as the source .puml file.
---

# Puml2jpg

## Overview

Convert PlantUML diagram files (.puml) to image formats. The skill extracts the diagram definition from the specified file and generates a corresponding image file.

## Quick Start

When a user provides a .puml file path:

1. Identify the .puml file path from the user's request
2. Execute the conversion script
3. Report the location of the generated image

## Usage

### Single File Conversion

Execute the conversion script directly:

```bash
python3 scripts/puml2jpg.py /path/to/diagram.puml
```

The generated image will be saved in the same directory as the input file with the same base name.

### Specifying Output Directory

To save the image to a different directory:

```bash
python3 scripts/puml2jpg.py /path/to/diagram.puml -o /output/directory
```

## Requirements

The script automatically installs the required `plantuml` Python package on first run. The conversion uses the public PlantUML server (plantuml.com) for processing.

**Note:** The public server generates PNG format. Local JPG generation requires plantuml.jar and Java runtime.

## Output

- **Default location:** Same directory as the input .puml file
- **File naming:** `{input_filename}.png` (same base name as input)
- **Format:** PNG (JPG support requires local plantuml.jar)

## Example

User input: `"Convert my diagram.puml to image"`

Response:
```bash
python3 scripts/puml2jpg.py diagram.puml
```

Output: `✓ Generated: /path/to/diagram.png`

## Resources

### scripts/

- **puml2jpg.py** - Main conversion script that handles PlantUML to image conversion
