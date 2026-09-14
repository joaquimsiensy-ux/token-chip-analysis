#!/usr/bin/env python3
"""State selection must not materialize an entire chain interval."""
import ast
import gc
import importlib.util
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import weakref
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/solana"))
import sqd_gap_repair as repair

class IndexOnlyStates:
    def __init__(self): self.lookups = []
    def __len__(self): return 140002896
    def __iter__(self): raise AssertionError("full interval iteration/materialization forbidden")
    def __getitem__(self, index):
        if not 0 <= index < len(self): raise IndexError(index)
        self.lookups.append(index)
        return "HEALTHY" if index else "DEFECT_CANDIDATE"

class StateMemoryTests(unittest.TestCase):
    def test_whole_states_are_released_after_selection(self):
        references = []
        class States:
            def __len__(self): return 2
            def __getitem__(self, index): return ["DEFECT_CANDIDATE", "HEALTHY"][index]
        def plan(*args):
            states = States()
            references.append(weakref.ref(states))
            return ({"candidate_slots": [10]}, (None, None, {}),
                    ({}, {"slot_counts": {"from_slot": 10}}, None, None,
                     {"recomputed": {"states": states}}))
        released = []
        def stop(*args):
            gc.collect()
            released.append(references[0]() is None)
            raise RuntimeError("stop before any production writes")
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(repair, "_plan", side_effect=plan), \
                mock.patch.object(repair, "sqd_repair_paths", side_effect=stop):
            args = SimpleNamespace(case_root=directory, mint="m", blocks_cache=None,
                                   reference_fingerprint="f", beta_slots=[])
            with self.assertRaisesRegex(RuntimeError, "stop before"):
                repair._produce_blocks(args)
        self.assertEqual(released, [True])

    def test_exploration_cache_retains_healthy_slot_support(self):
        function = next(node for node in ast.parse(Path(repair.__file__).read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name == "_produce_blocks")
        branch = next(node for node in ast.walk(function) if isinstance(node, ast.If)
                      and ast.unparse(node.test) == "args.blocks_cache")
        selected = repair._candidate_coverage_states(["DEFECT_CANDIDATE", "HEALTHY"], 10, [10])
        environment = dict(vars(repair), args=SimpleNamespace(blocks_cache="unit-cache"),
                           coverage_states=selected,
                           coverage_checked={"recomputed": {"states": ["DEFECT_CANDIDATE", "HEALTHY"]}},
                           from_slot=10, plan={"candidate_slots": [10]},
                           _cache_payloads=lambda ignored: [{"slot": 11}])
        exec(compile(ast.Module(body=branch.body, type_ignores=[]),
                     "<native-cache-branch>", "exec"), environment)
        self.assertEqual(environment["payloads"][0]["coverage_state"], "HEALTHY")

    def test_actual_producer_state_assignment_is_candidate_bounded(self):
        tree = ast.parse(Path(repair.__file__).read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_produce_blocks")
        assignment = next(n for n in ast.walk(fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "coverage_states" for t in n.targets))
        states = IndexOnlyStates()
        env = dict(vars(repair), from_slot=100, coverage_checked={"recomputed":{"states":states}}, plan={"candidate_slots":[100,140002995]})
        result = eval(compile(ast.Expression(assignment.value), "actual-production-assignment", "eval"), env)
        self.assertEqual(result, {100:"DEFECT_CANDIDATE",140002995:"HEALTHY"})
        self.assertEqual(states.lookups,[0,140002895])
    def test_outside_selected_slot_fails(self):
        for slot in [99,140002996,True,"100"]:
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                repair._candidate_coverage_states(IndexOnlyStates(),100,[slot])
    def test_main_only_computes_plan_for_plan_command(self):
        tree=ast.parse(Path(repair.__file__).read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="main")
        parents={child:node for node in ast.walk(fn) for child in ast.iter_child_nodes(node)}
        calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="_plan"]
        self.assertEqual(len(calls),1)
        n=calls[0]; ancestors=[]
        while n in parents: n=parents[n];ancestors.append(n)
        self.assertTrue(any(isinstance(n,ast.If) and ast.unparse(n.test)=="args.command == 'plan'" for n in ancestors))

class StreamingReplayTests(unittest.TestCase):
    def test_reconcile_summary_single_pass_and_exact(self):
        import hashlib, json
        from unittest.mock import patch
        import solana_exact_validate as exact
        zero="0x"+"0"*40
        rows=[(10,1,0,-1,zero,"alice",10**30),(11,2,0,-1,"alice","bob",3),(12,3,0,-1,"bob",zero,2)]
        reasons=[]
        with patch.object(exact,"_iter_edge_rows",return_value=iter(rows)), patch.object(exact,"_edge_rows",side_effect=AssertionError("full-list path forbidden")):
            result=exact._stream_reconcile_summary("unused",reasons)
        self.assertEqual(result["balances"],{"alice":10**30-3,"bob":1})
        self.assertEqual((result["minted"],result["burned"],result["count"]),(10**30,2,3))
        self.assertEqual(result["extrema"],{"first":{"slot":1,"ts":10},"last":{"slot":3,"ts":12}})
        expected=hashlib.sha256("".join(json.dumps(list(r),ensure_ascii=False)+"\n" for r in rows).encode()).hexdigest()
        self.assertEqual(result["digest"],expected)
    def test_empty_extrema_and_invalid_evidence_propagation(self):
        from unittest.mock import patch
        import solana_exact_validate as exact
        reasons=[]
        def invalid(path, out, label):
            out.append("invalid edge evidence")
            return iter(())
        with patch.object(exact,"_iter_edge_rows",side_effect=invalid):
            result=exact._stream_reconcile_summary("unused",reasons)
        self.assertIsNone(result["extrema"])
        self.assertEqual(result["count"],0)
        self.assertEqual(reasons,["invalid edge evidence"])
    def test_beta_reopens_edges_for_each_owner(self):
        import gzip,json,tempfile
        from sqd_repair_core import iter_edge_file, owner_activity
        rows=[(1,1,0,-1,"alice","bob",4),(2,2,0,-1,"bob","carol",2)]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"edges.gz"
            with gzip.open(path,"wt") as f:
                for row in rows:f.write(json.dumps(row)+"\n")
            for owner in ["alice","bob","carol"]:
                self.assertEqual(owner_activity(iter_edge_file(path),owner),owner_activity(rows,owner))

if __name__ == "__main__": unittest.main()
