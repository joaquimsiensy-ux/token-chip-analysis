# 盲审 G2：PASS

未发现本段缺陷或工单外改动。完整报告已打印到 stdout。

实际核验结果：

- **终点反例已关闭**：内存执行真实函数，保持 raw_supply=100，将 config 从 `0/100` 改为 `2/1` 并重绑哈希；对账深验仍通过，但发布闸同时拒绝 facts/config 与观测不一致。accounting 与 bundle 不同值也被拒。
- `checks` 非 dict 返回拒收理由，不抛异常。
- 来源链闭合：冻结块 `decimals()` → bundle → accounting → 两处闸。
- 9 笔 transcript、两侧 uint8 校验、旧 v1 拒收、18 处 schema 同步均通过核验。
- 排除式 grep 零命中；字节数为 **8021 / 930076 / 8798**，references 恰增 15。
- 六视角、四组 RED、既有断言及白名单均核过，未发现断言弱化。

全部 21 个测试入口均已尝试。`invariant_scan`、`docs_lint --all`、`test_commands_deploy_sync` 完整通过；17 个入口因临时目录权限未完成，纵切片因 `socket.bind EPERM` 未完成。内存补验中，observation 原用例 **7/11**、nonempty_code **5/5** 通过；完整 CLI 回归仍未验证。

全程只读、离线，工作区干净；未读取 `~/.codex/` 或 memories。
