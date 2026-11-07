#!/usr/bin/env python3
'''Inflect principal parts or resolve a lemma through a Lexerat dictionary.'''
import argparse
import json
import sys
import unicodedata
from copy import copy
from itertools import product
from pathlib import Path

import yaml

# Walks thru the YAML tree, and outputs the leaves, such as:
# (('act', 'ind', 'pres', '1sg'), 'bero')
def leaves(tree, path=()):
    '''Yield (path, word) for every cell, including cells inside lists.'''
    if isinstance(tree, (dict, list)):
        items = tree.items() if isinstance(tree, dict) else enumerate(tree)
        for key, value in items:
            yield from leaves(value, path + (str(key),))
    elif isinstance(tree, str):
        yield path, tree
    else:
        raise ValueError(f"Expected a word at {'.'.join(path)}")

# Put generated forms back into the nested tree.
def rebuild(tree, forms, path=()):
    '''Preserve the model's table structure while replacing its words.'''
    if isinstance(tree, dict):
        return {k: rebuild(v, forms, path + (str(k),)) for k, v in tree.items()}
    if isinstance(tree, list):
        return [rebuild(v, forms, path + (str(i),)) for i, v in enumerate(tree)]
    return forms[path]


def substitutions(model_part, entry_part):
    '''Try shared suffixes longest first; keep a nonempty model prefix.'''
    shared = 0
    for a, b in zip(reversed(model_part), reversed(entry_part)):
        if a != b:
            break
        shared += 1
    for size in range(min(shared, len(model_part) - 1), -1, -1):
        old = model_part[:-size] if size else model_part
        new = entry_part[:-size] if size else entry_part
        yield old, new, size


class Model:
    '''Define a model with a name, kind, and ordered principal-part endings.'''

    kind = ''
    name = ''
    endings = {}  # Principal-part path -> recognition suffix, in input order.

    def __init__(self, directory=None):
        if directory is None:
            directory = Path(__file__).parent / 'model-words'
        file = Path(directory) / f'model-{self.kind}-{self.name}.yaml'
        self.table = yaml.safe_load(file.read_text(encoding='utf-8'))
        self.cells = dict(leaves(self.table))
        if not self.cells or not self.endings:
            raise ValueError('A model needs a nonempty table and endings dictionary')

    @classmethod
    def matches(cls, parts):
        if len(parts) != len(cls.endings):
            return False
        return all(part.endswith(end) for part, end in zip(parts, cls.endings.values()))

    def transfer(self, rules):
        '''Apply inferred prefixes, preferring the longest matching prefix.'''
        result = {}
        for path, word in self.cells.items():
            matches = [rule for rule in rules if word.startswith(rule[0])]
            if not matches:
                return None
            longest = max(len(old) for old, new, size in matches)
            forms = {new + word[len(old):] for old, new, size in matches
                     if len(old) == longest}
            if len(forms) != 1:
                return None  # Equally specific rules disagree about this cell.
            result[path] = forms.pop()
        return result

    def inflect(self, parts, paths=None):
        if not parts or not all(parts):
            raise ValueError('Principal parts must not be empty')
        if parts == [self.name] and paths is None:
            return self.table
        if paths is None and len(parts) != len(self.endings):
            raise ValueError(f'{self.name} needs {len(self.endings)} principal part(s)')

        anchors = [tuple(path.split('.')) for path in (paths if paths is not None else self.endings)]
        if len(anchors) != len(parts) or not anchors:
            raise ValueError('Each principal part needs one model path')
        choices = []
        for anchor, part in zip(anchors, parts):
            if anchor not in self.cells:
                raise ValueError(f"Missing model principal part: {'.'.join(anchor)}")
            choices.append(list(substitutions(self.cells[anchor], part)))

        if all(self.cells[anchor] == part for anchor, part in zip(anchors, parts)):
            return self.table

        # Maximize total shared suffix length, subject to explaining every cell
        # and reproducing every supplied principal part exactly.
        best = None
        best_score = -1
        ambiguous = False
        for rules in product(*choices):
            score = sum(size for old, new, size in rules)
            if score < best_score:
                continue
            result = self.transfer(rules)
            if result is None:
                continue
            if any(result[path] != part for path, part in zip(anchors, parts)):
                continue
            if score > best_score:
                best, best_score, ambiguous = result, score, False
            elif result != best:
                ambiguous = True

        if best is None:
            raise ValueError('Cannot infer prefixes that explain the whole model')
        if ambiguous:
            raise ValueError('Equally good stem boundaries produce different tables')
        return rebuild(self.table, best)

# o-stem animate
class Viros(Model):
    name = 'viros'
    kind = 'noun'
    endings = {'sg.nom': 'os'}

# a-stem
class Bena(Model):
    name = 'bena'
    kind = 'noun'
    endings = {'sg.nom': 'a'}

# o-stem neuter
class Donom(Model):
    name = 'donom'
    kind = 'noun'
    endings = {'sg.nom': 'om'}

# i-stem animate
class Mentis(Model):
    name = 'mentis'
    kind = 'noun'
    endings = {'sg.nom': 'is', 'sg.gen': 'ies'}

# u-stem animate
class Lokus(Model):
    name = 'lokus'
    kind = 'noun'
    endings = {'sg.nom': 'us', 'sg.gen': 'ues'}

# n-stem
class Nomyn(Model):
    name = 'nomyn'
    kind = 'noun'
    endings = {'sg.nom': 'yn', 'sg.gen': 'ens'}

# s-stem
class Nebos(Model):
    name = 'nebos'
    kind = 'noun'
    endings = {'sg.nom': 'os', 'sg.gen': 'esos'}

# liquid stem
class Pater(Model):
    name = 'pater'
    kind = 'noun'
    endings = {'sg.nom': 'ter', 'sg.gen': 'tres'}

# sigmatic liquid stem
class Svesor(Model):
    name = 'svesor'
    kind = 'noun'
    endings = {'sg.nom': 'sor', 'sg.gen': 'stres'}

# TODO: figure out what to call this
class Dvor(Model):
    name = 'dvor'
    kind = 'noun'
    endings = {'sg.nom': 'or', 'sg.gen': 'res'}

# Regular consonantal stem
class Ratzion(Model):
    name = 'ratzion'
    kind = 'noun'
    endings = {'sg.nom': ''}

# Regular adjective
class Rudros(Model):
    name = 'rudros'
    kind = 'adjective'
    endings = {'m.sg.nom': 'os'}

# Thematic verb
class Bero(Model):
    name = 'bero'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'o'}

# Thematic latinate verb
class Adapto(Model):
    name = 'adapto'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'o'}

# Athematic verb with sigmatic aorist
class Megmi(Model):
    name = 'megmi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'mi',
               'act.ind.pres.1pl': 'mos',
               'act.ind.aor.1sg': 'sym',
               'act.ind.aor.1pl': 'sme',
               'act.ind.perf.1sg': 'a',
               'act.ind.perf.1pl': 'me',
               }

# Athematic verb with a-vocalic root, reduplicated present, and asigmatic aorist
class Stistami(Model):
    name = 'stistami'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'mi',
               'act.ind.pres.1pl': 'mos',
               'act.ind.aor.1sg': 'm',
               'act.ind.aor.1pl': 'me',
               'act.ind.perf.1sg': 'a',
               'act.ind.perf.1pl': 'me',
               }

# Athematic verb with o-vocalic root, reduplicated present, and asigmatic aorist
class Didomi(Model):
    name = 'didomi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'mi',
               'act.ind.pres.1pl': 'mos',
               'act.ind.aor.1sg': 'm',
               'act.ind.aor.1pl': 'me',
               'act.ind.perf.1sg': 'a',
               'act.ind.perf.1pl': 'me',
               }

# Athematic verb with nu-present and asigmatic aorist
class Lipnumi(Model):
    name = 'lipnumi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'numi',
               'act.ind.pres.1pl': 'numos',
               'act.ind.aor.1sg': 'ym',
               'act.ind.aor.1pl': 'me',
               'act.ind.perf.1sg': 'a',
               'act.ind.perf.1pl': 'me',
               }

# Athematic verb with i-vocalic root, nu-present, and asigmatic aorist
class Sjlinumi(Model):
    name = 'sjlinumi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'numi',
               'act.ind.pres.1pl': 'numos',
               'act.ind.aor.1sg': 'm',
               'act.ind.aor.1pl': 'me',
               'act.ind.perf.1sg': 'a',
               'act.ind.perf.1pl': 'me',
               }

# Athematic verb with u-vocalic root, nu-present, and asigmatic aorist
class Strunumi(Model):
    name = 'strunumi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'numi',
               'act.ind.pres.1pl': 'numos',
               'act.ind.aor.1sg': 'm',
               'act.ind.aor.1pl': 'me',
               'act.ind.perf.1sg': 'a',
               'act.ind.perf.1pl': 'me',
               }

# Suppletive models have their own complete tables.
class Dekmi(Didomi):
    name = 'dekmi'

class Edmi(Didomi):
    name = 'edmi'

class Imi(Didomi):
    name = 'imi'

class Esmi(Model):
    name = 'esmi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'mi',
               'act.ind.pres.1pl': 'mos',
               'act.ind.pres.3pl': 'nti',
               'act.ind.aor.1sg': 'm',
               'act.ind.perf.1sg': 'a'}

# Add your new model class to this list.
MODEL_CLASSES = [
    Viros,
    Bena,
    Donom,
    Mentis,
    Lokus,
    Nomyn,
    Nebos,
    Pater,
    Svesor,
    Dvor,
    Ratzion,
    Rudros,
    Bero,
    Adapto,
    Megmi,
    Stistami,
    Didomi,
    Lipnumi,
    Sjlinumi,
    Strunumi,
    Dekmi,
    Edmi,
    Imi,
    Esmi,
]
MODELS = {model.name: model for model in MODEL_CLASSES}


def choose_model(parts, kind=None):
    candidates = []
    for name, model in MODELS.items():
        if kind and model.kind != kind:
            continue
        if parts == [name]:
            return name
        if model.matches(parts):
            candidates.append(name)
    if len(candidates) != 1:
        names = ', '.join(candidates) or 'none'
        raise ValueError(f'Matching models: {names}. Specify --model NAME.')
    return candidates[0]


def normalized(name):
    return unicodedata.normalize('NFC', name.strip())


def split_parts(text):
    """Accept bare principal parts or the contents of a complete @key macro."""
    text = text.strip()
    if text.startswith('@key(') and text.endswith(')'):
        text = text[5:-1]
    groups = [[part.strip() for part in group.split(',')]
              for group in text.split(';')]
    if not all(part for group in groups for part in group):
        raise ValueError('Principal parts must not be empty')
    return groups


def principal_paths(model, groups):
    """Semicolons select tense groups; commas select anchors within a group."""
    paths = list(model.endings)
    if len(groups) == 1 or model.kind != 'verb':
        if sum(map(len, groups)) != len(paths):
            raise ValueError(f'{model.name} needs {len(paths)} principal part(s); '
                             'use semicolons to supply partial tense groups')
        return paths
    grouped_paths = []
    for path in paths:
        group_key = path.rsplit('.', 1)[0]
        if not grouped_paths or grouped_paths[-1][0] != group_key:
            grouped_paths.append((group_key, []))
        grouped_paths[-1][1].append(path)
    if len(groups) != len(grouped_paths):
        raise ValueError(f'{model.name} needs {len(grouped_paths)} principal-part groups')
    selected = []
    for parts, (_, candidates) in zip(groups, grouped_paths):
        if len(parts) > len(candidates):
            raise ValueError(f'Too many principal parts for {candidates[0]}')
        selected.extend(candidates[:len(parts)])
    return selected


def load_dictionary(paths):
    """Read Lexerat JSON or raw sources (with Lexerat installed or alongside)."""
    entries = []
    raw = []
    for path in paths:
        path = Path(path)
        sources = sorted(path.glob('*.txt')) if path.is_dir() else [path]
        for source in sources:
            if source.suffix.lower() == '.json':
                data = json.loads(source.read_text(encoding='utf-8'))
                if not isinstance(data, list):
                    raise ValueError(f'{source}: expected a Lexerat JSON entry list')
                entries.extend(data)
            else:
                raw.append(source.read_text(encoding='utf-8'))
    if raw:
        try:
            from lexerat import parse
        except ImportError:
            sibling = Path(__file__).resolve().parent.parent / 'lexerat'
            if not (sibling / 'lexerat.py').is_file():
                raise ValueError('Reading raw dictionaries requires Lexerat. '
                                 'Install it or export the dictionary to JSON.') from None
            sys.path.insert(0, str(sibling))
            from lexerat import parse
        from dataclasses import asdict
        entries.extend(asdict(entry) for entry in parse('\n'.join(raw)))
    return entries


class Lexicon:
    """Resolve immediate models without losing intermediate principal parts."""

    def __init__(self, entries, directory=None):
        self.directory = directory
        self.entries = {}
        self.cache = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError('Dictionary entries must be JSON objects')
            if entry.get('kind', 'lemma') != 'lemma':
                continue
            forms = entry.get('forms', [])
            if not isinstance(forms, list) or not forms or not all(isinstance(part, str) and part for part in forms):
                raise ValueError('Dictionary entries need nonempty forms')
            self.entries.setdefault(normalized(forms[0]), []).append(entry)

    def resolve(self, lemma, trail=()):
        name = normalized(lemma)
        if name in trail:
            raise ValueError('Circular @infl reference: ' + ' -> '.join((*trail, name)))
        if name in self.cache:
            return self.cache[name]
        entries = self.entries.get(name, [])
        if len(entries) > 1:
            raise ValueError(f'Ambiguous dictionary lemma: {lemma!r}')
        if not entries:
            if name not in MODELS:
                raise ValueError(f'Unknown @infl target or dictionary lemma: {lemma!r}')
            result = MODELS[name](self.directory)
        else:
            entry = entries[0]
            forms = entry['forms']
            reference = entry.get('infl')
            if reference is not None and (not isinstance(reference, str) or not reference.strip()):
                raise ValueError(f'{lemma}: invalid infl model reference')
            reference = normalized(reference) if reference is not None else None
            if reference == name:
                if name not in MODELS:
                    raise ValueError(f'{lemma}: self-reference has no registered model table')
                result = MODELS[name](self.directory)
                # The table supplies the pattern; the lexicon supplies the parts.
                if len(forms) > 1:
                    groups = entry.get('principal_parts') or [forms]
                    paths = principal_paths(result, groups)
                    result.table = result.inflect(forms, paths)
                    result.cells = dict(leaves(result.table))
            elif reference:
                base = self.resolve(reference, (*trail, name))
                result = copy(base)
                if len(forms) == 1:
                    # A bare compound inherits EVERY form, including suppletion.
                    if not name.endswith(reference):
                        raise ValueError(f'{lemma}: cannot infer a prefix from {reference!r}; '
                                         'supply principal parts')
                    prefix = name[:-len(reference)]
                    result.table = rebuild(base.table, {
                        path: prefix + word for path, word in base.cells.items()})
                else:
                    groups = entry.get('principal_parts') or [forms]
                    result.table = base.inflect(forms, principal_paths(base, groups))
                result.cells = dict(leaves(result.table))
            else:
                model = choose_model(forms)
                result = MODELS[model](self.directory)
                groups = entry.get('principal_parts') or [forms]
                result.table = result.inflect(forms) if len(forms) == 1 else result.inflect(
                    forms, principal_paths(result, groups))
                result.cells = dict(leaves(result.table))
        result.name = name
        self.cache[name] = result
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('word', help="lemma, 'principal parts', or '@key(principal parts)'")
    parser.add_argument('--model', help='model word or dictionary lemma')
    parser.add_argument('--typ', choices=('noun', 'adjective', 'verb'))
    parser.add_argument('--models', type=Path, default=Path(__file__).parent / 'model-words')
    parser.add_argument('--dictionary', type=Path, nargs='+',
                        help='Lexerat JSON, raw source files, or raw source directories')
    args = parser.parse_args()
    try:
        groups = split_parts(args.word)
        parts = [part for group in groups for part in group]
        lexicon = Lexicon(load_dictionary(args.dictionary), args.models) if args.dictionary else None
        if args.model:
            if lexicon:
                model = lexicon.resolve(args.model)
            elif args.model in MODELS:
                model = MODELS[args.model](args.models)
            else:
                raise ValueError(f'Unknown model {args.model!r}; supply --dictionary for a dictionary model')
            # With an explicit model, a lone compound may inherit its whole table.
            if len(parts) == 1 and normalized(parts[0]) != normalized(args.model) and parts[0].endswith(args.model):
                prefix = parts[0][:-len(args.model)]
                table = rebuild(model.table, {path: prefix + word for path, word in model.cells.items()})
            elif len(parts) == 1 and normalized(parts[0]) == normalized(args.model):
                table = model.table
            else:
                table = model.inflect(parts, principal_paths(model, groups))
        elif lexicon and len(parts) == 1:
            model = lexicon.resolve(parts[0])
            table = model.table
        else:
            name = choose_model(parts, args.typ)
            model = MODELS[name](args.models)
            table = model.inflect(parts)
        if args.typ and model.kind != args.typ:
            raise ValueError('--model or dictionary entry and --typ disagree')
        print(json.dumps(table, ensure_ascii=False, indent=2))
    except (ValueError, OSError, yaml.YAMLError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
