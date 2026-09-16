# 施工 T3-r1: 完成

本轮按 `workorder_t3_r1.md` v2 完成指定返修。完整契约测试 exit 0、283 项全部通过；相对施工开始时工作树，仅两个白名单文件变化并新增本报告。

分支：`fix/three-items-20260916`。施工前 HEAD：`8d8787e67ae1229b3c906e63bcdc421ae9d2cc14`。验收基线为本轮开始时的工作树，包含 T3 主工单既有未提交改动。

| 文件 | 施工后行号 | 本轮改动 |
| --- | --- | --- |
| `scripts/tests/test_handoff_manifest.py` | 735–737 | 写事件的非整数相对路径直接记为“未归属写事件”并返回；绝对路径和 fd 逻辑保留。 |
| 同上 | 777 | 在原最后一例 rename 源端事件后追加 `sys.audit('open', 'probe_rel', None, os.O_WRONLY \| os.O_CREAT)`。 |
| 同上 | 788–792 | 原 check 的报警数改为 8，核对 `alarms[7]` 的事件及归属，文案追加“/相对路径”；原 `alarms[:3]` 和 `alarms[4]["scope"]` 断言保留。 |
| `maintenance/repair-20260916-three-items/t3_scope_evidence.txt` | 施工前 17–20；施工后删除位置为 17 行前 | 仅删除 add_path / discover / add_explicit / bound_ref 四行“新增函数”笔误，其他内容及工具输出格式不变。 |
| `maintenance/repair-20260916-three-items/t3_r1_done.md` | 1 起 | 本单新增施工报告。 |

未新增 check。正例日志为空的断言（施工后 796–797 行）保持原文；其他六组子测及其余既有函数保持原文。施工前将原钩子抽取到内存并合成相对路径写 open，实际得到 `alarms=[]`，复现漏记。

**测试记录**

执行命令：

```sh
python3 -B scripts/tests/test_handoff_manifest.py
```

退出码：`0`。PASS 数：`283`，FAIL 数：`0`，与工单要求的 283 项一致。实际输出节选：

```text
ok    T3 audit 自检 flags/rename 目标/链接词法/相邻边界/dir_fd/未归属/realpath/源端/相对路径
ok    T3 案目录快照完全一致
========================================
handoff_manifest 契约测试全部通过（283 项）
```

28 条正例“案目录零写入”、28 条审计包装后的正例退出码及 28 条去写位后的正例检查全部通过。完整测试可正常使用临时目录，无沙箱临时目录阻断。

`git diff --check`：exit 0，无输出。两个目标文件的实际 SHA-256 与施工前仅应用工单指定替换得到的预期全文 SHA-256 完全一致，因此改动严格限于指定区域和四行删除。

**施工前快照**

`git status --porcelain=v1 --untracked-files=all` 原始输出（4 个 M，15 个 ??）：

```text
 M references/context-discipline.md
 M references/split-run.md
 M scripts/report/handoff_manifest.py
 M scripts/tests/test_handoff_manifest.py
?? maintenance/repair-20260916-three-items/t3_accept_fable.txt
?? maintenance/repair-20260916-three-items/t3_blind_reply.txt
?? maintenance/repair-20260916-three-items/t3_blind_reply_opus.txt
?? maintenance/repair-20260916-three-items/t3_byte_evidence.txt
?? maintenance/repair-20260916-three-items/t3_docs_lint.txt
?? maintenance/repair-20260916-three-items/t3_done.md
?? maintenance/repair-20260916-three-items/t3_forggie_fable.txt
?? maintenance/repair-20260916-three-items/t3_green_evidence.txt
?? maintenance/repair-20260916-three-items/t3_r1_review_reply.txt
?? maintenance/repair-20260916-three-items/t3_r1_review_reply_r2.txt
?? maintenance/repair-20260916-three-items/t3_red_evidence.txt
?? maintenance/repair-20260916-three-items/t3_run_all_evidence.txt
?? maintenance/repair-20260916-three-items/t3_run_all_fable.log
?? maintenance/repair-20260916-three-items/t3_scope_evidence.txt
?? maintenance/repair-20260916-three-items/workorder_t3_r1.md
```

另在内存保留两个允许修改文件的施工前完整原文，并为全部 tracked 路径及未跟踪文件记录类型、SHA-1、SHA-256，共 1,263 个文件。

白名单外全部已改/未跟踪文件的 `shasum` 原始输出如下，共 17 个；施工后逐项复核均相同：

```text
0be23f37f2a3dd92d6c11ec531489178983e28c3  maintenance/repair-20260916-three-items/t3_accept_fable.txt
7adb8c78d498bad7d6774d502b3a5e4c3399e755  maintenance/repair-20260916-three-items/t3_blind_reply.txt
a3dfa2eb7e4c7ee80d5b04e4fab1c99fcec55b23  maintenance/repair-20260916-three-items/t3_blind_reply_opus.txt
04912eec7423b55a298a64b5875f47c0fcec4f4b  maintenance/repair-20260916-three-items/t3_byte_evidence.txt
504527edc273d65828997b9bb230300273dacfb5  maintenance/repair-20260916-three-items/t3_docs_lint.txt
91c5175e2672a7d3376ad7ac527d51fbdefb6aa4  maintenance/repair-20260916-three-items/t3_done.md
5d25dcb6019f6def20df87ed64c063e796cec416  maintenance/repair-20260916-three-items/t3_forggie_fable.txt
6aa9e6472921cb4b0b13e821d7dc54d88b4833d7  maintenance/repair-20260916-three-items/t3_green_evidence.txt
650eb4472f19ae247f8aaa260787ec628c18bdf3  maintenance/repair-20260916-three-items/t3_r1_review_reply.txt
4ac9c92b85407146748c8ff7bebe588966c71fd9  maintenance/repair-20260916-three-items/t3_r1_review_reply_r2.txt
4f8e4db5570d1c980037dfca7360b17a202a253b  maintenance/repair-20260916-three-items/t3_red_evidence.txt
9b8459f96dba30316cd0e6d1f115d199719620f4  maintenance/repair-20260916-three-items/t3_run_all_evidence.txt
63539cd082c529eed95be3d098c519867a87688d  maintenance/repair-20260916-three-items/t3_run_all_fable.log
41a1b19e715b4125f34ed052c9f7a8ff7dbd9cc5  maintenance/repair-20260916-three-items/workorder_t3_r1.md
7b650bfdacdc658d9644dfdc53849a5f5c28a336  references/context-discipline.md
b90a9d093fd4922ae9db1efd7365b9ce98531952  references/split-run.md
15fbe24ff7b886bdf6e3a16d6d7603457165b6c9  scripts/report/handoff_manifest.py
```

**生产代码与文档零增量**

计算口径：

```sh
git diff HEAD -- scripts/report/handoff_manifest.py references/ | shasum
```

施工前：`ae825f2bbe8c4ac300091426da7b57cc21ec5582  -`。
施工后：`ae825f2bbe8c4ac300091426da7b57cc21ec5582  -`。

`scripts/report/handoff_manifest.py`、`references/context-discipline.md`、`references/split-run.md` 的文件哈希也均与基线相同。`CHANGELOG.md`、`VERSION`、`pyproject.toml` 内容哈希均未变。

两个允许修改文件的全文 SHA-256：

| 文件 | 施工前 | 施工后 |
| --- | --- | --- |
| `scripts/tests/test_handoff_manifest.py` | `c24c72850cdbb6a87748b24125098ec79c4d0be76ab88733cfd6c37d774080aa` | `19b3bbf02b117020f603d6a3273ea926375684cbfa856fdc31547ca6358c400c` |
| `maintenance/repair-20260916-three-items/t3_scope_evidence.txt` | `092bc7d1eddb6fa3b67260363d219ae71197bf8cf54aeaf5aec6721f24241ff1` | `9daff9ebd7eb0baaf8dda2b2af8524a794b3e07c9d527e71acbf62e5cf3183ce` |

**最终快照比对**

最终核对 PASS：原有 1,263 个文件中仅 §0 两个文件内容变化；唯一新增文件为本报告，未删除任何原有文件。最终共记录 1,264 个文件。白名单外 17 个已改/未跟踪文件的 SHA-1 逐项与施工前一致，生产 diff SHA-1 完全一致，HEAD 与分支均未变。未 commit；没有执行 stash、checkout 或 reset。既有 T3 主工单施工完整保留。

施工后 `git status --porcelain=v1 --untracked-files=all` 原始输出（4 个 M，16 个 ??）；去除本报告的新增行后，与施工前原始输出逐字一致：

```text
 M references/context-discipline.md
 M references/split-run.md
 M scripts/report/handoff_manifest.py
 M scripts/tests/test_handoff_manifest.py
?? maintenance/repair-20260916-three-items/t3_accept_fable.txt
?? maintenance/repair-20260916-three-items/t3_blind_reply.txt
?? maintenance/repair-20260916-three-items/t3_blind_reply_opus.txt
?? maintenance/repair-20260916-three-items/t3_byte_evidence.txt
?? maintenance/repair-20260916-three-items/t3_docs_lint.txt
?? maintenance/repair-20260916-three-items/t3_done.md
?? maintenance/repair-20260916-three-items/t3_forggie_fable.txt
?? maintenance/repair-20260916-three-items/t3_green_evidence.txt
?? maintenance/repair-20260916-three-items/t3_r1_done.md
?? maintenance/repair-20260916-three-items/t3_r1_review_reply.txt
?? maintenance/repair-20260916-three-items/t3_r1_review_reply_r2.txt
?? maintenance/repair-20260916-three-items/t3_red_evidence.txt
?? maintenance/repair-20260916-three-items/t3_run_all_evidence.txt
?? maintenance/repair-20260916-three-items/t3_run_all_fable.log
?? maintenance/repair-20260916-three-items/t3_scope_evidence.txt
?? maintenance/repair-20260916-three-items/workorder_t3_r1.md
```

**本单增量（相对施工开始时原文）**

```diff
--- scripts/tests/test_handoff_manifest.py (施工前)
+++ scripts/tests/test_handoff_manifest.py (施工后)
@@ -732,6 +732,9 @@
             isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
         if not writes:
             return
+        if not isinstance(path, int) and not os.path.isabs(os.fsdecode(path)):
+            events.append({'event': 'open', 'args': repr(args), 'scope': '未归属写事件'})
+            return
         paths, access = [(path, None)], True
     elif event in ('os.remove', 'os.unlink', 'os.rmdir'):
         paths = [(args[0], args[1] if len(args) > 1 else None)]
@@ -771,6 +774,7 @@
         sys.audit('os.remove', 'probe', -98765)
         sys.audit('open', os.path.join(os.path.dirname(case_real), 'into_case'), None, os.O_WRONLY)
         sys.audit('os.rename', os.path.join(case_real, 'x'), case_real + '_sibling/x', -1, -1)
+        sys.audit('open', 'probe_rel', None, os.O_WRONLY | os.O_CREAT)
     else:
         sys.argv = [script, *arguments]
         runpy.run_path(script, run_name='__main__')
@@ -781,10 +785,11 @@
         p = subprocess.run([sys.executable, "-B", str(wrapper), str(case), str(log),
                             "selftest", SCRIPT], capture_output=True, text=True)
         alarms = json.loads(log.read_text())
-        check("T3 audit 自检 flags/rename 目标/链接词法/相邻边界/dir_fd/未归属/realpath/源端",
-              p.returncode == 0 and len(alarms) == 7
+        check("T3 audit 自检 flags/rename 目标/链接词法/相邻边界/dir_fd/未归属/realpath/源端/相对路径",
+              p.returncode == 0 and len(alarms) == 8
               and [x["event"] for x in alarms[:3]] == ["open", "os.rename", "os.remove"]
-              and alarms[4]["scope"] == "未归属写事件")
+              and alarms[4]["scope"] == "未归属写事件"
+              and alarms[7]["event"] == "open" and alarms[7]["scope"] == "未归属写事件")
         for command in positives:
             p = subprocess.run([sys.executable, "-B", str(wrapper), str(case), str(log),
                                 "run", SCRIPT, *command[3:]], capture_output=True, text=True)

--- maintenance/repair-20260916-three-items/t3_scope_evidence.txt (施工前)
+++ maintenance/repair-20260916-three-items/t3_scope_evidence.txt (施工后)
@@ -14,10 +14,6 @@
 新增函数 _lookup_index: 1516-1550
 新增函数 _lookup_text: 1553-1559
 新增函数 cmd_lookup: 1562-1610
-新增函数 add_path: 266-281
-新增函数 discover: 283-286
-新增函数 add_explicit: 288-295
-新增函数 bound_ref: 969-989
 scripts/tests/test_handoff_manifest.py: 既有函数变更仅 main；其他既有函数文本完全相同 PASS。
 新增函数 test_t3_readonly_queries: 531-863
 新增函数 invoke: 546-555
```
