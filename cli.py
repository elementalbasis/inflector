#!/usr/bin/env python3
"""Read a Lexerat dictionary and export entries enriched with inflection tables."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

import yaml

from dictionary import enrich_dictionary, load_dictionary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', type=Path, nargs='+',
                        help='raw dictionary files or directories of *.txt files')
    parser.add_argument('--models', type=Path,
                        help='alternative directory of registered YAML model tables')
    parser.add_argument('-o', '--output', type=Path)
    args = parser.parse_args()
    try:
        entries = enrich_dictionary(load_dictionary(args.sources), directory=args.models)
        text = json.dumps([asdict(entry) for entry in entries],
                          ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.write_text(text, encoding='utf-8')
        else:
            print(text, end='')
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
