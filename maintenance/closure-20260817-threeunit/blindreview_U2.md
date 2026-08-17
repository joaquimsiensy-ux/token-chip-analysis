# U2 盲审报告（opus 攻击型盲审 · 2026-08-17 · 被审版本 2e986c0/6.47.0）

> 盲审方式：实跑 20 个攻击向量 + 837baa8 基线对照 + 27 个真实存量采集目录扫描。仓库工作树全程未被污染（`git status` 空）。
> 攻击脚本与基线树遗留：session scratchpad（`attack_u2.py`、`attack2.py`、`baseline_check.py`、`scan_real_dirs.py`、`baseline837/`）；APU clone 副本 `/private/tmp/u2-apu-clone`（148M，APFS clone；原目录零改动）。

# 结论：BLOCK（不可交付，需消化轮）

**4 BREACH / 6 WEAK / 2 NOTE / 11 DEFENDED**

## BREACH（必修）

**B-01 UNKNOWN_LEGACY → VERIFIED 零成本洗白**（本单元立项理由未关闭）
迁移段改写成原生 v4 后，preflight 收据从 `UNKNOWN_LEGACY` 变 `VERIFIED`。攻击者只需删掉 `collector_provenance` 与三个迁移键、把 `collector` 填成公开可算的当前脚本哈希（`shasum -a 256 scripts/evm/fetch_hypersync_v2.py`）。**不需要伪造脚本**——施工报告声明的"不防能同时伪造脚本与收据的攻击者"覆盖不到这个成本为零的路径。工单 §1 说的"洗归属窗口"只是从 identity 层搬到了 done 层。更讽刺的是不对称：真段在脚本升级后失效（B-02），伪造段永远新鲜。
建议：`VERIFIED` 改为 `SELF_REPORTED`，或直接输出 collector 哈希由上层判定，不给二值语义标签。

**B-02 采集器一升级，既有 v4 done 与 recovered identity 全部 fail-closed**
`collector`/`migrator`/`recoverer` 三条线分别绑 protocol `hypersync-v2-done/v4` 与 `hypersync-capture-identity/v2`，登记表里这两个 protocol 首版全空 → allowlist 只有当前脚本哈希。实测：改脚本哈希后原生 v4 done 报 `collector 未绑定当前或历史 ACTIVE hypersync-v2-done/v4 采集器`，recovered identity 报同族错误。
`references/maintenance-review-repair.md:172` 只写"登记被替换版本"，没写要按 protocol 逐条补登；本次只补了 `identity/v1` 一条。下次维护者照抄就断链——**而这条纪律的来源正是 NES 0816「169 份正版 receipt 被追溯误拦」，同一个坑本单元新挖两个**。

**B-03 新 inventory 闸与仓库自有的隔离/回滚机制互斥，且无自愈路径**
`validate_capture_inventory` 要求根目录只有 `run_[0-9]+`、每 run 恰三件套。全部实测阻断：
- `staged_capture.sh` 自己建的 `outdir/quarantine/`（该脚本 :39、:50）→ preflight/recover/refresh 全拒；
- refresh 回滚失败时**特意保留**的 `<done>.recover`（`fetch_hypersync_v2.py:675-679`，F-07 设计）→ 恢复件自己变成锁，refresh 再也跑不了；
- SIGKILL/断电残留的 `.done.json.refresh-tmp.<pid>` / `.refresh-bak.<pid>` → 同样锁死；
- **真实实件**：APU 0801 案主目录（全库唯一带 identity、数据完整、已交付）基线 837baa8 下 preflight PASS，U2 后 BLOCKED，卡在人工诊断目录 `partial_run_19368487_wrongurl_bsc`。
文档只加了一句"正式 preflight 前须把该诊断目录移出采集根"——人肉纪律，且没覆盖 recover/refresh 也被堵；报错"未识别残件: X"不给任何补救命令（对比 identity 缺失明确指向 `--recover-identity`）。移走残件后 refresh+preflight 可通（已在 clone 副本验证），所以是可修的，但目前无机器化出路。

**B-04 `staged_capture.sh` 对全新目录彻底不可用**
identity 检查在 skip 循环之前，而 identity 只有 fetch 脚本首跑才会建。全新目录 → FATAL(rc=2) → 提示跑 `--recover-identity` → recover 对空目录报"没有 run_* 数据段" → 死路。基线下全新目录正常进入采集。分段采集从零起步正是该脚本的主用途（其用法示例即全新目录），设计与施工双方都没走过首采路径。

## WEAK

- **W-01** macOS `.DS_Store` 锁死目录：根目录的让 recover 拒，run 内的让已通过的 preflight 转拒；基线均放行。用户是 Mac，Finder 访问即生成。
- **W-02** REVOKED 对当前脚本无效：`_allowed_script_hashes` 无条件并入 `sha256_file(__file__)`，吊销当前版本不生效（既有模式，本单元复制到三条新线）。
- **W-03** recovered 身份在 preflight 收据里不可见：`kind` 仍是 `hypersync-v2-native`，identity 层不带 `recovered`/`lineage`，与原生身份完全同形；而 recovered 目录允许混入新的原生 VERIFIED 段，会进一步抬高上层信心。附带：删 identity + 改 done token 后 recover 会照 done 自证签发新 token 身份（下游有通道声明 token 兜底，故不单列 BREACH）。
- **W-04** `pre_migration_sha256` 事后不可验（原件已覆盖），改成任意 64 位十六进制仍过——是留痕不是闸，但被写成"判别联合必备项"。
- **W-05** `root = Path(outdir).resolve()` 后的 `root.is_symlink()` 恒假 = 死代码，symlink 根直接放行。
- **W-06** CSV 回执仍用裸 `json.loads`（`channels_preflight.py:141`），重复键闸跨通道不等深。

## NOTE

- **N-01** 施工偏离工单 §13 未报备但方向正确：工单要求 consumer 段 v3「替换」为 v4，施工方保留 v3。盲审实测删掉 v3 后 `invariant_scan` rc=1（两条 discrepancy），证明保留是机器必需的，**工单判断有误**。（改动已即时还原并校验字节一致。）
- **N-02** CHANGELOG「实件演练三态闭合」样本有选择性：演练用的是 `APU分析/data_lp`（PASS），不是 APU 0801 案主目录（BLOCKED）。27 个真实采集根扫描 5 PASS / 22 BLOCKED——多数 BLOCKED 是 07-31 磁盘清理残骸（拦对了，不算账），APU0801 是真回归。

## DEFENDED（挡住了，如实记）

判别联合三种混合形态全拒；protocol 伪造入口否决（含 mock 历史条目正例）；REVOKED 跨 protocol hash-wide；done+identity 两族全部读入点重复键拒；未知 schema 不落默认分支；枚举前收类型；TOCTOU 三处冻结+复验；多段 pre-schema 拒猜；migrator 未登记拒；recover→refresh 顺序强制；recover 拒覆盖既有 identity。`f544a196` 的 git 考证独立复算成立（基线树该文件 sha256 与登记一致，commit `0ec6d1e` 是 HEAD 祖先）。
