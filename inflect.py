#!/usr/bin/env python3
'''Small model-word inflector. Requires PyYAML; no dictionary needed.'''
import argparse
import json
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
        raise ValueError(f'Expected a word at {'.'.join(path)}')

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

    def inflect(self, parts):
        if not parts or not all(parts):
            raise ValueError('Principal parts must not be empty')
        if parts == [self.name]:
            return self.table
        if len(parts) != len(self.endings):
            raise ValueError(f'{self.name} needs {len(self.endings)} principal part(s)')

        anchors = [tuple(path.split('.')) for path in self.endings]
        choices = []
        for anchor, part in zip(anchors, parts):
            if anchor not in self.cells:
                raise ValueError(f'Missing model principal part: {'.'.join(anchor)}')
            choices.append(list(substitutions(self.cells[anchor], part)))

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


class Viros(Model):
    name = 'viros'
    kind = 'noun'
    endings = {'sg.nom': 'os'}


class Bena(Model):
    name = 'bena'
    kind = 'noun'
    endings = {'sg.nom': 'a'}


class Donom(Model):
    name = 'donom'
    kind = 'noun'
    endings = {'sg.nom': 'om'}


class Mentis(Model):
    name = 'mentis'
    kind = 'noun'
    endings = {'sg.nom': 'is', 'sg.gen': 'ies'}


class Lokus(Model):
    name = 'lokus'
    kind = 'noun'
    endings = {'sg.nom': 'us', 'sg.gen': 'ues'}


class Nomyn(Model):
    name = 'nomyn'
    kind = 'noun'
    endings = {'sg.nom': 'yn', 'sg.gen': 'ens'}

class Nebos(Model):
    name = 'nebos'
    kind = 'noun'
    endings = {'sg.nom': 'os', 'sg.gen': 'esos'}

class Pater(Model):
    name = 'pater'
    kind = 'noun'
    endings = {'sg.nom': 'ter', 'sg.gen': 'tres'}


class Svesor(Model):
    name = 'svesor'
    kind = 'noun'
    endings = {'sg.nom': 'sor', 'sg.gen': 'stres'}


class Dvor(Model):
    name = 'dvor'
    kind = 'noun'
    endings = {'sg.nom': 'or', 'sg.gen': 'res'}


class Rudros(Model):
    name = 'rudros'
    kind = 'adjective'
    endings = {'m.sg.nom': 'os'}


class Bero(Model):
    name = 'bero'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'o'}


class Adapto(Model):
    name = 'adapto'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'o'}


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
    Rudros,
    Bero,
    Adapto,
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('word', help=''word, second part' or '@key(word, second part)'')
    parser.add_argument('--model', choices=MODELS)
    parser.add_argument('--typ', choices=('noun', 'adjective', 'verb'))
    parser.add_argument('--models', type=Path, default=Path(__file__).parent / 'model-words')
    args = parser.parse_args()
    text = args.word.strip()
    if text.startswith('@key(') and text.endswith(')'):
        text = text[5:-1]
    parts = [part.strip() for part in text.split(',')]
    try:
        if not all(parts):
            raise ValueError('Principal parts must not be empty')
        model = args.model or choose_model(parts, args.typ)
        if args.typ and MODELS[model].kind != args.typ:
            raise ValueError('--model and --typ disagree')
        print(json.dumps(MODELS[model](args.models).inflect(parts), ensure_ascii=False, indent=2))
    except (ValueError, OSError, yaml.YAMLError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
