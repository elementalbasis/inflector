import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from inflect import Lexicon, MODELS, leaves, load_dictionary, principal_paths, split_parts


FIXTURE = [
    {'forms': ['megmi', 'mygmos', 'megsym', 'mygsme', 'memoga', 'memygme'],
     'principal_parts': [['megmi', 'mygmos'], ['megsym', 'mygsme'], ['memoga', 'memygme']],
     'infl': 'megmi'},
    {'forms': ['jekmi', 'ikmos', 'jeksym', 'iksme', 'jejoka', 'jeikme'], 'infl': 'megmi'},
    {'forms': ['apojekmi'], 'infl': 'jekmi'},
    {'forms': ['upapojekmi'], 'infl': 'apojekmi'},
]


class DictionaryTests(unittest.TestCase):
    def test_intermediate_parts_and_all_compound_cells(self):
        lexicon = Lexicon(FIXTURE)
        root = lexicon.resolve('jekmi')
        compound = lexicon.resolve('apojekmi')
        deep = lexicon.resolve('upapojekmi')
        self.assertEqual(root.table['act']['ind']['perf']['1sg'], 'jejoka')
        self.assertEqual(root.table['act']['ind']['pres']['1pl'], 'ikmos')
        self.assertEqual(compound.cells, {p: 'apo' + w for p, w in root.cells.items()})
        self.assertEqual(deep.cells, {p: 'up' + w for p, w in compound.cells.items()})
        self.assertEqual(lexicon.resolve('megmi').table['act']['ind']['aor']['1sg'], 'megsym')

    def test_partial_tense_groups(self):
        entry = {'forms': ['sjostrunumi', 'sjostrum', 'sjostestruka'],
                 'principal_parts': [['sjostrunumi'], ['sjostrum'], ['sjostestruka']],
                 'infl': 'strunumi'}
        result = Lexicon([entry]).resolve('sjostrunumi')
        base = MODELS['strunumi']()
        self.assertEqual(result.cells, {p: 'sjo' + w for p, w in base.cells.items()})

    def test_terminal_partial_parts_and_suppletion(self):
        entries = [
            {'forms': ['lipnumi', 'lipym', 'leloipa', 'lelipme'],
             'principal_parts': [['lipnumi'], ['lipym'], ['leloipa', 'lelipme']],
             'infl': 'lipnumi'},
            {'forms': ['imi', 'imos', 'bem', 'byme', 'beboka', 'bebykme'],
             'principal_parts': [['imi', 'imos'], ['bem', 'byme'], ['beboka', 'bebykme']],
             'infl': 'imi'},
            {'forms': ['anaimi'], 'infl': 'imi'}]
        lex = Lexicon(entries)
        self.assertEqual(lex.resolve('lipnumi').table, MODELS['lipnumi']().table)
        self.assertEqual(lex.resolve('anaimi').table['act']['ind']['aor']['1sg'], 'anabem')
        self.assertEqual(lex.resolve('anaimi').table['act']['ind']['pres']['3pl'], 'anajenti')

    def test_bad_references(self):
        cases = [
            ([{'forms': ['a'], 'infl': 'b'}, {'forms': ['b'], 'infl': 'a'}], 'a', 'Circular.*a -> b -> a'),
            ([{'forms': ['a'], 'infl': 'missing'}], 'a', 'Unknown.*missing'),
            ([{'forms': ['a'], 'infl': 'a'}], 'a', 'no registered model table'),
            ([{'forms': ['a'], 'infl': 'viros'}], 'a', 'cannot infer a prefix'),
            ([{'forms': ['a']}, {'forms': ['a']}], 'a', 'Ambiguous'),
        ]
        for entries, lemma, error in cases:
            with self.subTest(lemma=lemma, error=error):
                with self.assertRaisesRegex(ValueError, error):
                    Lexicon(entries).resolve(lemma)

    def test_all_registered_tables_and_anchor_roundtrips(self):
        for name, cls in MODELS.items():
            with self.subTest(model=name):
                model = cls()
                parts = [model.cells[tuple(p.split('.'))] for p in model.endings]
                self.assertEqual(model.inflect([name]), model.table)
                self.assertEqual(model.inflect(parts), model.table)

    def test_existing_noun_and_verb_usage(self):
        self.assertEqual(MODELS['viros']().inflect(['stauros'])['sg']['gen'], 'staurosio')
        groups = split_parts('@key(jekmi, ikmos; jeksym, iksme; jejoka, jeikme)')
        model = MODELS['megmi']()
        table = model.inflect([p for g in groups for p in g], principal_paths(model, groups))
        self.assertEqual(table['act']['ind']['perf']['1sg'], 'jejoka')

    def test_json_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dictionary.json'
            path.write_text(json.dumps(FIXTURE))
            self.assertEqual(len(load_dictionary([path])), len(FIXTURE))
            script = Path(__file__).resolve().parents[1] / 'inflect.py'
            process = subprocess.run([sys.executable, str(script), 'apojekmi',
                                      '--dictionary', str(path)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)['act']['ind']['perf']['1sg'], 'apojejoka')


if __name__ == '__main__':
    unittest.main()
