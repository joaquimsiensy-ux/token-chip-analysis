#!/usr/bin/env python3
"""跨进程文件锁（C2，3.19）——fcntl.flock 主锁 + 锁文件元数据（pid/run_id/心跳）诊断。

设计要点（与 O_EXCL 方案的取舍权衡，草稿已随 scratch-3.19 清理，2026-07-31）：
  - 真锁是 flock(LOCK_EX|LOCK_NB)：内核级原子，持有进程死亡（含 SIGKILL、
    run_guarded 水位击杀）即自动释放——"PID 不存在 → 可接管"由内核天然保证，
    无 O_EXCL 方案的残留锁/接管竞态问题。
  - 锁文件内容只是诊断元数据：{pid, run_id, role, started, heartbeat}，
    运行中由持有方定期 heartbeat() 刷新。抢锁失败时读它向人报告持有者是谁。
  - 陈死判定 stale 口径：持有者 PID 不存在，或心跳距今 > STALE_HEARTBEAT_S（600s）。
    * PID 不存在 → flock 已被内核释放，acquire 直接成功；若锁文件残留前任
      内容（异常退出没清理），acquire 返回"接管"说明，调用方记日志。
    * 心跳超时但 flock 仍被持有 → 进程活着但挂死（或心跳线程死了）。**保守
      拒绝**，报错里附 kill 建议——强抢一个还活着的进程的锁只会制造并发写。
  - 心跳写是原地写（seek0+truncate+write），**不可用 rename 原子写**：rename 换
    inode 会让 flock 绑在旧 inode 上、新路径可被第二个进程重复上锁（双持锁）。
    读方对半截 JSON 容错即可。
  - 同进程两线程对同一路径各自 open+flock 也互斥（flock 属 open file description）
    ——collect_queue 双泳道并行时同名币（多链同 workdir）天然被挡。
  - 子进程不继承锁：Python3 的 subprocess 默认 close_fds=True。
（来源：C2 采集侧并发加固，2026-07-22）"""
import datetime
import fcntl
import json
import os

STALE_HEARTBEAT_S = 600  # 心跳超时判陈死阈值（秒）


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, TypeError, ValueError):
        return False
    except PermissionError:
        return True


def _age_s(iso):
    try:
        t = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc)
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds()
    except (TypeError, ValueError):
        return None


class ProcLock:
    """一个锁文件一把锁。用法：
        lk = ProcLock(path, run_id=..., role="queue")
        ok, note = lk.acquire()   # note 非空 = 接管陈死残留的说明（记日志）
        if not ok: ...拒绝，note 是持有者诊断串...
        lk.heartbeat()            # 运行中定期刷
        lk.release()              # finally 里调；进程死亡时内核自动释放 flock
    """

    def __init__(self, path, run_id="", role=""):
        self.path = path
        self.run_id = run_id
        self.role = role
        self.started = None
        self._f = None

    # ---- 内部 ----
    def _read_info(self, f=None):
        try:
            if f is None:
                with open(self.path) as rf:
                    raw = rf.read()
            else:
                f.seek(0)
                raw = f.read()
            return json.loads(raw) if raw.strip() else None
        except (OSError, json.JSONDecodeError):
            return None  # 不存在/正在被写/半截 JSON——都当读不出

    def holder_diag(self):
        """抢锁失败时的持有者诊断串（人读）。"""
        info = self._read_info()
        if not info:
            return "锁被持有但锁文件读不出内容（可能正在写入）"
        pid = info.get("pid")
        age = _age_s(info.get("heartbeat"))
        age_s = f"{age:.0f}s 前" if age is not None else "未知"
        base = (f"持有者 pid={pid} role={info.get('role')} "
                f"run_id={info.get('run_id')} 启动 {info.get('started')} 心跳 {age_s}")
        if not _pid_alive(pid):
            # flock 仍被持有但 PID 不存在：理论不可能（内核会释放），唯一现实
            # 解释是锁 fd 被别的进程继承。指名道姓让人查。
            return base + "（异常：该 PID 已不存在但 flock 仍被持有——查是否有子进程继承了锁 fd）"
        if age is not None and age > STALE_HEARTBEAT_S:
            return (base + f"（心跳已超 {STALE_HEARTBEAT_S}s：进程疑似挂死。"
                    f"确认无采集 IO 后可 kill {pid} 再重试——本锁不强抢活进程）")
        return base + "（运行中）"

    # ---- 对外 ----
    def acquire(self):
        """非阻塞抢锁。返回 (ok, note)：
        ok=True  → note=None 或 "接管陈死残留…"（前任异常退出，调用方记日志）
        ok=False → note=持有者诊断串"""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        f = open(self.path, "a+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False, self.holder_diag()
        note = None
        prev = self._read_info(f)
        if prev and prev.get("pid") != os.getpid():
            age = _age_s(prev.get("heartbeat"))
            note = (f"接管陈死锁残留：前任 pid={prev.get('pid')} "
                    f"run_id={prev.get('run_id')} 最后心跳 "
                    f"{f'{age:.0f}s 前' if age is not None else '未知'}"
                    f"（进程已消亡未清理，flock 已由内核释放）")
        self._f = f
        self.started = _now_iso()
        self.heartbeat()
        return True, note

    def heartbeat(self):
        """原地刷新锁文件元数据（持有中定期调用）。"""
        if self._f is None:
            return
        try:
            self._f.seek(0)
            self._f.truncate()
            json.dump({"pid": os.getpid(), "run_id": self.run_id, "role": self.role,
                       "started": self.started, "heartbeat": _now_iso()}, self._f)
            self._f.flush()
        except OSError:
            pass  # 心跳失败不致命——flock 才是真锁

    def release(self):
        """清空元数据并放锁（锁文件本体常驻，避免 unlink 与新 open 的竞态）。"""
        if self._f is None:
            return
        try:
            self._f.seek(0)
            self._f.truncate()
            self._f.flush()
            fcntl.flock(self._f.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            try:
                self._f.close()
            except OSError:
                pass
            self._f = None
