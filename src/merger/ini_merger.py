"""INI file merger for combining base and custom strings."""
from pathlib import Path
from typing import Dict


def merge_ini_files(
    source_path: str | Path,
    overrides_dict: Dict[str, str],
    output_path: str | Path
) -> None:
    """Merge source INI with overrides, preserving all lines.

    Reads source file line-by-line, replaces values for matching keys,
    and writes to output as UTF-8.

    Args:
        source_path: Path to base global.ini
        overrides_dict: Dictionary of key-value overrides
        output_path: Path to write merged output
    """
    source_path = Path(source_path)
    output_path = Path(output_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(source_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:

            for line in infile:
                # Preserve line ending style, but work with stripped version
                line_rstrip = line.rstrip('\n\r')
                original_ending = line[len(line_rstrip):]

                # Skip processing for comments and empty lines
                if not line_rstrip.strip() or line_rstrip.strip().startswith(';'):
                    outfile.write(line)
                    continue

                # Try to split on first '='
                if '=' not in line_rstrip:
                    outfile.write(line)
                    continue

                key, value = line_rstrip.split('=', 1)
                key_stripped = key.strip()

                # Check if we have an override for this key
                if key_stripped in overrides_dict:
                    # Replace value, preserving key spacing
                    new_value = overrides_dict[key_stripped]
                    new_line = f"{key}={new_value}{original_ending}"
                    outfile.write(new_line)
                else:
                    # Keep original line
                    outfile.write(line)

    except Exception as e:
        raise IOError(f"Error merging INI files: {e}")
