#!/usr/bin/env python3
"""address-book.md 实战核验条目 → manual_labels.csv（最高优先级源）
地址逐条复制自 ~/.codex/skills/token-chip-analysis/references/address-book.md（2026-07-16 版）"""
import csv

R = []
def a(addr, chains, name, cat, tier, date='2026-07', ev='address-book 实战核验',
      merge_policy='', balance_policy='', status=''):
    """v4.2：支持 merge_policy/balance_policy/status 覆盖列（manual 层是策略覆盖的第一真源；
    不填走 resolver 推导）。"""
    for ch in chains:
        R.append(dict(address=addr, chain=ch, name=name, category=cat, tier=tier,
                      source='addressbook', added_date=date, evidence=ev,
                      merge_policy=merge_policy, balance_policy=balance_policy, status=status))

EVM3 = ('eth', 'bsc', 'base')   # EOA/CREATE2 跨 EVM 链同址
# ===== EVM CEX 主段 =====
a('0xf977814e90da44bfa03b6295a0616a897441acec', EVM3, 'Binance HotWallet20', 'cex', 'exclude')
a('0x8894e0a0c962cb723c1976a4421c95949be2d4e3', ('bsc',), 'Binance 51', 'cex', 'exclude')
a('0xe2fc31f816a9b94326492132018c3aecc4a93ae1', ('eth', 'bsc'), 'Binance Withdrawals7（提币出口）', 'cex', 'exclude')
a('0x631fc1ea2270e98fbd9d92658ece0f5a269aa161', ('bsc',), 'Binance BSC hot', 'cex', 'exclude')
a('0x5a52e96bacdabb82fd05763e25335261b270efcb', ('eth', 'bsc'), 'Binance 28', 'cex', 'exclude')
a('0x28c6c06298d514db089934071355e5743bf21d60', ('eth',), 'Binance 14', 'cex', 'exclude')
a('0xdfd5293d8e347dfe59e90efd55b2956a1343963d', ('eth',), 'Binance 16', 'cex', 'exclude')
a('0xf89d7b9c864f589bbf53a82105107622b35eaa40', ('eth', 'bsc'), 'Bybit HotWallet', 'cex', 'exclude')
a('0x4982085c9e2f89f2ecb8131eca71afad896e89cb', ('eth', 'bsc'), 'MEXC 13', 'cex', 'exclude')
a('0x75e89d5979e4f6fba9f97c104c2f0afb3f1dcb88', ('eth',), 'MEXC 1', 'cex', 'exclude')
a('0x0d0707963952f2fba59dd06f2b425ace40b492fe', ('eth', 'bsc'), 'Gate.io 1', 'cex', 'exclude')
a('0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23', ('eth', 'bsc'), 'Bitget 6', 'cex', 'exclude')
a('0x2b5634c42055806a59e9107ed44d43c426e58258', ('eth',), 'KuCoin 1', 'cex', 'exclude')
a('0xdc76cd25977e0a5ae17155770273ad58648900d3', ('eth',), 'HTX 56', 'cex', 'exclude')
a('0x6cc5f688a315f3dc28a7781717a9a798a59fda7b', ('eth',), 'OKX', 'cex', 'exclude')
# 币安 BSC 二级提币热钱包（funded-by 聚类头号假阳性源）
for h in ('0xdccf3b77da55107280bd850ea519df3705d1a75a', '0x1fbe2acee135d991592f167ac371f3dd893a508b',
          '0x73f5ebe90f27b46ea12e5795d16c4b408b19cc6f', '0xbd612a3f30dca67bf60a39fd0d35e39b7ab80774',
          '0xeb2d2f1b8c558a40207669291fda468e50c8a0bb'):
    a(h, ('bsc',), 'Binance BSC 二级提币热钱包（nonce 百万级）', 'cex', 'exclude',
      ev='外部 BSC 分析考古 2026-07；funded-by 聚类假阳性源')

# ===== 聚合器/跨链桥基建（EVM 通用） =====
a('0xf70da97812cb96acdf810712aa562db8dfa3dbef', EVM3 + ('robinhood',), 'Relay 桥 solver 热钱包（供gas/代发/替空投池发币）', 'bridge', 'exclude')
a('0x9008d19f58aabd9ed0d60971565aa8510560ab41', EVM3, 'CoW Protocol Settlement', 'router', 'exclude')
a('0x1111111254eeb25477b68fb85ed929f73a960582', EVM3, '1inch v5 Router', 'router', 'exclude')
a('0x111111125421ca6dc452d289314280a0f8842a65', EVM3, '1inch v6 Router', 'router', 'exclude')
a('0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae', EVM3, 'LI.FI Diamond（跨链聚合）', 'bridge', 'exclude')
a('0x663dc15d3c1ac63ff12e45ab68fea3f0a883c251', ('bsc',), 'deBridge（BSC 结算）', 'bridge', 'exclude')
# 做市商
a('0xf584f8728b874a6a5c7a8d4d387c9aae9172d621', ('eth', 'bsc'), 'Jump Trading', 'market-maker', 'identity')
a('0xdbf5e9c5206d0db70a90108bf936da60221dc080', ('eth', 'bsc'), 'Wintermute', 'market-maker', 'identity')
a('0xd8d6ffe342210057bf4dcc31da28d006f253cef0', ('eth', 'bsc'), 'GSR', 'market-maker', 'identity')
a('0xddacad3b1edee8e2f5b2e84f658202534fcb0374', ('eth', 'bsc'), 'DWF Labs', 'market-maker', 'identity')
# 通用合约
a('0xca11bde05977b3631167028862be2a173976ca11', EVM3 + ('robinhood',), 'Multicall3（全 EVM 同址）', 'infra', 'exclude')
a('0x0000000071727de22e5e9d8baf0edac6f37da032', EVM3 + ('robinhood',), 'ERC-4337 EntryPoint v0.7（跨链同址）', 'infra', 'exclude')
a('0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789', EVM3 + ('robinhood',), 'ERC-4337 EntryPoint v0.6（跨链同址，存量流量仍大）', 'infra', 'exclude',
  date='2026-07-17', ev='四链 getCode 亲验 2026-07-17（code 全长一致 47380）')

# ===== BSC 路由/托管/平台 =====
a('0x73d8bd54f7cf5fab43fe4ef40a62d390644946db', ('bsc',), 'Binance: Alpha 2.0 Router Proxy（场内买盘链上托管 omnibus）', 'cex', 'exclude', ev='bibi 分析核验 2026-07-12')
a('0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f', ('bsc',), 'RelayRouterV3（Relay.link 跨链聚合路由）', 'bridge', 'exclude')
a('0xb300000b72deaeb607a12d5f54773d1c19c7028d', ('bsc',), 'Binance: DEX Router（币安 Web3 钱包入口）', 'router', 'exclude')
a('0x00000000009726632680fb29d3f7a9734e3010e2', ('bsc',), 'Rainbow: Router', 'router', 'exclude')
a('0x0d4eca97c066961e0caa10608a0736f858dd13e6', ('bsc',), '"Prediction" 高频对倒 bot 代理（292万笔+净仓恒零）', 'bot-service', 'exclude')
a('0x757eba15a64468e6535532fcf093cef90e226f85', ('bsc',), 'four.meme 主合约（mint 接收/createToken 入口）', 'launchpad', 'exclude')
a('0x5c952063c7fc8610ffdb798152d69f0b9550762b', ('bsc',), 'four.meme TokenManager（bonding curve 分发）', 'launchpad', 'exclude')
a('0x238a358808379702088667322f80ac48bad5e6c4', ('bsc',), 'PancakeSwap Infinity Vault（LP 基础设施）', 'protocol', 'exclude')
a('0x28e2ea090877bf75740558f6bfb36a5ffee9e9df', ('bsc',), 'Uniswap V4 PoolManager（BSC 单例，内嵌池）', 'protocol', 'exclude')
a('0xc7f501d25ea088aefca8b4b3ebd936aae12bf4a4', ('bsc',), 'Giggle Academy 捐赠地址（CZ 慈善 Safe 2/4）', 'charity', 'identity')
# EIP-7702 delegate 实现
a('0xcc0c946eecf01a4bc76bc333ea74ceb04756f17b', EVM3, '某钱包 App 统一 EIP-7702 实现（同 delegate≠同实体）', 'infra', 'exclude')
a('0x63c0c19a282a1b52b07dd5a65b58948a07dae32b', EVM3, 'MetaMask StatelessDeleGator（EIP-7702）', 'infra', 'exclude')

# ===== Solana =====
a('9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM', ('sol',), 'Binance 冷钱包', 'cex', 'exclude')
a('3gd3dqgtJ4jWfBfLYTX67DALFetjc5iS72sCgRhCkW2u', ('sol',), 'Binance 冷钱包2', 'cex', 'exclude')
a('5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9', ('sol',), 'Binance 热钱包', 'cex', 'exclude')
a('5LZkATrLwHYCQj2YuVbjjgsDZzBk6YfL4pFQRJmtboT2', ('sol',), 'Bybit（PoR 审计收录）', 'cex', 'exclude')
a('u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w', ('sol',), 'Gate.io', 'cex', 'exclude')
a('ASTyfSima4LLAdDgoFGkgqoKowG1LZFDr9fAQrg7iaJZ', ('sol',), 'MEXC', 'cex', 'exclude')
a('BmFdpraQhkiDQE6SnfG5omcA1VwzqfXrwtNYBwWTymy6', ('sol',), 'KuCoin', 'cex', 'exclude')
a('H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS', ('sol',), 'Coinbase（含 Prime 托管）', 'cex', 'exclude')
a('AobVSwdW9BbpMdJvTqeCN4hPAmh4rHm7vwLnQ5ATSyrS', ('sol',), 'Crypto.com', 'cex', 'exclude')
# v4.2 策略修正（codex 第四轮复核）：未确证设施禁边不剔仓——万一它其实是大户，exclude 会把
# 真实持仓静默藏掉。确证后再升 cex/exclude。
a('8Mm46CsqxiyAputDUp2cXHg41HE3BfynTeMBDwzrMZQH', ('sol',), '疑似 OKX/Bitget 归集（未免费确证）',
  'suspected-cex', 'identity', merge_policy='no_merge', balance_policy='count')
# 程序 ID
a('magnaSHyv8zzKJJmr8NSz5JXmtdGDTTFPEADmvNAwbj', ('sol',), 'Magna vesting 程序', 'locker', 'exclude')
a('SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf', ('sol',), 'Squads 多签程序', 'program', 'exclude')
a('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', ('sol',), 'SPL Token 程序', 'program', 'exclude')
a('pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA', ('sol',), 'PumpSwap AMM 程序（creator-vault PDA=dev 领费来源）', 'program', 'exclude')
a('6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P', ('sol',), 'pump.fun bonding curve 程序', 'launchpad', 'exclude')
# 平台/路由/锁仓
a('BAGSB9TpGrZxQbEsrEznv5jXXdwyP6AXerN8aVRiAmcv', ('sol',), 'Bags 平台署名 creator（平台特征非项目方）', 'launchpad', 'exclude')
a('FhVo3mqL8PW5pH5U2CN4XE33DokiyZnUwuGpH2hmHLuM', ('sol',), 'Bags 平台金库（每币 17% 整数配额，算集中度前剔除）', 'launchpad', 'exclude')
a('FLASHX8DrLbgeR8FcfNV1F5krxYcYMUdBkrP1EPBtxB9', ('sol',), 'Axiom Trade 路由', 'router', 'exclude')
a('jitodontfrontB1111111TradeWithAxiomDotTrade', ('sol',), 'Axiom 防抢跑标记账户', 'router', 'exclude')
a('strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m', ('sol',), 'Streamflow 锁仓程序', 'locker', 'exclude')
a('wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u', ('sol',), 'Streamflow 自动提取服务 feePayer', 'locker', 'exclude')
a('pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ', ('sol',), 'pump.fun fee 程序', 'launchpad', 'exclude')
a('HNCne2FkVaNghhjKXapxJzPaBvAKDG1Ge3gqhZyfVWLM', ('sol',), 'Base-Solana 官方桥 Bridge 程序', 'bridge', 'exclude')
a('g1et5VenhfJHJwsdJsDbxWZuotD5H4iELNG61kS4fb9', ('sol',), 'Base-Solana 官方桥 Base Relayer 程序', 'bridge', 'exclude')

# ===== Robinhood Chain =====
RH = ('robinhood',)
a('0x00000000aa59b37306e34cef3e021e07156cfa3a', RH, '聚合器执行器（代发交易高度数节点）', 'router', 'exclude')
a('0x8366a39cc670b4001a1121b8f6a443a643e40951', RH, 'Uniswap V4 PoolManager（单例，"持仓"=全链 V4 池合计）', 'protocol', 'exclude')
a('0x7b226b0b2347aa522b97eba6c6da59c2edf908b2', RH, 'DEX 聚合器执行合约（即收即卖，峰值持仓≈0；已仲裁非 V4 PoolManager）', 'router', 'exclude')
a('0x0bd7d308f8e1639fab988df18a8011f41eacad73', RH, 'WETH（Robinhood Chain）', 'token-contract', 'exclude')
a('0x1887fa9edadeab7562b01cc3f4fa246ace2c3cdd', RH, '公共提款热钱包（App 托管出金通道；时均 ~50 收款人）', 'infra', 'exclude', ev='Pointless/CASHCAT 三次核验；据它建的聚类一律作废')
a('0x4cd00e387622c35bddb9b4c962c136462338bc31', RH, 'RelayDepository（Relay 桥存款库；depositNative=跨链离场断头）', 'bridge', 'exclude', date='2026-07-17', ev='TRASH 增量核验：创建者利润经 23 跳板归集离场通道')
a('0xa687b664662b96b180346d699a6d5b42e9b05d31', RH, '聚合卖出路由/原子中转（549 上游→唯一下游 PM，余额恒 0）', 'bot-service', 'exclude', date='2026-07-17', ev='TRASH 增量核验：转给它=同 tx 落池卖出，勿判私有漏斗')
a('0x2e9b3fc5e73221e8ac0da2a1d836bda0273eab7f', RH, 'App 交易路径中转（同秒入出，上游 RobinHoodSettler）', 'bot-service', 'exclude', date='2026-07-17', ev='TRASH 增量核验：经它转入=App 内市场买入交付，共同上游≠关联')
a('0x8f10b468b06c6fd214b65f87778827f7d113f996', RH, '套利/路由 bot 原子中转（PM↔交付金库对倒，零驻留）', 'bot-service', 'exclude', date='2026-07-17', ev='TRASH 增量核验')
a('0x469cb5da5f46d9c16d9825e41d831377e167478f', RH, '公共提款热钱包的补货金主（累计 3666E）', 'infra', 'exclude')
a('0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f', RH, 'Relay/App 代币交付金库（双向：入=市场买入；转给它=同 tx 原子落池卖出）', 'bridge', 'exclude')
a('0xe72688f7d25d7318b9a81f21edda640ca948c83b', RH, 'RobinHoodSettler（App 交易结算器，原子过手末余额 0）', 'infra', 'exclude')
a('0xabb2acd3be814a80e502575d6c1dc5f789e9cd10', RH, '公共 relayer（代发交易）', 'infra', 'exclude')
a('0xb477751b76cf82d00a686a1232f5fcd772414af3', RH, 'LiFiDiamond（跨链聚合路由，原子过手）', 'bridge', 'exclude')
a('0xcaf681a66d020601342297493863e78c959e5cb2', RH, 'Uniswap SwapRouter02', 'router', 'exclude')
a('0xd9ec2db5f3d1b236843925949fe5bd8a3836fccb', RH, '主流 meme 发射台工厂（fee 流向 per-launch 可变，现场实测）', 'launchpad', 'exclude')
a('0x7e035fb048a31e0481b88074557415b1c187242b', RH, '发射台基建部署者 EOA', 'launchpad', 'exclude')
a('0x26605f322f7ff986f381bb9a6e3f5dab0beaeb09', RH, 'Flap（flap.sh）Portal v5.14+（第三家发射台）', 'launchpad', 'exclude')
a('0x09ad820aac5779683b481c4674208a4e1b024afa', RH, 'DexAggregatorCore（已验证；池买→分发用户，存量零）', 'router', 'exclude')
a('0x20f6ee51340adeed01a59b0e65cb3703f3dc860c', RH, 'DexAggregator（聚合器外层，与 Core 互转是内部结构）', 'router', 'exclude')
a('0x56c262027e0de4aea31d2489529cb25d23e58a8b', RH, 'bot relayer（全链 14 万+笔代发 swap，按 swap.to 归因）', 'infra', 'exclude')
a('0xa67d7eb4dc68fa6ce8e34ef8cadaf075b9893fbb', RH, 'bot relayer（同上，币对级）', 'infra', 'exclude')
a('0x91604f590d66ace8975eed6bd16cf55647d1c499', RH, '尘埃 gas 出纳服务（发尘埃 gas→收款者秒级交易；gas 边一律降级）', 'infra', 'exclude')
a('0x32487287c65f11d53bbca89c2472171eb09bf337', RH, 'Virtuals 平台回购机器（TWAP buyback bot，150+ agent 币系统组件）', 'platform', 'exclude')
a('0xe4a0015b4c12f84bf9b8b9db56b7ef0bc539d88f', RH, 'Virtuals 平台部署管理员/funder（掌握工厂与执行器权限）', 'platform', 'exclude')
a('0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc', RH, '公共狙击 bot 执行代理（1500+ 独立用户，共用≠关联）', 'bot-service', 'exclude')
a('0x8876789976decbfcbbbe364623c63652db8c0904', RH, 'Uniswap UniversalRouter（92 万+笔）', 'router', 'exclude')
a('0x53bf6b0684ec7ef91e1387da3d1a1769bc5a6f77', RH, 'Uniswap UniversalRouter 第二部署（设施剔除两个都要含）', 'router', 'exclude')
a('0x73991a25c818bf1f1128deaab1492d45638de0d3', RH, 'Uniswap V3 NonfungiblePositionManager（从它收币=LP 提取非买入）', 'protocol', 'exclude')
a('0x81f7ca6af86d1ca6335e44a2c28bc88807491415', RH, 'Virtuals 跨项目 keeper EOA（50% 锁仓分配器+ACF 分账）', 'platform', 'exclude')
a('0x3eb3394f5d89465a77f73a83d3675b0ed051f852', RH, 'Virtuals 平台批量执行合约（ACF 阶梯挂单执行器）', 'platform', 'exclude')
a('0x8a19963649b2fc3d50c951953f89bcbfbd5f0b51', RH, 'Virtuals 内盘 bonding router（真实买卖家=同 tx 终端）', 'platform', 'exclude')
a('0xd4ccbfa37e2f35611b3042e4096ad7a3459bd007', RH, 'Virtuals TokenFactory/铸币分发', 'platform', 'exclude')
a('0x6d80b81d9fc56a7a839b1af9006eb49151961ce7', RH, 'Virtuals AgentTaxV2 税合约（70% creator/30% 平台）', 'platform', 'exclude')
a('0xf36f0dd7b6b1730d0a59d1f3fd0e494c4d5c66e8', RH, 'Virtuals 税 swapper（机械卖回执行腿，单列勿算庄家出货）', 'platform', 'exclude')
a('0x000000e200088d55c39a11f609e5f667729ad49b', RH, 'Uniswap 官方 UERC20Factory（第 4 类发射台）', 'launchpad', 'exclude')
a('0x00004c4ccc709ef590f7c81102c0689f0263d4e9', RH, 'Uniswap 官方 LiquidityLauncher', 'launchpad', 'exclude')
a('0x000000001f26a0044baa66024e7b6599c61963f8', RH, 'Uniswap 官方 CCA 工厂 v2.1.0（auction 实例 per-launch）', 'launchpad', 'exclude')
a('0x05d552391067389ee44fec3924157ed33f976000', RH, 'Uniswap 官方 LBPStrategy v3.1.0 单例（过手全部发射盘勿当大户）', 'launchpad', 'exclude')
a('0x9be3cc594a47d90148b9f65466c57600018d237c', RH, '公共 bot 卖币执行合约（"经同一合约出货"永不构成协同证据）', 'bot-service', 'exclude')
a('0x2a7f3d7486641c77600b9b9256132755c8aebb4f', RH, '公共 bot 卖币执行合约（同模板；按 txfrom 穿透真实卖家）', 'bot-service', 'exclude')
a('0x68be5163fdd75ecad02aee1c9242e8afc8e95c8d', RH, '公共 bot 卖币执行合约第三部署（同模板）', 'bot-service', 'exclude')
a('0xb01ca24bd01be40ee950a8746cf7546134442049', RH, '公共 swap bot 合约（双向；0.99 ETH 默认参数指纹≠同一运营者）', 'bot-service', 'exclude')
a('0x2ca37ff95caf25366ef16fc2e655b78a165d125f', RH, '公共工具合约（12.5KB 未验证；"漏斗"定性前先 getCode）', 'bot-service', 'exclude')
a('0x5d6395cde0e26aa97fcf3a8004439f29a9124d5c', RH, '公共工具合约（21.6KB 未验证）', 'bot-service', 'exclude')
a('0x3da66157309794822c1506702a9c966fd9612773', RH, '原子中转小合约（同 tx 同额转发，假集群元凶）', 'bot-service', 'exclude')
a('0xa58bdd0ab5ebbb8dc425090fea8fd0ba969c1668', RH, '路由/中转合约组（100% 同 tx 进出）', 'bot-service', 'exclude')
a('0x71f2f1c2dc94cdabfe29cb355119f8683ae0969b', RH, 'NOXA 平台金库 treasury.noxa.eth（多币费归集+平台自营币发射者；WETH 收入为多币混合口径）', 'project-treasury', 'identity', ev='BEGGAR 核验 2026-07-17：ENS 双向解析+创始人推文自认')
a('0x69957a4b1b97adb44742bb2f0f736f196960a83a', RH, 'NOXA 平台出纳机器人（每5分钟自动归集；ETH 分发名单=官方关联仓发现通道；gas 边不可作私有聚类）', 'infra', 'exclude', ev='BEGGAR 核验 2026-07-17')
a('0x7f03effbd7ceb22a3f80dd468f67ef27826acd85', RH, 'NOXA LaunchLocker（LP NFT 托管+费分成；ERC-721 转出=撤池信号）', 'locker', 'identity', ev='BEGGAR 核验 2026-07-17：已验证合约')
a('0xd7aaa32920ebca1ef9b9bc684f519da56b37503d', RH, '公共卖币执行合约（66 txfrom 同 tx 等额进出落池）', 'bot-service', 'exclude', ev='BEGGAR 核验 2026-07-17')
a('0x7b021ceb65edaf40ed73c51e78cf44ad4edf99a4', RH, '路由/中转合约组', 'bot-service', 'exclude')
a('0x48a097df16c7844a33b1c3d11ab353457846e13f', RH, '路由/中转合约组', 'bot-service', 'exclude')
a('0x50ad1c820290c9cc694dd47b0a61323f4d163e7e', RH, '路由/中转合约组', 'bot-service', 'exclude')
a('0x4e5ffb3bd801d9db9a98daee7d4293afd46da677', RH, '路由/中转合约组', 'bot-service', 'exclude')
a('0x58daec3116aae6d93017baaea7749052e8a04fa7', RH, 'Uniswap V4 PositionManager（keeper 形态替所有发射盘建池）', 'protocol', 'exclude')
a('0xe6cae83bde06e4c305530e199d7217f42808555b', RH, 'Robinhood 钱包 EIP-7702 标准实现（海量散户共用）', 'infra', 'exclude')
a('0xe492912f37c2a4eca45d42dc67548f4c6cd7ce2b', RH, '买入代理合约（IN 全来自 PoolManager、OUT 分发 300+ 址）', 'bot-service', 'exclude')
a('0x3f43479c8536f7ee8180d0f67a050980dc5bc8c8', RH, 'batchTransferNative 批量转账工具（判关联看单笔 payload）', 'infra', 'exclude')
a('0xd29c85f15df544ba632c9e25829fd29d767d7978', RH, 'Across 桥 Universal_SpokePool（跨链入金通道之三）', 'bridge', 'exclude')
a('0x243a17063102c29fb60aa930db199d4b73ab8a37', RH, '公共热钱包/托管结算设施（大户转给它=经它卖出/托管过手，勿判私人分仓）', 'infra', 'exclude', date='2026-07-17', ev='Pointless 二次增量核验：8万+笔高频')
a('0xb0999731f7c2581844658a9d2ced1be0077b7397', RH, '公共 bot 服务费收集地址（"共同下游"不构成关联）', 'bot-service', 'exclude')
a('0xcdca5d374e46a6dddab50bd2d9acb8c796ec35c3', RH, 'Chainlink CCIP OffRamp（桥入代币统一 txto）', 'bridge', 'exclude')
a('0x78680385fcb8187ac1b28e0d6b1e0acf5e0d0992', RH, 'CCIP 桥出收集通道（收币→同链 burn；转给它=桥出回主链）', 'bridge', 'exclude')
a('0x43e4c17b15365596caae8e7d00e42bc8e988c2d4', RH, 'Virtuals TokenFactory 直连分发代理（常设分发枢纽）', 'platform', 'exclude')

# ===== 通用 burn 地址（全 EVM 链） =====
a('0x0000000000000000000000000000000000000000', EVM3 + ('robinhood',), '零地址（burn/mint 对手方）', 'burn', 'exclude', ev='协议常识')
a('0x000000000000000000000000000000000000dead', EVM3 + ('robinhood',), 'dead 销毁地址', 'burn', 'exclude', ev='协议常识')
a('0x0000000000000000000000000000000000000001', EVM3, '0x…01 黑洞地址', 'burn', 'exclude', ev='协议常识')
# SOL 系统性地址
a('11111111111111111111111111111111', ('sol',), 'System Program', 'program', 'exclude', ev='协议常识')
a('1nc1nerator11111111111111111111111111111111', ('sol',), 'Incinerator 销毁地址', 'burn', 'exclude', ev='协议常识')

# ===== 知名 KOL 公开地址（2026-07-16 本轮搜集核验） =====
a('HUpPyLU8KWisCAr3mzWy2FKT6uuxQ2qGgJQxyTpDoes5', ('sol',), '0xSun（@0xSunNFT，链上打新头部 KOL）', 'kol', 'identity',
  date='2026-07-16', ev='本人推特自证 x.com/0xSunNFT/status/1805980670227066921；TRUMP 战绩报道多源吻合【置信:高】')
a('G1pRtSyKuWSjTqRDcazzKBDzqEF96i1xSURpiXj3yFcc', ('sol',), '加密D哥（中文车头/打新 KOL）', 'kol', 'identity',
  date='2026-07-16', ev='社区标注 x.com/sol123eth/status/1922641254363582725（单源推文，用前核验）【置信:中】')
a('Ay9wnuZCRTceZJuRpGZnuwYZuWdsviM4cMiCwFoSQiPH', ('sol',), '冷静哥（中文车头/打新 KOL）', 'kol', 'identity',
  date='2026-07-16', ev='社区标注 x.com/sol123eth/status/1922641254363582725（单源推文，用前核验）【置信:中】')
a('8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6', ('sol',), 'cooker（中文车头/打新 KOL）', 'kol', 'identity',
  date='2026-07-16', ev='社区标注 x.com/sol123eth/status/1922641254363582725（单源推文，用前核验）【置信:中】')

# ===== Hyperliquid（地址簿 HL 段；v4 起 resolver 支持 hyperliquid 链，check_manual_sync 首跑抓出的漏同步） =====
a('0x43e9abea1910387c4292bca4b94de81462f8a251', ('hyperliquid',), 'Hyperliquid 团队地址', 'fund', 'identity',
  ev='address-book HL 段（HYPE 分析核验 2026-07）')
a('0xd57ecca444a9acb7208d286be439de12dd09de5d', ('hyperliquid',), 'Hyper Foundation', 'fund', 'identity',
  ev='address-book HL 段（HYPE 分析核验 2026-07）')

# ===== 核心锁仓合约（locker 快速档 2026-07-16 亲验补录；锁仓量是有经济含义的供应——识别不剔除，
# 聚类合并边禁用由 labels_resolver.no_merge 负责） =====
a('0x407993575c91ce7643a4d4ccacc9a98c36ee1bbe', ('bsc',), 'Pinksale: PinkLock V2（合约名 PinkLock02，106万笔 Lock/Unlock；BSC meme 最高频锁仓设施）',
  'locker', 'identity', date='2026-07-16', ev='bscscan 官方标签亲验 2026-07-16')
a('0xe2fe530c047f2d85298b07d9333c05737f1435fb', ('eth',), 'TrustSwap: Team Finance Lock（AdminUpgradeabilityProxy，托管 266+ 币种）',
  'locker', 'identity', date='2026-07-16', ev='etherscan 官方标签亲验 2026-07-16')
a('0xe2fe530c047f2d85298b07d9333c05737f1435fb', ('bsc',), 'Team Finance Lock（BSC 同址部署，合约名 LockToken；无官方名标签）',
  'locker', 'identity', date='2026-07-16', ev='bscscan 合约名+Lock/Withdraw 交易史亲验 2026-07-16')

with open('manual_labels.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['address', 'chain', 'name', 'category', 'tier', 'source',
                                      'added_date', 'evidence', 'risk_flags', 'merge_policy',
                                      'balance_policy', 'source_snapshot_at', 'verified_at',
                                      'status', 'raw_labels'])
    for r in R:
        for k in ('risk_flags', 'merge_policy', 'balance_policy', 'source_snapshot_at',
                  'verified_at', 'status', 'raw_labels'):
            r.setdefault(k, '')
    w.writeheader(); w.writerows(R)
print('manual_labels.csv rows:', len(R))
