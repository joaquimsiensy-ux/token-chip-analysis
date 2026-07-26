#!/usr/bin/env python3
"""全 key 健康巡检（C3 密钥治理，3.19）——对 ~/.claude/api-keys.md 登记的在役 key
逐一做**最小且不耗付费额度**的探测，输出五分类摘要；launchd 每周一 10:00 自动跑。

探测清单（全部免费/不占付费额度；来源注释在各探测函数）：
  hypersync  GET /height（Starter key，~/.config/hypersync/token）
  alchemy    eth_blockNumber @ base-mainnet（走 clash 代理——*.g.alchemy.com 被墙）
  drpc       eth_blockNumber（429=限流也算认证有效，登记文件实测语义）
  etherscan  V2 chainid=1 proxy.eth_blockNumber（走代理；免费层 10 万次/天，1 次无感）
  xapi       GET /2/usage/tweets（官方注明不占读额度；走代理；402=credits 耗尽单列）
  dune       GET query/7999252/results?limit=1（GET results 不耗 credits）
  helius     getHealth（免费 RPC 方法）
  gmgn       gmgn-cli token info 轻查询（免费 key、Ed25519 签名由 CLI 完成）
  firecrawl  GET /v2/team/credit-usage（登记免报备端点；key 从 ~/.zshrc 提取）
  bigquery   OAuth refresh_token 刷新（POST token_uri，免费、非交互不弹浏览器；走代理）
未覆盖：SQD（公共端点不认证无从探测）、Vybe（无已知免额度端点）——报告注明。

分类口径：ok / auth_invalid / quota_exhausted / service_error / network_error
  （+ skipped=没法免额度探测或 key 源缺失）；429 归 ok 加注"限流（认证未被拒）"。

输出：~/.cache/chip-analysis/probe_report.json + stdout 人读摘要（每 key 一行）。
**任何输出/报告/异常信息都经 sanitize() 脱敏——key 明文绝不落盘/上屏**。

用法：
  python3 probe_keys.py [--feishu] [--timeout 15]
  --feishu：存在异常（skipped 不算）才推送摘要到 ~/.config/feishu/webhook；全 ok 静默
（来源：C3 密钥治理，2026-07-22）"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

import requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
MD_PATH = os.path.expanduser(
    os.environ.get("CHIP_API_KEYS_FILE", "~/.claude/api-keys.md")
)
REPORT_DIR = os.path.expanduser("~/.cache/chip-analysis")
GMGN_CLI = os.path.expanduser("~/.npm-global/bin/gmgn-cli")
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"  # gmgn 探测用的常青标的

_SECRETS = []  # 运行中登记的所有 key 明文，sanitize 全量替换


def _reg(secret):
    if secret and secret not in _SECRETS:
        _SECRETS.append(secret)
    return secret


def sanitize(text):
    """把已知 key 明文从任意字符串里抹掉（异常消息常含带 key 的 URL）。"""
    s = str(text)
    for sec in _SECRETS:
        s = s.replace(sec, "<REDACTED>")
    return s


def read_file_key(path):
    try:
        return _reg(open(os.path.expanduser(path)).read().strip()) or None
    except OSError:
        return None


def key_from_md(section_kw, line_re):
    """api-keys.md 按 '## ' 切节，节标题含 section_kw 的节内取 line_re 第一捕获组。"""
    try:
        md = open(MD_PATH).read()
    except OSError:
        return None
    for sec in md.split("\n## "):
        head = sec.split("\n", 1)[0]
        if section_kw in head:
            m = re.search(line_re, sec)
            if m:
                return _reg(m.group(1))
    return None


def classify_http(status, ok_note=""):
    if status == 200:
        return "ok", ok_note
    if status in (401, 403):
        return "auth_invalid", f"HTTP {status}"
    if status == 402:
        return "quota_exhausted", "HTTP 402（credits 耗尽）"
    if status == 429:
        return "ok", "HTTP 429 限流（认证未被拒）"
    if status >= 500:
        return "service_error", f"HTTP {status}"
    return "service_error", f"HTTP {status}（意外状态码）"


def http_probe(method, url, use_proxy=False, timeout=15, **kw):
    """统一 HTTP 探测：返回 (response|None, err_note)。网络类异常归 err_note。"""
    try:
        r = requests.request(method, url, timeout=timeout,
                             proxies=PROXY if use_proxy else None, **kw)
        return r, None
    except requests.exceptions.RequestException as e:
        note = f"{type(e).__name__}: {sanitize(e)}"[:200]
        if use_proxy:
            note += "（走 clash 代理 127.0.0.1:7897——先确认 clash 在跑）"
        return None, note


# ---------------- 各服务探测（返回 dict） ----------------

def probe_hypersync(t):
    key = read_file_key("~/.config/hypersync/token")
    if not key:
        return {"category": "skipped", "note": "~/.config/hypersync/token 缺失"}
    r, err = http_probe("GET", "https://eth.hypersync.xyz/height",
                        headers={"Authorization": f"Bearer {key}"}, timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    cat, note = classify_http(r.status_code)
    if cat == "ok" and r.status_code == 200:
        try:
            note = f"height={r.json().get('height')}"
        except ValueError:
            pass
    return {"category": cat, "note": note}


def probe_alchemy(t):
    key = key_from_md("Alchemy", r"Key（现役[^`]*`([A-Za-z0-9_\-]{15,})`")
    if not key:
        return {"category": "skipped", "note": "api-keys.md 里没提取到现役 key"}
    r, err = http_probe("POST", f"https://base-mainnet.g.alchemy.com/v2/{key}",
                        json={"jsonrpc": "2.0", "id": 1,
                              "method": "eth_blockNumber", "params": []},
                        use_proxy=True, timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    cat, note = classify_http(r.status_code)
    if cat == "ok" and r.status_code == 200:
        j = r.json()
        if j.get("error"):
            return {"category": "auth_invalid",
                    "note": sanitize(j["error"].get("message", ""))[:120]}
        note = f"base blockNumber={int(j.get('result', '0x0'), 16)}"
    return {"category": cat, "note": note}


def probe_drpc(t):
    key = key_from_md("dRPC", r"\*\*Key\*\*：`([A-Za-z0-9_\-]{30,})`")
    if not key:
        return {"category": "skipped", "note": "api-keys.md 里没提取到 key"}
    r, err = http_probe("POST", f"https://lb.drpc.org/ogrpc?network=ethereum&dkey={key}",
                        json={"jsonrpc": "2.0", "id": 1,
                              "method": "eth_blockNumber", "params": []}, timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    # 登记实测语义：真 key 429（限流）、假 key 403（invalid）
    cat, note = classify_http(r.status_code)
    if cat == "ok" and r.status_code == 200:
        note = "eth_blockNumber 通"
    return {"category": cat, "note": note}


def probe_etherscan(t):
    key = key_from_md("Etherscan", r"\*\*Key\*\*：`([A-Z0-9]{30,40})`")
    if not key:
        return {"category": "skipped", "note": "api-keys.md 里没提取到 key"}
    r, err = http_probe(
        "GET", "https://api.etherscan.io/v2/api",
        params={"chainid": 1, "module": "proxy", "action": "eth_blockNumber",
                "apikey": key}, use_proxy=True, timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    if r.status_code != 200:
        cat, note = classify_http(r.status_code)
        return {"category": cat, "note": note}
    j = r.json()
    body = sanitize(json.dumps(j, ensure_ascii=False))
    if "Invalid API Key" in body:
        return {"category": "auth_invalid", "note": "Invalid API Key"}
    if "rate limit" in body.lower():
        return {"category": "ok", "note": "限流（认证未被拒）"}
    if j.get("result"):
        return {"category": "ok", "note": "eth_blockNumber 通"}
    return {"category": "service_error", "note": body[:120]}


def probe_xapi(t):
    key = key_from_md("X / Twitter", r"Key（Bearer[^`]*`([^`]{40,})`")
    if not key:
        return {"category": "skipped", "note": "api-keys.md 里没提取到 Bearer"}
    r, err = http_probe("GET", "https://api.x.com/2/usage/tweets",
                        headers={"Authorization": f"Bearer {key}"},
                        use_proxy=True, timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    cat, note = classify_http(r.status_code)
    if cat == "ok" and r.status_code == 200:
        try:
            d = r.json().get("data", {})
            note = (f"月读 {d.get('project_usage')}/{d.get('project_cap')}")
        except ValueError:
            pass
    return {"category": cat, "note": note}


def probe_dune(t):
    key = read_file_key("~/.config/dune/api-key")
    if not key:
        return {"category": "skipped", "note": "~/.config/dune/api-key 缺失"}
    r, err = http_probe("GET", "https://api.dune.com/api/v1/query/7999252/results",
                        params={"limit": 1},
                        headers={"X-Dune-API-Key": key}, timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    cat, note = classify_http(r.status_code)
    if cat == "ok" and r.status_code == 200:
        note = "labels query results 可读（不耗 credits）"
    return {"category": cat, "note": note}


def probe_helius(t):
    key = read_file_key("~/.config/helius/api-key")
    if not key:
        return {"category": "skipped", "note": "~/.config/helius/api-key 缺失"}
    r, err = http_probe("POST", f"https://mainnet.helius-rpc.com/?api-key={key}",
                        json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                        timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    cat, note = classify_http(r.status_code)
    if cat == "ok" and r.status_code == 200:
        note = f"getHealth={r.json().get('result', '?')}"
    return {"category": cat, "note": note}


def probe_gmgn(t):
    envf = os.path.expanduser("~/.config/gmgn/.env")
    if not os.path.exists(envf):
        return {"category": "skipped", "note": "~/.config/gmgn/.env 缺失"}
    for line in open(envf):
        if line.startswith("GMGN_API_KEY="):
            _reg(line.split("=", 1)[1].strip())
    if not os.path.exists(GMGN_CLI):
        return {"category": "skipped", "note": "gmgn-cli 未安装"}
    try:
        p = subprocess.run([GMGN_CLI, "token", "info", "--chain", "bsc",
                            "--address", WBNB, "--raw"],
                           capture_output=True, text=True, timeout=max(t, 30))
    except subprocess.TimeoutExpired:
        return {"category": "network_error", "note": "gmgn-cli 超时"}
    out = sanitize(p.stdout + p.stderr)
    if p.returncode == 0 and ("price" in out or "symbol" in out.lower()):
        return {"category": "ok", "note": "token info 轻查询通（免费 key）"}
    low = out.lower()
    if any(w in low for w in ("unauthorized", "401", "invalid key", "signature")):
        return {"category": "auth_invalid", "note": out[:120]}
    if any(w in low for w in ("timeout", "econn", "network", "enotfound")):
        return {"category": "network_error", "note": out[:120]}
    return {"category": "service_error", "note": out[:150] or f"退出码 {p.returncode}"}


def probe_firecrawl(t):
    key = None
    try:
        zr = open(os.path.expanduser("~/.zshrc")).read()
        m = re.search(r"FIRECRAWL_API_KEY=[\"']?(fc-[0-9a-f]{32})", zr)
        if m:
            key = _reg(m.group(1))
    except OSError:
        pass
    if not key:
        key = key_from_md("Firecrawl", r"Key（现役[^`]*`(fc-[0-9a-f]{32})`")
    if not key:
        return {"category": "skipped", "note": "~/.zshrc 与 api-keys.md 均没提取到 key"}
    hdr = {"Authorization": f"Bearer {key}"}
    r, err = http_probe("GET", "https://api.firecrawl.dev/v2/team/credit-usage",
                        headers=hdr, timeout=t)
    if err:  # 直连失败换代理再试一次
        r, err = http_probe("GET", "https://api.firecrawl.dev/v2/team/credit-usage",
                            headers=hdr, use_proxy=True, timeout=t)
        if err:
            return {"category": "network_error", "note": err}
    if r.status_code == 404:  # v2 端点不在了就退 v1
        r, err = http_probe("GET", "https://api.firecrawl.dev/v1/team/credit-usage",
                            headers=hdr, timeout=t)
        if err:
            return {"category": "network_error", "note": err}
    cat, note = classify_http(r.status_code)
    if cat == "ok" and r.status_code == 200:
        try:
            d = r.json().get("data", {})
            note = f"剩余 credits={d.get('remainingCredits', d.get('remaining_credits'))}"
        except ValueError:
            pass
    return {"category": cat, "note": note}


def probe_bigquery(t):
    """OAuth refresh_token 刷新（免费、非交互）——不 import SDK、绝不弹浏览器。"""
    cred_path = os.path.expanduser("~/.config/pydata/pydata_google_credentials.json")
    if not os.path.exists(cred_path):
        return {"category": "skipped", "note": "OAuth 凭据缓存缺失（首跑 fetch_bigquery 授权）"}
    try:
        c = json.load(open(cred_path))
    except (OSError, json.JSONDecodeError) as e:
        return {"category": "skipped", "note": f"凭据文件读不出: {type(e).__name__}"}
    for f in ("client_secret", "refresh_token"):
        _reg(c.get(f))
    r, err = http_probe("POST", c.get("token_uri", "https://oauth2.googleapis.com/token"),
                        data={"client_id": c.get("client_id"),
                              "client_secret": c.get("client_secret"),
                              "refresh_token": c.get("refresh_token"),
                              "grant_type": "refresh_token"},
                        use_proxy=True, timeout=t)
    if err:
        return {"category": "network_error", "note": err}
    if r.status_code == 200:
        tok = r.json().get("access_token")
        if tok:
            _reg(tok)
        return {"category": "ok", "note": "refresh_token 换 access_token 成功"}
    body = sanitize(r.text)[:150]
    if "invalid_grant" in body:
        return {"category": "auth_invalid",
                "note": "invalid_grant（凭据已吊销/过期，需重跑 fetch_bigquery 授权）"}
    cat, note = classify_http(r.status_code)
    return {"category": cat, "note": f"{note} {body}"[:150]}


PROBES = [
    ("hypersync", probe_hypersync),
    ("alchemy", probe_alchemy),
    ("drpc", probe_drpc),
    ("etherscan", probe_etherscan),
    ("xapi", probe_xapi),
    ("dune", probe_dune),
    ("helius", probe_helius),
    ("gmgn", probe_gmgn),
    ("firecrawl", probe_firecrawl),
    ("bigquery", probe_bigquery),
]
NOT_COVERED = {"sqd": "公共端点不认证，key 无从探测",
               "vybe": "无已知免额度端点，跳过"}


def push_feishu(text):
    try:
        hook = open(os.path.expanduser("~/.config/feishu/webhook")).read().strip()
    except OSError:
        print("[feishu] webhook 文件缺失，跳过推送", file=sys.stderr)
        return False
    try:
        r = requests.post(hook, json={"msg_type": "text",
                                      "content": {"text": text}}, timeout=10)
        return r.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"[feishu] 推送失败: {type(e).__name__}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser(description="全 key 健康巡检（免额度探测）")
    ap.add_argument("--feishu", action="store_true",
                    help="有异常才推送摘要到飞书（全 ok 静默）")
    ap.add_argument("--timeout", type=float, default=15.0)
    a = ap.parse_args()

    results = {}
    for name, fn in PROBES:
        try:
            res = fn(a.timeout)
        except Exception as e:  # 单探测崩溃不塌整轮
            res = {"category": "service_error",
                   "note": f"探测器异常 {type(e).__name__}: {sanitize(e)}"[:150]}
        res["note"] = sanitize(res.get("note", ""))
        results[name] = res
        print(f"{name:10s} {res['category']:16s} {res['note']}", flush=True)
    for name, why in NOT_COVERED.items():
        results[name] = {"category": "skipped", "note": why}
        print(f"{name:10s} {'skipped':16s} {why}", flush=True)

    bad = {k: v for k, v in results.items()
           if v["category"] not in ("ok", "skipped")}
    os.makedirs(REPORT_DIR, exist_ok=True)
    rpath = os.path.join(REPORT_DIR, "probe_report.json")
    report = {"ts": datetime.datetime.now(datetime.timezone.utc)
              .strftime("%Y-%m-%dT%H:%M:%SZ"),
              "results": results,
              "summary": {"total": len(results), "bad": len(bad),
                          "bad_services": sorted(bad)}}
    tmp = rpath + ".tmp"
    json.dump(report, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, rpath)
    print(f"[report] {rpath}  异常 {len(bad)} 项", flush=True)

    if bad and a.feishu:
        lines = [f"[key 巡检] {len(bad)} 项异常（{report['ts']}）"]
        lines += [f"- {k}: {v['category']} {v['note']}"[:120] for k, v in bad.items()]
        lines.append("详情: ~/.cache/chip-analysis/probe_report.json")
        push_feishu("\n".join(lines))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
