"""Load Lexerat dictionaries and enrich entries with inflection tables."""
from dataclasses import dataclass, fields
from pathlib import Path

from lexerat import Entry, parse

from inflect import Inflector


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


@dataclass
class InflectedEntry(Entry):
    """A Lexerat-compatible entry whose extra field survives JSON serialization."""
    inflections: dict | None = None


def enrich_dictionary(entries, directory=None, models=None):
    """Return enriched copies suitable for Lexerat rendering or dataclasses.asdict.

    Only lemma entries with a nonempty infl field request a table. Other
    entries remain present, with inflections=None. Resolve against the entire
    dictionary, including model entries which do not themselves request tables.
    """
    entries = list(entries)
    inflector = Inflector(entries, directory, models)
    enriched = {}
    for entry in entries:
        data = {field.name: getattr(entry, field.name) for field in fields(Entry)}
        table = None
        if entry.kind == 'lemma' and entry.infl and entry.infl.strip():
            try:
                table = inflector.inflect(entry.lemma)
            except ValueError as error:
                raise ValueError(f'Inflecting {entry.lemma!r}: {error}') from error
        enriched[id(entry)] = InflectedEntry(**data, inflections=table)
    # Preserve linked expression identity without modifying the loaded entries.
    for entry in entries:
        enriched[id(entry)].expressions = [enriched.get(id(expression), expression)
                                           for expression in entry.expressions]
    return [enriched[id(entry)] for entry in entries]
