# 工单 C 消化轮 2 盲审复核报告（第三轮，对 a3447ac）——判定 CLOSED

> 入档件。盲审员（opus 子代理）11 项注入＋symlink 五形态＋staging 新产物独立复验。
> 判定：**CLOSED，可交付**——二轮全部 6 条 finding 闭合，无新击穿无新缺陷；残留 4 条观察级（全局口径边界/冗余闸钉子缺口），登记供用户裁决。
> 三轮收敛轨迹：首轮 2 击穿＋7 缺陷＋8 观察 → 二轮 2 缺陷（新引入）＋5 观察 → 三轮 0 缺陷。

## 二轮 finding 逐项判定

- **N-01 CLOSED**：symlink 五形态（绝对/相对/嵌套两跳/symlink→hard link/悬空）编译点全拒、producer CLI 侧拒；hard link 绿反证不误伤；注入 s01/s03 精确转红。
- **N-02 CLOSED**：接线锚走 run(new-analysis) 真发布路由＋末字节异或篡改＋断言"物理 sha256"错误串——删接线该 error 消失即红（t08）。
- **N-03 CLOSED**：size+1／sha 大写／63 字符全拒（t06/t15/tc4 转红）。
- **N-04 CLOSED**：producer parse_constant 钉在解析层（业务未读取字段注入 NaN——设计正确），t13 转红。
- **N-05 CLOSED（主入口）**：load_json 委托 load_adversarial_json 无第三份 loader；audit_release_gate 零裸 json.loads 残留；NaN 归类"JSON无法读取"不落逐点比对兜底；RecursionError 不外冒有锚。残留 O-2。
- **N-06 CLOSED**：migration/snapshot/reconcile 三处 producer 指纹与快照实算逐一相符。

## 注入 11 项：9 RED／2 STILL_GREEN（均核实非缺陷）

s02＝producer 双 symlink 闸删一道另一道仍拦（冗余闸非漏闸，两条路径实测都关死）；s05＝reproduce 调用点守卫缺口（闸已统一，归 O-2 观察）。

## PYTHIA staging 新产物独立复验（全绿）

边逻辑摘要三处一致且与盲审首轮独立重算的 json.dumps 口径值相同（BC-O1 在 4,857,654 行真实案实证闭合）；物理指纹逐字相符；边文件与 data/ 目录均非 symlink、与源同 inode（nlink=3 含备份链接）；类型面全对；分母对锚 998158041739995；三输入 sha 全符。

## 观察级残留（4 条，登记供用户裁决）

- **O-1** 目录级 symlink 可绕：整个 data/ 换软链后边文件自身非 symlink → 放行。全库既有 symlink 口径（_resolve_ref/importer 同样只查路径末段）固有边界，非本轮引入；内容仍受三输入 sha 三验＋发布点物理 sha 约束，不产生假数据放行。收口须全库统一 realpath 逐段校验，属跨工单面。
- **O-2** reproduce 收据入口（check_reproduce_receipt 的 load_json 调用点）无接线守卫（s05 绿）；summary_sha256 比对仍在。
- **O-3** symlink 拒绝退出码两路不一致（CLI 路径 rc=1、直调 rc=2）——沿用 load_edges 既有风格，非本轮新问题。
- **O-4** a4_gate.py（7 处）/a5_report_seal.py（8 处）仍有裸 json.loads——不在 reconcile 链上，属别的工单面，记录备同族等深。

首轮登记项 BC-O2/O3/O4/O7 无变化维持。

## 只读自证

零 git 写；快照六件 sha 相符；注入 cp -al 副本＋断链；工作区 0 改动 HEAD=a3447ac；PYTHIA 案根零改动；staging 时间戳核对为裁判执行窗口。
