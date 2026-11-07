#!/usr/bin/env python3
'''Model-word inflection and dictionary model-reference resolution.'''
from collections.abc import Mapping
from copy import copy, deepcopy
import unicodedata
import re
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
                raise ValueError(f"Missing model principal part: {'.'.join(anchor)}")
            choices.append(list(substitutions(self.cells[anchor], part)))

        # Identity needs no inferred stem substitutions. This also preserves
        # suppletive cells not covered by any principal-part prefix.
        if all(self.cells[path] == part for path, part in zip(anchors, parts)):
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

# Regular fleeting s noun
class Agents(Model):
    name = 'agents'
    kind = 'noun'
    endings = {'sg.nom': 'nts'}

    @classmethod
    def matches(cls, parts):
        return (
                len(parts) == 1
                and parts[0].endswith(('nts', 'rts', 'tats'))
                )

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

# Suppletive verb with six principal parts
class Dekmi(Model):
    name = 'dekmi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'dekmi',
               'act.ind.pres.1pl': 'dykmos',
               'act.ind.aor.1sg': 'masjym',
               'act.ind.aor.1pl': 'mysjme',
               'act.ind.perf.1sg': 'memosja',
               'act.ind.perf.1pl': 'memysjme',
               }

# Suppletive verb with six principal parts
class Edmi(Model):
    name = 'edmi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'edmi',
               'act.ind.pres.1pl': 'edmos',
               'act.ind.aor.1sg': 'brom',
               'act.ind.aor.1pl': 'bryme',
               'act.ind.perf.1sg': 'bebroka',
               'act.ind.perf.1pl': 'bebrykme',
               }

# Suppletive verb with the same six input anchors as other athematic verbs
class Esmi(Model):
    name = 'esmi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'mi',
               'act.ind.pres.1pl': 'mos',
               'act.ind.aor.1sg': 'm',
               'act.ind.aor.1pl': 'me',
               'act.ind.perf.1sg': 'a',
               'act.ind.perf.1pl': 'me',
               }

# Suppletive verb with six principal parts
class Imi(Model):
    name = 'imi'
    kind = 'verb'
    endings = {'act.ind.pres.1sg': 'imi',
               'act.ind.pres.1pl': 'imos',
               'act.ind.aor.1sg': 'bem',
               'act.ind.aor.1pl': 'byme',
               'act.ind.perf.1sg': 'beboka',
               'act.ind.perf.1pl': 'bebykme',
               }

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
    Agents,
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
    Esmi,
    Imi,
]
MODELS = {model.name: model for model in MODEL_CLASSES}


def choose_model(parts, kind=None, models=None):
    """Prefer specific recognition endings over the general consonant model."""
    registry = MODELS if models is None else models
    candidates = []
    for name, model in registry.items():
        if kind and model.kind != kind:
            continue
        if parts == [name]:
            return name
        if model.matches(parts):
            candidates.append((sum(map(len, model.endings.values())), name, model))
    if candidates:
        best_score = max(score for score, _, _ in candidates)
        best = [(name, model) for score, name, model in candidates if score == best_score]
        # Aliases for the same class do not introduce a genuine ambiguity.
        classes = {model for _, model in best}
        if len(classes) == 1:
            model = next(iter(classes))
            return model.name if model.name in dict(best) else best[0][0]
    names = ', '.join(name for _, name, _ in candidates) or 'none'
    raise ValueError(f'Matching models: {names}. Supply a usable @infl reference.')


NOUN_TYPES = {'noun', 'n', 'm', 'f', 'mf', 'neut', 'masc', 'fem',
              'neuter', 'masculine', 'feminine', 'animate', 'inanimate'}
VERB_TYPES = {'verb', 'v', 'vt', 'vi', 'vtr', 'vintr'}
NEUTER_TYPES = {'n', 'neut', 'neuter'}


def entry_types(entry):
    result = set()
    for definition in entry_field(entry, 'definitions', ()):
        typ = entry_field(definition, 'typ')
        if typ is None:
            typ = entry_field(definition, 'state', {}).get('typ')
        if typ:
            result.update(re.findall(r'[^\W_]+', typ.casefold()))
    return result


def entry_kind(entry):
    types = entry_types(entry)
    if types & {'pron', 'pronoun', 'num', 'numeral', 'number'}:
        return None
    noun, verb = bool(types & NOUN_TYPES), bool(types & VERB_TYPES)
    if noun and verb:
        raise ValueError('Both noun and verb senses: supply an explicit @infl reference')
    return 'noun' if noun else 'verb' if verb else None


def thematic_parts(parts, model):
    """Consume a thematic class marker without passing it as a stem anchor."""
    if len(parts) == 1:
        return parts
    ending = 'amos' if issubclass(model, Adapto) else 'omos'
    if (len(parts) == 2 and parts[0].endswith('o')
            and parts[1] in ('-' + ending, parts[0][:-1] + ending)):
        return parts[:1]
    raise ValueError(f'{model.name}: expected one thematic lemma or its -{ending} marker')


def infer_entry(entry, models):
    """Return a registered model name and its normalized input parts."""
    parts = list(entry_field(entry, 'forms'))
    kind = entry_kind(entry)
    if kind == 'verb':
        if parts[0].endswith('mi'):
            raise ValueError('Athematic verbs require @infl and six principal parts '
                             '(prefixed compounds may inherit their model)')
        if not parts[0].endswith('o'):
            raise ValueError('Cannot infer a thematic verb from a lemma not ending in -o')
        latinate = len(parts) == 2 and parts[1] in ('-amos', parts[0][:-1] + 'amos')
        cls = Adapto if latinate else Bero
        parts = thematic_parts(parts, cls)
        candidates = [name for name, model in models.items() if model is cls]
        if candidates:
            return (cls.name if cls.name in candidates else candidates[0]), parts
        raise ValueError(f'No registered {cls.name} model')
    if kind != 'noun':
        raise ValueError('No noun or verb type available for automatic inflection')

    # Neuter nouns need a model with neuter nominative/accusative behavior.
    neuter = bool(entry_types(entry) & NEUTER_TYPES)
    registry = {name: model for name, model in models.items()
                if model.kind == 'noun'
                and (not neuter or model in (Donom, Nomyn, Nebos))}
    # A redundant regular genitive can be checked after selecting by nominative.
    if len(parts) == 2:
        regular_genitives = {Viros: parts[0][:-2] + 'osio',
                             Donom: parts[0][:-2] + 'osio', Bena: parts[0] + 's'}
        for name, model in registry.items():
            if (model in regular_genitives and model.matches(parts[:1])
                    and parts[1] == regular_genitives[model]):
                return name, parts[:1]
    if len(parts) == 1:
        lemma = parts[0]
        for name, model in registry.items():
            if lemma == model.name:
                return name, parts
        # These classes have no one-part model in the current registry. Do not
        # silently send them through the empty-ending consonant fallback.
        specific = any(model.matches(parts) and any(model.endings.values())
                       for model in registry.values())
        if not specific and lemma.endswith(('tats', 'ants', 'ents', 'onts', 'rts', 'es', 'e', 'i', 'u')):
            raise ValueError('This noun pattern needs an additional paradigm or explicit @infl')
        # An omitted genitive means a regular unchanged stem for productive
        # i-, u-, and n-stems. Supplied genitives carry any ablaut instead.
        if not specific:
            for name, model in registry.items():
                if model in (Mentis, Lokus, Nomyn):
                    nom_end, gen_end = model.endings.values()
                    if lemma.endswith(nom_end):
                        return name, [lemma, lemma[:-len(nom_end)] + gen_end]
        incomplete = [model for model in registry.values()
                      if len(model.endings) > 1
                      and lemma.endswith(next(iter(model.endings.values())))]
        regular = any(model in (Viros, Bena, Donom) and model.matches(parts)
                      for model in registry.values())
        if incomplete and not specific and not regular and not lemma.endswith(('tor', 'tzion', 'sion', 'al', 'il', 'en')):
            raise ValueError('This noun requires its genitive principal part')
    return choose_model(parts, kind='noun', models=registry), parts


def entry_field(entry, name, default=None):
    """Accept Lexerat entry objects or their JSON dictionary representation."""
    return entry.get(name, default) if isinstance(entry, Mapping) else getattr(entry, name, default)


def normalized(text):
    return unicodedata.normalize('NFC', text.strip())


class Inflector:
    """Index a dictionary and resolve each immediate model before its child.

    ``inflect(lemma)`` returns a table. ``resolve(lemma)`` returns a model with
    that table and its principal-part anchors. Input entries are never changed.
    The optional models mapping can register additional class labels.
    """

    def __init__(self, entries=(), directory=None, models=None):
        self.directory = directory
        self.models = dict(MODELS if models is None else models)
        self.entries = {}
        self.cache = {}
        for entry in entries:
            if entry_field(entry, 'kind', 'lemma') != 'lemma':
                continue
            parts = entry_field(entry, 'forms')
            if (not isinstance(parts, (list, tuple)) or not parts
                    or any(not isinstance(part, str) or not part.strip() for part in parts)):
                raise ValueError('Dictionary entries need nonempty forms')
            self.entries.setdefault(normalized(parts[0]), []).append(entry)

    @staticmethod
    def derive(base, name, table):
        result = copy(base)
        result.name = name
        result.table = table
        result.cells = dict(leaves(table))
        return result

    @staticmethod
    def adapt(base, parts):
        if isinstance(base, (Bero, Adapto)):
            parts = thematic_parts(parts, type(base))
        if parts == [base.name]:
            return base.table
        if len(parts) == 1 and len(base.endings) > 1:
            lemma = normalized(parts[0])
            if not lemma.endswith(base.name):
                raise ValueError(f'{parts[0]!r} needs principal parts to follow {base.name!r}; '
                                 'its prefix cannot be inferred')
            prefix = lemma[:-len(base.name)]
            # Prefix the complete resolved table, including suppletive forms.
            return rebuild(base.table, {path: prefix + word for path, word in base.cells.items()})
        return base.inflect(parts)

    def resolve(self, lemma, trail=()):
        name = normalized(lemma)
        if name in trail:
            raise ValueError('Circular @infl reference: ' + ' -> '.join((*trail, name)))
        if name in self.cache:
            return self.cache[name]
        matches = self.entries.get(name, [])
        if len(matches) > 1:
            raise ValueError(f'Ambiguous dictionary lemma: {name!r}')
        if not matches:
            if name not in self.models:
                chain = ' -> '.join((*trail, name))
                raise ValueError(f'Unknown inflection model: {chain}')
            base = self.models[name](self.directory)
            result = self.derive(base, name, base.table)
        else:
            entry = matches[0]
            parts = list(entry_field(entry, 'forms'))
            reference = entry_field(entry, 'infl')
            if reference is not None and not isinstance(reference, str):
                raise ValueError(f'{name!r}: infl must be text')
            reference = normalized(reference) if reference is not None else ''
            if not reference:
                if entry_kind(entry) is None and name in self.models:
                    target = name
                else:
                    target, parts = infer_entry(entry, self.models)
                base = (self.models[target](self.directory) if target == name
                        else self.resolve(target, (*trail, name)))
                result = self.derive(base, name, self.adapt(base, parts))
            elif reference == name:
                if name not in self.models:
                    raise ValueError(f'{name!r}: no registered model or usable @infl reference')
                base = self.models[name](self.directory)
                result = self.derive(base, name, self.adapt(base, parts))
            else:
                base = self.resolve(reference, (*trail, name))
                result = self.derive(base, name, self.adapt(base, parts))
        self.cache[name] = result
        return result

    def inflect(self, lemma):
        """Return an independent table so editing it cannot corrupt the cache."""
        return deepcopy(self.resolve(lemma).table)
