#!/usr/bin/env python3
"""G3 F-06: alternate CSV collector protocol and formal-eligibility guards."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
EVM = HERE.parent / "evm"
sys.path.insert(0, str(EVM))


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class FakeRequests:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def Session(self):
        outer = self

        class Session:
            def post(self, *args, **kwargs):
                index = min(outer.calls, len(outer.responses) - 1)
                outer.calls += 1
                return FakeResponse(outer.responses[index])

        return Session()

    def get(self, *args, **kwargs):
        raise AssertionError("显式 --to-block 不应请求 finalized-head")


class FakePool:
    def attest(self):
        return None

    def call(self, method, params):
        return {"ok": True, "result": {}}


def capture_system_exit(func):
    code = 0
    out = io.StringIO()
    err = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = func()
        if isinstance(result, int):
            code = result
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue() + err.getvalue()


def run_sqd(root, responses, receipt_name):
    import fetch_sqd_evm

    out = root / f"{receipt_name}.csv"
    receipt = root / f"{receipt_name}.receipt.json"
    old_requests = fetch_sqd_evm.requests
    old_sleep = fetch_sqd_evm.time.sleep
    old_argv = sys.argv
    fetch_sqd_evm.requests = FakeRequests(responses)
    fetch_sqd_evm.time.sleep = lambda _seconds: None
    sys.argv = [
        "fetch_sqd_evm.py", "bsc", "10", "--token-addr", "0x" + "a" * 40,
        "--out", str(out), "--to-block", "12", "--sleep", "0", "--receipt", str(receipt),
    ]
    try:
        code, transcript = capture_system_exit(fetch_sqd_evm.main)
    finally:
        fetch_sqd_evm.requests = old_requests
        fetch_sqd_evm.time.sleep = old_sleep
        sys.argv = old_argv
    partials = list(root.glob(out.name + "*.partial"))
    return code, transcript, out, receipt, partials


def run_alchemy(root):
    import fetch_alchemy

    config = root / "alchemy.json"
    config.write_text(json.dumps({
        "alchemy_key": "test-key",
        "alchemy_network": "base-mainnet",
        "token": "0x" + "b" * 40,
    }), encoding="utf-8")
    out_dir = root / "alchemy-out"
    old_pool = fetch_alchemy.attested_rpc_pool
    old_sleep = fetch_alchemy.time.sleep
    old_argv = sys.argv
    fetch_alchemy.attested_rpc_pool = lambda *args, **kwargs: FakePool()
    fetch_alchemy.time.sleep = lambda _seconds: None
    sys.argv = [
        "fetch_alchemy.py", "--config", str(config), "--chain", "base",
        "--out-dir", str(out_dir), "--from-block", "10", "--to-block", "12",
    ]
    try:
        code, transcript = capture_system_exit(fetch_alchemy.main)
    finally:
        fetch_alchemy.attested_rpc_pool = old_pool
        fetch_alchemy.time.sleep = old_sleep
        sys.argv = old_argv
    return code, transcript, out_dir


def make_alchemy_receipt(root):
    import channels_preflight

    data = root / "alchemy-data.csv"
    data.write_text(
        "block,ts,tx,log_index,from,to,value_raw,block_hash\n"
        "10,2026-01-01T00:00:00,0xt,0,0xa,0xb,1,0xh\n",
        encoding="utf-8",
    )
    script = EVM / "fetch_alchemy.py"
    digest = channels_preflight._sha256_file(data)
    size = data.stat().st_size
    payload = {
        "schema": "evm-collector-run/v2",
        "status": "PASS",
        "collector": {"path": script.name, "sha256": channels_preflight._sha256_file(script)},
        "query": {
            "token": "0x" + "c" * 40,
            "query_schema": "erc20-transfer-fields/v2",
            "provider_url": "https://base-mainnet.g.alchemy.com/v2/redacted",
            "requested_from": 10,
            "requested_to": 13,
        },
        "completion": {"reason": "requested_bound_reached", "next_block": 13},
        "segments": [{
            "requested_from": 10,
            "requested_to": 13,
            "provider_next_block": 13,
            "output_prefix": {"size": size, "sha256": digest},
        }],
        "output": {
            "path": str(data.resolve()),
            "size": size,
            "sha256": digest,
            "rows": 1,
            "min_block": 10,
            "max_block": 10,
        },
    }
    receipt = root / "alchemy-native.json"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    return data, receipt, payload["query"]["token"]


def sqd_stream_row(number, *, logs=None, timestamp=1):
    """Build one structurally valid SQD stream row for offline protocol tests."""
    header = {"number": number, "timestamp": timestamp, "hash": "0xblock"}
    payload = {"header": header}
    if logs is not None:
        payload["logs"] = logs
    return json.dumps(payload)


def valid_sqd_log():
    return {
        "topics": [
            "0x" + "d" * 64,
            "0x" + "0" * 24 + "a" * 40,
            "0x" + "0" * 24 + "b" * 40,
        ],
        "data": "0x1",
        "transactionHash": "0x" + "c" * 64,
        "logIndex": "0",
    }


def main():
    checks = []
    skip_red = []

    def check(name, fn):
        try:
            fn()
        except Exception as exc:
            checks.append((name, False, f"{type(exc).__name__}: {exc}"))
        else:
            checks.append((name, True, ""))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        def r1():
            code, transcript, out, receipt, partials = run_sqd(root, [""], "sqd-empty")
            assert code != 0, f"empty SQD response exited {code}: {transcript!r}"
            assert not receipt.exists(), "empty SQD response signed a formal receipt"
            assert not out.exists() and partials, "new SQD output was not quarantined as .partial"

        check("R1 SQD empty response cannot complete or sign", r1)

        def r2():
            code, transcript, out_dir = run_alchemy(root)
            assert code != 0, f"missing transfers exited {code}: {transcript!r}"
            assert not (out_dir / "transfers_full.csv").exists(), "failed Alchemy output stayed publishable"
            assert list(out_dir.glob("transfers_full.csv*.partial")), "failed Alchemy output lacks .partial"

        check("R2 Alchemy empty result is a protocol error", r2)

        def r3():
            sentinel = json.dumps({"header": {"number": 10, "timestamp": 1, "hash": "0xh"}})
            code, transcript, out, receipt, partials = run_sqd(root, [sentinel, ""], "sqd-partial")
            assert code != 0, f"partially advanced SQD run exited {code}: {transcript!r}"
            assert not receipt.exists(), "partially advanced SQD run signed a receipt"
            assert not out.exists() and partials, "partially advanced SQD output lacks .partial"

        check("R3 SQD partial progress cannot hide a later anomaly", r3)

        def r4():
            sentinel = sqd_stream_row(10**9)
            code, transcript, out, receipt, partials = run_sqd(
                root, [sentinel], "sqd-overshoot-only"
            )
            assert code != 0, f"overshoot-only SQD response exited {code}: {transcript!r}"
            assert not receipt.exists(), "overshoot-only SQD response signed a receipt"
            assert not out.exists() and partials, "overshoot-only output lacks .partial"

        check("R4 SQD overshoot-only sentinel cannot complete or sign", r4)

        def r5():
            response = "\n".join((
                sqd_stream_row(11, logs=[valid_sqd_log()]),
                sqd_stream_row(10**9),
            ))
            code, transcript, out, receipt, partials = run_sqd(
                root, [response], "sqd-real-plus-overshoot"
            )
            assert code != 0, f"mixed real+overshoot SQD response exited {code}: {transcript!r}"
            assert not receipt.exists(), "mixed real+overshoot response signed a receipt"
            assert not out.exists() and partials, "mixed real+overshoot output lacks .partial"

        check("R5 SQD real row plus overshoot sentinel cannot complete or sign", r5)

        def r6():
            half_log = valid_sqd_log()
            half_log.pop("topics")
            response = sqd_stream_row(12, logs=[half_log])
            code, transcript, out, receipt, partials = run_sqd(
                root, [response], "sqd-half-log"
            )
            assert code != 0, f"half-log SQD response exited {code}: {transcript!r}"
            assert not receipt.exists(), "half-log SQD response signed a receipt"
            assert not out.exists() and partials, "half-log output lacks .partial"

        check("R6 SQD half-log response cannot complete or sign", r6)

        try:
            import fetch_sqd_evm
            parse_stream_response = fetch_sqd_evm.parse_stream_response
        except AttributeError:
            skip_red.append("SQD parse_stream_response missing")
        else:
            def sqd_parser():
                assert parse_stream_response("", 10, 12) == ([], None)
                assert parse_stream_response("  \n\t", 10, 12) == ([], None)
                row = sqd_stream_row(11)
                rows, last = parse_stream_response(row, 10, 12)
                assert rows == [] and last == 11
                for bad in ('{"header":{}}', "not-json"):
                    try:
                        parse_stream_response(bad, 10, 12)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(f"malformed SQD line accepted: {bad}")

                for invalid_number in (11.0, "11", 9, 13):
                    bad = sqd_stream_row(invalid_number)
                    try:
                        parse_stream_response(bad, 10, 12)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(
                            f"invalid/out-of-range SQD header.number accepted: {invalid_number!r}"
                        )

                invalid_logs = []
                missing_topics = valid_sqd_log()
                missing_topics.pop("topics")
                invalid_logs.append(missing_topics)
                only_two_topics = valid_sqd_log()
                only_two_topics["topics"] = only_two_topics["topics"][:2]
                invalid_logs.append(only_two_topics)
                short_topic = valid_sqd_log()
                short_topic["topics"][1] = "0x1234"
                invalid_logs.append(short_topic)
                bad_data = valid_sqd_log()
                bad_data["data"] = "0xzz"
                invalid_logs.append(bad_data)
                bad_log_index = valid_sqd_log()
                bad_log_index["logIndex"] = "not-an-int"
                invalid_logs.append(bad_log_index)
                for invalid_log in invalid_logs:
                    try:
                        parse_stream_response(
                            sqd_stream_row(11, logs=[invalid_log]), 10, 12
                        )
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(f"invalid SQD log accepted: {invalid_log}")

                for invalid_timestamp in ("bad", 1.5, True, 10**100):
                    try:
                        parse_stream_response(
                            sqd_stream_row(
                                11,
                                logs=[valid_sqd_log()],
                                timestamp=invalid_timestamp,
                            ),
                            10,
                            12,
                        )
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(
                            f"invalid SQD header.timestamp accepted: {invalid_timestamp!r}"
                        )

            check("P1 SQD stream parser protocol contract", sqd_parser)

        try:
            import fetch_alchemy
            validate_transfers_page = fetch_alchemy.validate_transfers_page
        except AttributeError:
            skip_red.append("Alchemy validate_transfers_page missing")
        else:
            valid_transfer = {
                "blockNum": "0xa", "hash": "0xt", "from": "0xa", "to": None,
                "uniqueId": "u1", "rawContract": {"value": "0x1"},
            }

            def alchemy_validator():
                for bad in (
                    {},
                    {"transfers": [{**valid_transfer, "rawContract": {}}]},
                    {"transfers": [{**valid_transfer, "rawContract": {"value": "bad-hex"}}]},
                    {"transfers": [{**valid_transfer, "blockNum": "0xd"}]},
                    {"transfers": [{**valid_transfer, "rawContract": {"value": "-0x5"}}]},
                    {"transfers": [{**valid_transfer, "rawContract": {"value": "0x_f"}}]},
                    {"transfers": [{**valid_transfer, "rawContract": {"value": " 0x5 "}}]},
                    {"transfers": [{**valid_transfer, "blockNum": "-0x5"}]},
                    {"transfers": [{**valid_transfer, "blockNum": "0x_f"}]},
                    {"transfers": [{**valid_transfer, "blockNum": " 0xa "}]},
                ):
                    try:
                        validate_transfers_page(bad, 10, 12, set())
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(f"invalid Alchemy page accepted: {bad}")
                assert validate_transfers_page({"transfers": []}, 10, 12, set()) == ([], None)
                seen = {"repeat"}
                try:
                    validate_transfers_page({"transfers": [], "pageKey": "repeat"}, 10, 12, seen)
                except ValueError:
                    pass
                else:
                    raise AssertionError("repeated Alchemy pageKey accepted")

            check("P2 Alchemy transfer page protocol contract", alchemy_validator)

        def deny_emitter():
            from csv_collector_receipt import emit_native_receipt

            data = root / "emitter.csv"
            data.write_text("block,ts,tx,log_index,from,to,value_raw,block_hash\n", encoding="utf-8")
            try:
                emit_native_receipt(
                    data, root / "emitter.json", EVM / "fetch_alchemy.py",
                    "0x" + "d" * 40, "https://provider", 10, 13, 13, fresh_output=True,
                )
            except ValueError:
                return
            raise AssertionError("receipt emitter accepted removed Alchemy collector")

        check("D1 receipt emitter rejects Alchemy", deny_emitter)

        def deny_emitter_overshoot():
            from csv_collector_receipt import emit_native_receipt

            data = root / "emitter-overshoot.csv"
            data.write_text(
                "block,ts,tx,log_index,from,to,value_raw,block_hash\n",
                encoding="utf-8",
            )
            try:
                emit_native_receipt(
                    data, root / "emitter-overshoot.json", EVM / "fetch_sqd_evm.py",
                    "0x" + "d" * 40, "https://provider", 10, 13, 14,
                    fresh_output=True,
                )
            except ValueError:
                return
            raise AssertionError("receipt emitter accepted provider frontier above requested bound")

        check("D1b receipt emitter rejects provider overshoot", deny_emitter_overshoot)

        def deny_preflight():
            import channels_preflight

            data, receipt, token = make_alchemy_receipt(root)
            try:
                channels_preflight._csv_collector_provenance(receipt, data, token, 10, 13)
            except channels_preflight.ChannelsPreflightError:
                return
            raise AssertionError("channels preflight accepted removed Alchemy collector")

        check("D2 channels preflight rejects Alchemy receipt", deny_preflight)

        def deny_cli_receipt():
            import fetch_alchemy

            old_argv = sys.argv
            sys.argv = [
                "fetch_alchemy.py", "--config", str(root / "does-not-exist.json"),
                "--chain", "base", "--receipt", str(root / "forbidden.json"),
            ]
            try:
                code, _transcript = capture_system_exit(fetch_alchemy.main)
            finally:
                sys.argv = old_argv
            assert code == 2, f"--receipt must be rejected by argparse, got {code}"

        check("D3 Alchemy CLI rejects --receipt", deny_cli_receipt)

        def receipt_help_is_removed():
            import fetch_alchemy

            old_argv = sys.argv
            sys.argv = ["fetch_alchemy.py", "--help"]
            try:
                code, transcript = capture_system_exit(fetch_alchemy.main)
            finally:
                sys.argv = old_argv
            assert code == 0, f"Alchemy --help exited {code}"
            assert "已除名：Alchemy 无 provider 侧完成证据，不支持正式 receipt，仅探索采集" \
                in transcript
            assert "成功收尾后写正式 evm-collector-run/v2" not in transcript

        check("D4 Alchemy --receipt help states removal", receipt_help_is_removed)

    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name}" + (f" -- {detail}" if detail else ""))
    for detail in skip_red:
        print(f"SKIP-RED: {detail}")
    failed = sum(not passed for _name, passed, _detail in checks)
    print(f"SUMMARY: {len(checks) - failed} passed, {failed} failed, {len(skip_red)} skip-red")
    return 1 if failed or skip_red else 0


if __name__ == "__main__":
    raise SystemExit(main())
