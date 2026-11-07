#!/usr/bin/env python3
"""Load raw dictionary files with Lexerat; optionally export their JSON."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from lexerat import parse


def load_dictionary(sources):
    """Return Lexerat entries from a path or an iterable of paths.

    Directories contribute their immediate *.txt files in filename order.
    Parse all sources together so expression links can cross file boundaries.
    Entry fields, including infl, retain Lexerat's ordinary semantics.
    """
    if isinstance(sources, (str, Path)):
        sources = [sources]
    files = []
    for source in sources:
        path = Path(source)
        if path.is_dir():
            files.extend(sorted(path.glob('*.txt')))
        else:
            files.append(path)
    if not files:
        raise ValueError('No dictionary source files found')
    text = '\n'.join(path.read_text(encoding='utf-8') for path in files)
    filename = str(files[0]) if len(files) == 1 else '<combined dictionary sources>'
    return parse(text, filename)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', type=Path, nargs='+',
                        help='raw dictionary files or directories of *.txt files')
    parser.add_argument('-o', '--output', type=Path)
    args = parser.parse_args()
    try:
        entries = load_dictionary(args.sources)
        text = json.dumps([asdict(entry) for entry in entries],
                          ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.write_text(text, encoding='utf-8')
        else:
            print(text, end='')
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
