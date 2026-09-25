# repair-20260925-label-blind-leak

**起因**：PYTHIA 案（2026-09-25）A3 四通道采集时，官方 `label_lookup.py --blind-serial` 公共输出里出现 1 行 serial=False 但 risk_flags=serial-offender 的混合行，案内泄露检测判 `BLIND_OUTPUT_INTEGRITY_FAILED`。根因：CLI 封存只看 `serial`（= category==serial-actor），curation 改类别后风险标记与来源仍留在公共输出。

**单序**：W1（CLI 封存判据改为结构化标记精确匹配 + 集成测试 + 9.2.1）。

**后续单候选（复核 r1 发现，本工程不动）**：
- `scripts/evm/analyze_holdings.py` 192–224：同类漏封（仅 serial=True 跳过）。
- `scripts/solana/replay_edges.py` 64–79、`scripts/solana/build_evolution.py` 107–121、`scripts/evm/cluster.py` 200–242、`scripts/report/entity_identity_gate.py` 334–361：盲化期名称/类别/来源直出，无盲化判断。
- `labels_resolver.py` 的 `get/policy/resolve_file` 本身不盲化；`is_serial()` 是否也应认风险标记待议。
- `--unseal` 与盲化参数同时给出时的优先级未写清。

**裁决记录**：混合行整行封存（盲化承诺优先于设施便利，A4 揭盲恢复）；`serial` 定义不改。
