#!/usr/bin/env python3
"""进程内异步网络层（B5，2026-07-22）——替代"spawn 上百 curl 子进程"的批量请求模式。

买的是稳定性不是速度（codex 修正预期，@CX 方案定位）：
  - 根治 exit 144：不再产生可被沙箱连带清理的 curl 子进程树
  - 精确限速：异步令牌桶贴着配额跑（如 Helius 10 RPS），比线程池+sleep 精确
  - 统一重试：tenacity 指数退避+抖动，替代到处手写的 429/504 循环
  - msgspec 解析大 JSON 响应（比 stdlib 快数倍），失败自动回退 stdlib

适用边界：JSON API / JSON-RPC 批量调用。**Cloudflare/浏览器指纹敏感的站点仍走本库登记的
curl_json 后端**（bscscan 网页、GT、SQD stream 等），不得由业务脚本私搭 subprocess curl。
新脚本的批量 HTTP 一律 import 本库；
在役老脚本不强改（改动须走等价对表）。

curl_json 只判断传输、HTTP 状态与 JSON/NDJSON 解码是否成功；“成功响应里的空数据是否
可信”属于 adapter 的分页终止/区间覆盖判断，本层绝不替业务层作 EMPTY_OK 裁决。

用法（同步入口，内部起事件循环，调用方无需懂 async）:
    from net import RpcPool, http_get_many
    pool = RpcPool("https://rpc...", rps=10, concurrency=8, headers={...})
    results = pool.call_many([("eth_getCode", [addr, "latest"]), ...])
    # results[i] = {"ok": True, "result": ...} 或 {"ok": False, "error": "..."}

    pages = http_get_many([url1, url2, ...], rps=5)     # 通用 GET JSON 批量
（来源：B5 网络层改造，2026-07-22）"""
import asyncio
import json as _stdjson
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

import httpx
import msgspec
from tenacity import (AsyncRetrying, retry_if_exception, stop_after_attempt,
                      wait_random_exponential)

# HTTP 状态码：这些值得重试（限流/网关抖动）；4xx 其余不重试
RETRYABLE_STATUS = {429, 500, 502, 503, 504, 408}
# JSON-RPC 错误码：限流/节点过载类可重试；其余（方法不存在/参数错）不重试
RETRYABLE_RPC = {-32005, -32603, -32000}
# Machine-readable registration consumed by invariant_scan.py.
REGISTERED_TRANSPORT_BACKEND = "curl"


@dataclass(frozen=True)
class Result:
    """Explicit transport result; callers must branch on ``.ok``."""

    ok: bool
    value: Any = None
    error: Any = None

    def __bool__(self):
        raise TypeError("Result has no truth value; test result.ok explicitly")


def _curl_error(category, message, *, returncode=None):
    error = {"category": category, "message": str(message)[:500]}
    if returncode is not None:
        error["returncode"] = int(returncode)
    return Result(ok=False, error=error)


def _decode_curl_json(raw: str):
    """Decode one JSON value or an all-valid newline-delimited JSON stream."""
    try:
        return _stdjson.loads(raw)
    except (TypeError, ValueError) as single_error:
        lines = [line for line in raw.splitlines() if line.strip()]
        if len(lines) <= 1:
            raise single_error
        values = []
        for line in lines:
            values.append(_stdjson.loads(line))
        return values


def curl_json(url, *, post_json=None, headers=None, timeout=45.0, attempts=4) -> Result:
    """Run the registered curl backend and return an explicit :class:`Result`.

    ``curl --fail-with-body`` maps HTTP failures to return code 22.  Other non-zero
    return codes are transport failures.  Empty, truncated, or otherwise invalid
    JSON/NDJSON is a decode failure.  Business adapters remain responsible for
    proving whether a successfully decoded empty value covers their requested range.
    """
    if not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be positive")
    if headers is not None and not hasattr(headers, "items"):
        raise TypeError("headers must be a mapping")

    command = ["curl", "--silent", "--show-error", "--fail-with-body",
               "--max-time", str(float(timeout))]
    header_map = dict(headers or {})
    if post_json is not None:
        command.extend(["--request", "POST"])
        if not any(str(key).lower() == "content-type" for key in header_map):
            header_map["Content-Type"] = "application/json"
    for key, value in header_map.items():
        command.extend(["--header", f"{key}: {value}"])
    if post_json is not None:
        command.extend(["--data-binary", _stdjson.dumps(
            post_json, ensure_ascii=False, separators=(",", ":"))])
    command.append(str(url))

    last = None
    for attempt in range(attempts):
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=float(timeout) + 10.0)
        except (OSError, subprocess.TimeoutExpired) as exc:
            last = _curl_error("transport", f"{type(exc).__name__}: {exc}")
        else:
            if completed.returncode != 0:
                category = "http_status" if completed.returncode == 22 else "transport"
                detail = completed.stderr.strip() or f"curl exited {completed.returncode}"
                last = _curl_error(category, detail, returncode=completed.returncode)
            elif not completed.stdout.strip():
                last = _curl_error("decode", "curl returned empty stdout")
            else:
                try:
                    value = _decode_curl_json(completed.stdout)
                except (TypeError, ValueError) as exc:
                    last = _curl_error("decode", f"invalid JSON response: {exc}")
                else:
                    return Result(ok=True, value=value)
        if attempt + 1 < attempts:
            time.sleep(min(2 ** attempt, 8))
    return last


def _decode(raw: bytes):
    """msgspec 快路径，异常回退 stdlib（两者都失败才抛）。"""
    try:
        return msgspec.json.decode(raw)
    except msgspec.DecodeError:
        return _stdjson.loads(raw)


class _Bucket:
    """异步令牌桶：所有并发任务共享一个桶，贴配额限速。"""

    def __init__(self, rps: float, burst: float | None = None):
        self.rate = float(rps)
        self.cap = float(burst if burst is not None else max(1.0, rps))
        self.tokens = self.cap
        self.ts = time.monotonic()
        self.lock = asyncio.Lock()

    async def take(self):
        while True:
            async with self.lock:
                now = time.monotonic()
                self.tokens = min(self.cap, self.tokens + (now - self.ts) * self.rate)
                self.ts = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                need = (1.0 - self.tokens) / self.rate
            await asyncio.sleep(need)


class _RetryableHTTP(Exception):
    pass


def _should_retry(e: BaseException) -> bool:
    return isinstance(e, (_RetryableHTTP, httpx.TransportError, httpx.TimeoutException))


async def _request_json(client, bucket, method, url, *, json_body=None, attempts=6):
    """单请求：限速→请求→重试策略→解析。抛出最终异常由调用方兜底。"""
    async for att in AsyncRetrying(
            retry=retry_if_exception(_should_retry),
            wait=wait_random_exponential(multiplier=1, max=30),
            stop=stop_after_attempt(attempts), reraise=True):
        with att:
            await bucket.take()
            r = await client.request(method, url, json=json_body)
            if r.status_code in RETRYABLE_STATUS:
                raise _RetryableHTTP(f"HTTP {r.status_code}")
            r.raise_for_status()
            return _decode(r.content)


class RpcPool:
    """JSON-RPC 批量调用池（同步入口）。逐笔并发（不是 JSON-RPC batch——
    Helius 免费层禁 batch(-32403)，逐笔并发是通用兼容形态）。"""

    def __init__(self, url, *, rps=8.0, concurrency=8, headers=None,
                 timeout=45.0, attempts=6, browser_ua=False):
        self.url = url
        self.rps, self.concurrency = rps, concurrency
        self.timeout, self.attempts = timeout, attempts
        self.headers = dict(headers or {})
        if browser_ua:  # robinhood 链 RPC 的 WAF 坑：python UA 被 403
            self.headers.setdefault(
                "User-Agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

    async def _one(self, client, bucket, sem, i, method, params):
        async with sem:
            body = {"jsonrpc": "2.0", "id": i, "method": method, "params": params}
            try:
                j = await _request_json(client, bucket, "POST", self.url,
                                        json_body=body, attempts=self.attempts)
            except Exception as e:
                return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}
            err = j.get("error") if isinstance(j, dict) else None
            if err:
                code = err.get("code")
                if code in RETRYABLE_RPC:
                    # RPC 层限流：温和等待后单次重打（tenacity 管不到成功 HTTP 里的错误对象）
                    await asyncio.sleep(2)
                    try:
                        j = await _request_json(client, bucket, "POST", self.url,
                                                json_body=body, attempts=self.attempts)
                        err = j.get("error") if isinstance(j, dict) else None
                    except Exception as e:
                        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}
                if err:
                    return {"ok": False, "error": f"rpc {err.get('code')}: {str(err.get('message'))[:120]}"}
            return {"ok": True, "result": j.get("result")}

    async def _run(self, calls, progress):
        bucket = _Bucket(self.rps)
        sem = asyncio.Semaphore(self.concurrency)
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            tasks = [self._one(client, bucket, sem, i, m, p)
                     for i, (m, p) in enumerate(calls)]
            out = await asyncio.gather(*tasks)  # gather 保原序
            if progress:
                nb = sum(1 for r in out if not r["ok"])
                print(f"[net] {len(out)} 调用完成, 失败 {nb}", file=sys.stderr, flush=True)
            return list(out)

    def call_many(self, calls, progress=True):
        """calls: [(method, params), ...] -> 同序 [{ok,result|error}, ...]"""
        return asyncio.run(self._run(calls, progress))

    def call(self, method, params):
        return self.call_many([(method, params)], progress=False)[0]


def http_get_many(urls, *, rps=5.0, concurrency=6, headers=None,
                  timeout=45.0, attempts=5, browser_ua=False):
    """通用 GET JSON 批量：-> 同序 [{ok,data|error}, ...]"""
    hdrs = dict(headers or {})
    if browser_ua:
        hdrs.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

    async def one(client, bucket, sem, url):
        async with sem:
            try:
                j = await _request_json(client, bucket, "GET", url, attempts=attempts)
                return {"ok": True, "data": j}
            except Exception as e:
                return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}

    async def run():
        bucket = _Bucket(rps)
        sem = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(headers=hdrs, timeout=timeout) as client:
            return list(await asyncio.gather(*[one(client, bucket, sem, u) for u in urls]))

    return asyncio.run(run())
