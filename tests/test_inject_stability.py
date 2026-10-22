import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('inject_stability', Path(__file__).parents[1] / 'scripts/inject_stability.py')
injector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(injector)


class StabilityInjectionTests(unittest.TestCase):
    def test_all_apps_injected_once(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            (dist / 'stability.js').write_text('// passive')
            apps = [{'id': f'app{i}', 'path': f'apps/app{i}/v1.0.0/'} for i in range(13)]
            (dist / 'versions.json').write_text(json.dumps({'apps': apps}))
            for a in apps:
                folder = dist / a['path']
                folder.mkdir(parents=True)
                (folder / 'index.html').write_text('<!doctype html><html><head><title>Test</title></head><body></body></html>')
            injector.inject(dist)
            injector.inject(dist)
            for a in apps:
                text = (dist / a['path'] / 'index.html').read_text()
                self.assertEqual(text.count('src="../../../stability.js"'), 1)
                self.assertLess(text.index('stability.js'), text.index('</head>'))

    def test_rejects_missing_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            (dist / 'stability.js').write_text('')
            (dist / 'versions.json').write_text(json.dumps({'apps':[{'id':str(i),'path':f'apps/{i}/v1/'} for i in range(13)]}))
            with self.assertRaises(ValueError):
                injector.inject(dist)


if __name__ == '__main__':
    unittest.main()
