#!/usr/bin/env python3
"""阵营 spec 共享校验（F-05，2026-08-13 六视角修复批 C）。

背景：camps 定义文档写明"阵营互斥（一地址只归一个阵营）"，但四个重放入口
（evm/replay_pass2.py、evm/replay_duck.py、solana/replay_edges.py、
solana/build_evolution.py）此前各自手写 `addr2camp[addr] = camp` 式装配——
同一地址配进两个阵营时被后出现的键静默覆盖，交换 JSON 键顺序即可改变归属，
且各阵营加总仍是 100%，图形外观完全正常（静默传播级错误）。

本模块是四入口共用的唯一校验实现（四份手抄条件必然再漂移，故收敛到一处）：
  - validate_camp_spec()：{阵营名: [地址,...]} 形态。先按链规范化（EVM 一律
    小写；Solana base58 原样——base58 大小写敏感，不得改写），再在**原始列表**
    上查重（set() 化之前，否则同营内重复被 set 静默吞掉）：同阵营内重复与
    跨阵营重复一律硬拒 exit 2。
  - load_addr_camp_json()：{地址: 阵营} 形态（build_evolution 用）。JSON 源文本
    里的重复键在 Python 解析后永远查不到（后键静默覆盖前键），必须用
    object_pairs_hook 在解析层拒收。

边界（by design，不在本模块管辖）：
  - 互斥只属 camps 域；entities 域一个地址可属多个实体（图 2 实体线与阵营
    本来就允许重叠），不查重。
  - "销毁"阵营由引擎自动补列（烧入 0x0 的量），spec 里可不配置。
"""
from __future__ import annotations

import json
import sys


def _fail(msg: str):
    print(f"[camp-spec] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _normalize(addr, chain_family: str, camp: str, source_label: str) -> str:
    if not isinstance(addr, str) or not addr.strip():
        _fail(f"{source_label} 阵营「{camp}」含非字符串/空地址: {addr!r}")
    addr = addr.strip()
    if chain_family == "evm":
        return addr.lower()
    if chain_family == "solana":
        return addr  # base58 大小写敏感，原样保留
    _fail(f"chain_family 只认 evm/solana，收到 {chain_family!r}")


def validate_camp_spec(camps, *, chain_family: str, source_label: str = "camps"):
    """校验 {阵营名: [地址,...]} 形态的阵营定义，返回规范化后的同形 dict（保序）。

    查重必须在原始列表上、规范化之后做：
      - 在 set() 化之前查：同阵营内的重复（含大小写变体）才抓得到；
      - 规范化之后查：EVM 的 0xAbC 与 0xabc 是同一地址，先 lower 再比，
        否则大小写变体绕过精确匹配（F-05 回归必含大小写变体用例的原因）。
    任何重复（同营内/跨营）→ 硬拒 exit 2。
    """
    if not isinstance(camps, dict):
        _fail(f"{source_label} 必须是 {{阵营名: [地址...]}} 对象，收到 {type(camps).__name__}")
    normalized = {}
    owner = {}  # 规范化地址 -> 首见阵营
    for camp, addrs in camps.items():
        if not isinstance(camp, str) or not camp.strip():
            _fail(f"{source_label} 含非法阵营名: {camp!r}")
        if not isinstance(addrs, list):
            _fail(f"{source_label} 阵营「{camp}」的值必须是地址列表，"
                  f"收到 {type(addrs).__name__}")
        out = []
        for raw in addrs:
            addr = _normalize(raw, chain_family, camp, source_label)
            if addr in owner:
                # 单点查重覆盖两种重复（变异自检要求每道检查独立可命中，
                # 不留并行冗余分支），消息区分同营内与跨营
                if owner[addr] == camp:
                    _fail(f"{source_label} 阵营「{camp}」内重复地址 {addr}"
                          f"（原文 {raw!r}）——阵营互斥且成员唯一，先修 spec 再重放")
                _fail(f"{source_label} 地址 {addr} 同时归入阵营"
                      f"「{owner[addr]}」与「{camp}」（原文 {raw!r}）——阵营互斥，"
                      f"JSON 键序决定归属是静默错误，先修 spec 再重放")
            owner[addr] = camp
            out.append(addr)
        normalized[camp] = out
    return normalized


def load_addr_camp_json(path, *, chain_family: str = "solana",
                        source_label: str | None = None):
    """读 {地址: 阵营名} 形态的 JSON（build_evolution 的 entity_camps.json）。

    JSON 文本中的重复键（同址两阵营，或同址同阵营写两遍）在解析层用
    object_pairs_hook 拒收——解析完成后 dict 里永远只剩最后一个，查不到。
    顶层解析后再反转成 {阵营: [地址]} 过一遍 validate_camp_spec，与其余
    三族入口同一深度（结构与规范化口径一致）。
    """
    label = source_label or str(path)

    def _hook(pairs):
        seen = set()
        out = {}
        for key, value in pairs:
            if key in seen:
                _fail(f"{label} JSON 重复键 {key!r}——同一地址写了两遍"
                      f"（后值会静默覆盖前值），先修文件再重放")
            seen.add(key)
            out[key] = value
        return out

    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh, object_pairs_hook=_hook)
    if not isinstance(obj, dict):
        _fail(f"{label} 必须是 {{地址: 阵营名}} 对象")
    inverted = {}
    for addr, camp in obj.items():
        if not isinstance(camp, str) or not camp.strip():
            _fail(f"{label} 地址 {addr} 的阵营名非法: {camp!r}")
        inverted.setdefault(camp, []).append(addr)
    validate_camp_spec(inverted, chain_family=chain_family, source_label=label)
    return obj
