from pathlib import Path, PurePosixPath
import hashlib
import subprocess
import tarfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "charts" / "whatap-operator"


class OperatorReleaseArtifactTest(unittest.TestCase):
    def test_archive_matches_source_and_repository_index(self):
        metadata = yaml.safe_load((CHART / "Chart.yaml").read_text())
        version = metadata["version"]
        archive = ROOT / f"whatap-operator-{version}.tgz"
        self.assertTrue(archive.is_file(), f"Missing release archive: {archive.name}")
        index = yaml.safe_load((ROOT / "index.yaml").read_text())
        entries = index["entries"]["whatap-operator"]
        matches = [entry for entry in entries if entry["version"] == version]
        self.assertEqual(1, len(matches))
        self.assertEqual(version, entries[0]["version"])
        self.assertEqual(metadata["appVersion"], matches[0]["appVersion"])
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), matches[0]["digest"])
        self.assertEqual([f"https://whatap.github.io/helm/{archive.name}"], matches[0]["urls"])

        source_files = {
            str(path.relative_to(CHART)): path.read_bytes()
            for path in CHART.rglob("*")
            if path.is_file()
        }
        packaged = {}
        with tarfile.open(archive, "r:gz") as package:
            for member in package.getmembers():
                path = PurePosixPath(member.name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertEqual("whatap-operator", path.parts[0])
                self.assertTrue(member.isfile() or member.isdir())
                if member.isfile():
                    relative = str(PurePosixPath(*path.parts[1:]))
                    self.assertNotIn(relative, packaged)
                    extracted = package.extractfile(member)
                    if extracted is None:
                        self.fail(f"Cannot read packaged file: {relative}")
                    packaged[relative] = extracted.read()
        self.assertEqual(set(source_files), set(packaged))
        for name, data in source_files.items():
            with self.subTest(file=name):
                if name == "Chart.yaml":
                    self.assertEqual(yaml.safe_load(data), yaml.safe_load(packaged[name]))
                else:
                    self.assertTrue(data == packaged[name], f"Source/package mismatch: {name}")

        def render(path):
            result = subprocess.run(
                ["helm", "template", "whatap-operator", str(path), "--namespace", "whatap-monitoring"],
                check=True, capture_output=True, text=True,
            )
            return result.stdout

        self.assertTrue(render(CHART) == render(archive), "Source/package rendering differs")


if __name__ == "__main__":
    unittest.main()
