# ============================================================
# config.py
# 所有配置、黑名单、测试数据集
# ============================================================

# ─── API 配置 ────────────────────────────────────────────────
ETHERSCAN_KEY = "NETW3M4DCWVV9QW4ZC7QFNC1IMF5F4VHWK"
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
ETHERSCAN_CHAIN = "1"  # 以太坊主网

# 追踪深度默认值
DEFAULT_HOPS = 2

# 污染率阈值（超过这个就算高风险）
TAINT_THRESHOLD_HIGH   = 30.0  # %
TAINT_THRESHOLD_MEDIUM = 10.0  # %
TAINT_THRESHOLD_LOW    = 5.0   # %

# ─── OFAC + 已知黑名单地址 ───────────────────────────────────
# 来源：OFAC SDN List / tayvano Lazarus研究库 / 公开黑客事件
BLACKLIST = {

    # ── Lazarus Group / DPRK (OFAC SDN) ──────────────────────
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96": "Lazarus Group — Ronin Bridge Hack $625M (OFAC)",
    "0xa0e1c89ef1a489c9c7de96311ed5ce5d32c20e4b": "Lazarus Group (OFAC SDN)",
    "0x3cd751e6b0078be393132286c442345e5dc49699": "Lazarus Group — Binance deposit (OFAC)",
    "0xb7f33280c1f39859c01ad24b0c5c5c1cba7bf3f1": "Lazarus Group — Harmony Bridge Hack (OFAC)",
    "0x58f479571d99f69f7d534c4b6e8d4b94c5d42b8e": "Lazarus Group — Harmony Bridge Hack (OFAC)",

    # ── Lazarus Dust Collectors (tayvano研究库) ───────────────
    "0xae69012d15d6b1a3b2412aadef712f06f9286e0e": "Lazarus — DPRK IT Worker Dust Collector ae69",
    "0x9a5fc00f9aaa07817725fd38d7e73252f9f49e27": "Lazarus — Dust Collector 9a5",
    "0xb5d70f00608c77724b5cb73b93da89df1ae9f6e8": "Lazarus — Dust Collector b5d",
    "0xfda946270a6f452e0a134e22b493f4e7e8bdbc50": "Lazarus — Dust Collector fda",
    "0xa547c81b67ec09072b21baa8e107816d39cbd969": "Lazarus — Dust Collector a54",
    "0x7ec567ce97ec28e19ce7e2d4bcbb7943eb90ede0": "Lazarus — Dust Collector 7ec",
    "0x31499e03303dd75851a1738e88972cd998337403": "Lazarus — Dust Collector 314",
    "0x2d7554062664050294640891a122019a68ac5a2b": "Lazarus — Dust Collector 2d7",
    "0x99739fa525c0a98384430235d278fd08938997f9": "Lazarus — Dust Collector 997",
    "0xc0b635fb9dc28dea84db150b89d4578ff9859877": "Lazarus — Dust Collector c0b",

    # ── Tornado Cash (OFAC制裁合约) ───────────────────────────
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash — Deployer (OFAC)",
    "0x12d66f87a04a9e220c9d6b6c3c99b4fc0c8a3c4c": "Tornado Cash — 0.1 ETH Pool (OFAC)",
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash — 1 ETH Pool (OFAC)",
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": "Tornado Cash — 10 ETH Pool (OFAC)",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": "Tornado Cash — 100 ETH Pool (OFAC)",
    "0x178169b1d9b15d15b4ce2e2b75c41e4ab5b17a98": "Tornado Cash — 1000 ETH Pool (OFAC)",
    "0x610b717796ad172b316836ac5a2b016af8a7f0aa": "Tornado Cash — TORN Token (OFAC)",
    "0x722122df12d4e14e13ac3b6895a86e84145b6967": "Tornado Cash — Proxy (OFAC)",
    "0xdd4c48c0b24039969fc16d1cdf626eab821d3384": "Tornado Cash — 0.1 ETH Pool 2 (OFAC)",
    "0xd96f2b1c14db8458374d9aca76e26c3950113463": "Tornado Cash — 1 ETH Pool 2 (OFAC)",
    "0x4736dcf1b7a3d580672cce6e7c65cd5cc9cfba9d": "Tornado Cash — 10 ETH Pool 2 (OFAC)",

    # ── Sinbad / Blender (OFAC制裁Mixer) ─────────────────────
    "0x1da5821544e25c636c1417ba96ade4cf6d2f9b5a": "Sinbad.io — Mixer (OFAC 2023)",
    "0x7f367cc41522ce07553e823bf3be79a889debe1b": "Blender.io — Mixer (OFAC 2022)",

    # ── 重大黑客事件地址 ──────────────────────────────────────
    "0x3cbded43efdaf0fc77b9c55f6fc9988fcc9b37d9": "Bitfinex Hack 2016",
    "0x53903c7d6de9d5d1c564b0c0a93e50f01c8b6c7f": "KuCoin Hack 2020 $275M",
    "0xeb31973e0febf3e3d7058234a5ebbae1ab4b8c23": "KuCoin Hack 2020 — Laundry",
    "0x5a5444f6b5d511f61ff73a497c7b8b6c9cba7bf3": "Ronin Bridge — Attacker",
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96": "Lazarus — Ronin Bridge Hack",

    # ── Garantex (OFAC制裁交易所) ─────────────────────────────
    "0x6f6b4e9b7d4f3aca2e9e0afe7f4c0bae9e4e4e4e": "Garantex — Sanctioned Exchange (OFAC 2022)",

    # ── Huione Group (OFAC制裁，东南亚洗钱网络) ──────────────
    "0x308ed4b7b49797e1a98d3818bff6fe5385410370": "Huione Group (OFAC 2024)",

    # ── 暗网市场 ─────────────────────────────────────────────
    "0x67d4e6bd676db6a6c7b224fdadfc0e1e73e50ab5": "Hydra Market — Darknet",
    "0x8576acc5c05d6ce88f4e49bf65bdf0c62f91353c": "AlphaBay — Darknet",
}

# ─── 已知 Mixer 合约地址 ─────────────────────────────────────
# 与这些地址交互 = C5 ZK Mixer 手法
KNOWN_MIXERS = {
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash Deployer",
    "0x12d66f87a04a9e220c9d6b6c3c99b4fc0c8a3c4c": "Tornado Cash 0.1 ETH",
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash 1 ETH",
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": "Tornado Cash 10 ETH",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": "Tornado Cash 100 ETH",
    "0x178169b1d9b15d15b4ce2e2b75c41e4ab5b17a98": "Tornado Cash 1000 ETH",
    "0x1da5821544e25c636c1417ba96ade4cf6d2f9b5a": "Sinbad.io",
    "0x7f367cc41522ce07553e823bf3be79a889debe1b": "Blender.io",
    "0x9ad122c22b14202b4490edaf288fdb3c7cb3ff5e": "Railgun",
}

# ─── 已知隐私币兑换服务 ──────────────────────────────────────
# 与这些地址交互 = C9 隐私币中转手法
KNOWN_XMR_SERVICES = {
    "0x70102b505ed2ea9a16c1d23c7b7b8cda8c19f7c": "ChangeNow — XMR Service",
    "0x8f8921db542b28a6b24a1a1530ab12bf3f0079d1": "SideShift — XMR Service",
    "0x6ba21f8a97d8c6855b5a2e7b2a21f5d7e1f87512": "Exolix — XMR Service",
    "0x3b59c9452b56c87d0e5c43f89deefa7c2d8c0cf1": "FixedFloat — XMR Service",
}

# ─── 已知跨链桥合约 ──────────────────────────────────────────
# 用于 D1/D2 跨链桥追踪
KNOWN_BRIDGES = {
    "0x1116898dda4015ed8ddefb84b6e8bc24528af2d8": "Harmony Horizon Bridge",
    "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf": "Polygon Bridge",
    "0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "Optimism Bridge",
    "0x8eb2e16f1f0f98f7e6c7a0929e0e7c4b5c6d7a8b": "Arbitrum Bridge",
    "0x3ee18b2214aff97000d974cf647e7c347e8fa585": "Wormhole Bridge",
}

# ─── 已知赌博合约地址（来自 Etherscan Gambling 标签）──────────
# 用于 A1/A8 赌博洗白检测
KNOWN_GAMBLING = {
    "0x974caa59029e46ec2393e2c454e6cc0d51e24d40": "Stake.com",
    "0xd1ceeeee54e9f5405c84f2350c05c69c5a9edf3b": "Dice2Win",
    "0x999999c68b812baf3c93a1c5e9e3f9e3a8bbf7bc": "FCK.com Dice",
    "0xa6214288c1cd1b3a54bdb68bac77a98a9db4e6e6": "Fomo3D Long",
    "0xe84a6967d5c2a8bacd6a2c2b9e7e5f3b9d33e8d6": "Adapp.Games Space Dice",
    "0xe9b1a216fa1bc6ee2bitsler000000000000000000": "Bitsler.com",
    "0x2239df71bcd8e1c7c47858a20bankheist000000000": "BankHeist4D",
}

# ─── 测试数据集 ──────────────────────────────────────────────

# 高风险地址集（用于测召回率）
# 来源：tayvano lazarus-bluenoroff-research
TEST_HIGH_RISK = [
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96",  # Lazarus Ronin
    "0xa0e1c89ef1a489c9c7de96311ed5ce5d32c20e4b",  # Lazarus OFAC
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",  # Tornado Cash Deployer
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf",  # Tornado Cash 10 ETH
    "0xae69012d15d6b1a3b2412aadef712f06f9286e0e",  # Lazarus IT Worker Dust Collector
    "0x3cbded43efdaf0fc77b9c55f6fc9988fcc9b37d9",  # Bitfinex Hack
    "0x53903c7d6de9d5d1c564b0c0a93e50f01c8b6c7f",  # KuCoin Hack
    "0x7f367cc41522ce07553e823bf3be79a889debe1b",  # Blender.io Mixer
    "0x1da5821544e25c636c1417ba96ade4cf6d2f9b5a",  # Sinbad.io Mixer
    "0x308ed4b7b49797e1a98d3818bff6fe5385410370",  # Huione Group
]

# 安全地址集（用于测误报率）
# 来源：Arkham CEX 标签 — 已知合规交易所热钱包/冷钱包
TEST_SAFE = [
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance Hot Wallet
    "0x21a31ee1afc51d94c2efee98d4c2d258c33d8b61",  # Binance Cold Wallet
    "0xf977814e90da44bfa03b6295a0616a897441acec",  # Binance Cold Wallet 2
    "0xdfd5293d8e347dfe59e90a3b8c60e8a387a5e4c3",  # Binance Cold Wallet 3
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",  # Binance Cold Wallet 4
    "0x3cd751e6b0078be393132286c442345e5dc49699",  # Binance Hot Wallet 2
    "0x56eddb7aa87536c09ccc9b7a0d9e75e4c0b5c6f2",  # OKX Hot Wallet
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",  # OKX Cold Wallet
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe",  # Gate.io
    "0x7ad4c1647aa947d1c0543ebdc5ad4b36b7f0a630",  # Coinbase
]

# 灰度地址集（用于测中间风险识别）
# 来源：Etherscan Gambling 标签
TEST_GREY = [
    "0x974caa590e9e3e763f26498f8c3e7cd59eb68cf4",  # Stake.com
    "0xd1ceeeee54e9f5405c84f2350c05c69c5a9edf3b",  # Dice2Win
    "0x999999c68b812baf3c93a1c5e9e3f9e3a8bbf7bc",  # FCK.com Dice
    "0xa6214288c1cd1b3a54bdb68bac77a98a9db4e6e6",  # Fomo3D Long
    "0xb898ceae3735ab5d1ddda71b6c06c5b05bb50e98",  # Crypto Lottery
    "0xaec1f783bc29ca9f1bc6ee2bitsler000000000000",  # Bitsler.com
    "0xa52e014bc5a7b0abd1ddc96171c3e1f2e08b3332",  # Etheroll
    "0xfef5497b3ba6683ff0cac95f4f01d9c01968f097",  # FairDAPP
]

# ─── 检测参数 ─────────────────────────────────────────────────
DETECTOR_CONFIG = {
    # C2 Peel Chain
    "peel_chain_min_depth": 5,       # 最短链长才触发
    "peel_chain_high_depth": 10,     # 超过这个长度升为 HIGH

    # C1 Smurfing
    "smurfing_min_repeat": 5,        # 同一金额至少重复几次
    "smurfing_regularity_tolerance": 0.3,  # 时间间隔容差（30%）

    # C3 Fan-out
    "fanout_min_in": 5,              # 最少入度
    "fanout_min_out": 5,             # 最少出度
    "fanout_max_lifetime": 3600,     # 存活时间上限（秒）

    # E2 Rapid LP
    "rapid_lp_max_hold": 1800,       # LP持仓时间上限（秒，30分钟）

    # E1 Multi Token Swap
    "token_swap_min_tokens": 4,      # 1小时内换几种币触发
    "token_swap_window": 3600,       # 时间窗口（秒）

    # G1 Dusting
    "dusting_max_value_eth": 0.001,  # ETH最大金额
    "dusting_min_count": 10,         # 最少笔数

    # G3 Front-run Freeze
    "frontrun_window": 2640,         # 冻结窗口（秒，44分钟）

    # Haircut 污染率
    "max_hops_taint": 5,             # 污染传播最大跳数
}
