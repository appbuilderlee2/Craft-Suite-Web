import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('build', Path(__file__).parents[1] / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildTests(unittest.TestCase):
    def test_stable_selection(self):
        releases = [{'tag_name': tag, 'prerelease': flag} for tag, flag in [('v0.9.0', False), ('v0.10.0', False), ('v9.0.0-rc.1', False), ('v8.0.0', True)]]
        self.assertEqual(build.choose_release(releases)['tag_name'], 'v0.10.0')

    def test_checksum_exact(self):
        digest = 'a' * 64
        self.assertEqual(build.checksum_for(digest + '  app.zip', 'app.zip'), digest)
        with self.assertRaises(ValueError):
            build.checksum_for(digest + '  other.zip', 'app.zip')
        with self.assertRaises(ValueError):
            build.checksum_for((digest + '  app.zip\n') * 2, 'app.zip')

    def extract(self, filename):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr(filename, 'content')
        data.seek(0)
        with tempfile.TemporaryDirectory() as temp:
            return build.safe_extract(data, Path(temp))

    def test_path_traversal(self):
        for name in ['../escape', '/absolute', 'dir/../../escape', 'dir\\escape', 'C:/escape']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.extract(name)

    def test_missing_index(self):
        with self.assertRaises(ValueError):
            self.extract('app/file.js')

    def test_asset_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'index.html').write_text('<script src="./app.js"></script>')
            (root / 'app.js').write_text('')
            (root / 'app.wasm').write_bytes(b'\0asm')
            build.verify_web(root)
            (root / 'index.html').write_text('<script src="/app.js"></script>')
            with self.assertRaises(ValueError):
                build.verify_web(root)

    def test_native_binary_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'index.html').write_text('')
            (root / 'app.js').write_text('')
            (root / 'app.wasm').write_bytes(b'\0asm')
            (root / 'unexpected').write_bytes(b'\x7fELF')
            with self.assertRaises(ValueError):
                build.verify_web(root)


if __name__ == '__main__':
    unittest.main()
