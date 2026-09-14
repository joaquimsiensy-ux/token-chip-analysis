"""Differential and failure tests for disk-backed repair finalization."""
import gzip
import hashlib
import json
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "solana"))
from scripts.solana.sqd_repair_core import merge_edges, edge_logical_evidence
from scripts.solana.sqd_repair_stream import publish_merged_edges


class StreamRepairTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.base = self.root / "base.gz"
        self.out = self.root / "repaired.gz"
        self.addCleanup(self.clean_case)

    def clean_case(self):
        for path in (self.base, self.out):
            if path.exists():
                path.unlink()
        self.root.rmdir()

    def write_base(self, rows):
        with gzip.open(self.base, "wt", encoding="utf-8") as handle:
            handle.write("\n")
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def check_case(self, base, repairs, maps):
        self.write_base(base)
        result = publish_merged_edges(self.base, iter(repairs), maps, self.out)
        expected = merge_edges(base, repairs, maps)
        raw = b"".join((json.dumps(list(row), ensure_ascii=False,
                                    separators=(",", ":")) + "\n").encode()
                       for row in expected)
        self.assertEqual(gzip.decompress(self.out.read_bytes()), raw)
        self.assertEqual(self.out.read_bytes(), gzip.compress(raw, mtime=0))
        logical, count = edge_logical_evidence(expected)
        self.assertEqual(result["edge_logical_sha256"], logical)
        self.assertEqual(result["edge_rows"], count)
        self.assertEqual(result["edges_added"], len(repairs))
        self.assertEqual(result["edge_file_size"], self.out.stat().st_size)
        self.assertEqual(result["edge_file_sha256"],
                         hashlib.sha256(self.out.read_bytes()).hexdigest())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         ["base.gz", "repaired.gz"])

    def test_random_differential(self):
        rng = random.Random(74021)
        for i in range(15):
            with self.subTest(i=i):
                maps = {s: [[t, 7-t, "signature"] for t in range(8)]
                        for s in (0, 2, 4)}
                rows = [[rng.randrange(100), rng.randrange(6), rng.randrange(8),
                         -1, rng.choice(["a", "é", "猫"]), "to",
                         rng.choice([2, 10, 10**60+1])]
                        for _ in range(170)]
                self.check_case(rows[:130], rows[130:], maps)
                self.out.unlink()

    def test_duplicates_ties_and_integer_width(self):
        big = 10**40
        base = [[99, big, big, -1, "a", "b", 10],
                [98, big, big, -1, "a", "b", 2],
                [96, big, big, -1, "a", "b", 10],
                [99, big, big, -1, "a", "b", 10]]
        repairs = [[5, big, big+1, -1, "a", "b", 10]]
        self.check_case(base, repairs, {big: [[big, big+1, "sig"]]})

    def test_empty(self):
        self.check_case([], [], {})

    def test_missing_map_and_bad_edges_leave_no_output(self):
        row = [1, 1, 0, -1, "a", "b", 1]
        self.write_base([row])
        with self.assertRaisesRegex(ValueError, "no slot-index solution"):
            publish_merged_edges(self.base, [], {1: []}, self.out)
        for bad in ([1, 2], [True, 1, 0, -1, "a", "b", 1],
                    [1, 1, 0, -1, "a", "b", -1]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    publish_merged_edges(self.base, [row, bad], {}, self.out)
                self.assertFalse(self.out.exists())
                self.assertEqual([p.name for p in self.root.iterdir()], ["base.gz"])

    def test_bad_base_and_bad_mapped_index(self):
        self.write_base([[1, 1, 0, -1, "a", "b", 1]])
        with self.assertRaises(ValueError):
            publish_merged_edges(self.base, [], {1: [[0, -2, "sig"]]}, self.out)
        self.write_base([[1, 2]])
        with self.assertRaises(ValueError):
            publish_merged_edges(self.base, [], {}, self.out)
        self.assertFalse(self.out.exists())

    def test_existing_same_reused_different_preserved(self):
        rows = [[1, 1, 0, -1, "a", "b", 1]]
        self.check_case(rows, [], {})
        before = self.out.stat()
        publish_merged_edges(self.base, [], {}, self.out)
        self.assertEqual(before.st_ino, self.out.stat().st_ino)
        original = self.out.read_bytes()
        with self.assertRaises(FileExistsError):
            publish_merged_edges(self.base, rows, {}, self.out)
        self.assertEqual(self.out.read_bytes(), original)

    def test_generator_failure_does_not_publish(self):
        self.write_base([])
        def bad_generator():
            yield [1, 1, 0, -1, "a", "b", 1]
            raise RuntimeError("injected producer failure")
        with self.assertRaisesRegex(RuntimeError, "injected"):
            publish_merged_edges(self.base, bad_generator(), {}, self.out, work_dir=self.root)
        self.assertEqual([p.name for p in self.root.iterdir()], ["base.gz"])

    def test_invalid_gzip_and_publish_failure(self):
        self.base.write_bytes(b"not gzip")
        with self.assertRaises(gzip.BadGzipFile):
            publish_merged_edges(self.base, [], {}, self.out)
        self.write_base([[1, 1, 0, -1, "a", "b", 1]])
        with patch("scripts.solana.sqd_repair_stream.os.link",
                   side_effect=PermissionError("injected exclusive publish failure")) as link:
            with self.assertRaisesRegex(PermissionError, "injected exclusive"):
                publish_merged_edges(self.base, [], {}, self.out)
            link.assert_called_once()
        self.assertEqual([p.name for p in self.root.iterdir()], ["base.gz"])

    def test_bounded_memory(self):
        # Isolated process: measure real peak RSS (including SQLite) and Python
        # allocations. Descending keys force a real external ordering workload.
        code = r'''
import gzip, json, resource, sys, tracemalloc
from pathlib import Path
from scripts.solana.sqd_repair_stream import publish_merged_edges
root = Path(sys.argv[1]); n = int(sys.argv[2])
with gzip.open(root / 'base.gz', 'wt') as f:
    for i in range(n, 0, -1):
        f.write(json.dumps([i, i, 0, -1, 'a', 'b', 10**40]) + '\n')
tracemalloc.start()
result = publish_merged_edges(root / 'base.gz', (), {}, root / 'out.gz')
peak = tracemalloc.get_traced_memory()[1]
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if sys.platform != 'darwin': rss *= 1024
print(json.dumps({'rss': rss, 'python_peak': peak, 'rows': result['edge_rows']}))
'''
        observations = []
        for n in (2000, 120000, 600000):
            directory = Path(tempfile.mkdtemp())
            try:
                run = subprocess.run([sys.executable, "-c", code, directory, str(n)],
                                     cwd=ROOT, check=True, capture_output=True, text=True)
                observation = json.loads(run.stdout)
                self.assertEqual(observation["rows"], n)
                observations.append(observation)
            finally:
                for path in (directory / "base.gz", directory / "out.gz"):
                    if path.exists():
                        path.unlink()
                directory.rmdir()
        print("stream-memory-evidence=" + json.dumps(observations), flush=True)
        self.assertLess(observations[1]["python_peak"], 8 * 1024**2)
        self.assertLess(observations[1]["rss"] - observations[0]["rss"], 40 * 1024**2)
        self.assertLess(observations[2]["python_peak"], 8 * 1024**2)
        self.assertLess(observations[2]["rss"] - observations[1]["rss"], 24 * 1024**2)


if __name__ == "__main__":
    unittest.main()
