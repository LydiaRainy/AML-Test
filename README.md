# LucidAML

**可解释的区块链反洗钱检测引擎**

> Unlike black-box AML solutions, LucidAML provides full explainability for every risk score.

---

## 快速开始

```bash
# 安装依赖
pip install requests flask flask-cors

# 分析 ETH 地址
cd compliance_engine
python analyze.py 0x098B716B8Aaf21512996dC57EB0615e2383E2f96

# 分析 BTC 地址
python analyze.py btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf

# 启动前端 API
python db.py

# 打开前端
open ../dashboard_v2.html
```

---

## 文件结构

```
stbc/
├── dashboard_v2.html          前端界面（多地址队列 + 图谱 + 审计）
├── README.md
└── compliance_engine/
    ├── analyze.py             主入口（ETH + BTC）
    ├── collector.py           ETH 数据采集（Etherscan V2）
    ├── collector_btc.py       BTC 数据采集（Blockstream API）
    ├── graph.py               图结构 + Haircut 污染率
    ├── scorer.py              风险评分引擎
    ├── db.py                  SQLite 数据库 + Flask API
    ├── config.py              黑名单 + 参数配置
    └── detectors/
        ├── d_blacklist.py     OFAC / Lazarus 黑名单
        ├── d_peel_chain.py    C2  Peel Chain
        ├── d_smurfing.py      C1  Smurfing 拆单
        ├── d_fanout.py        C3  Fan-out 蜘蛛网
        ├── d_bipartite.py     C4  Bipartite 二分图
        ├── d_mixer.py         C5/C8  混币器
        ├── d_crosschain.py    D1/D2/D3  跨链桥
        ├── d_defi.py          E1–E4  DeFi 滥用
        ├── d_nft.py           E5  NFT 洗钱
        ├── d_dusting.py       G1  尘埃攻击
        ├── d_pig_butchering.py B4  猪杀盘
        ├── d_reverse_taint.py G2  反向污染
        ├── d_pagerank.py      No.25  PageRank 风险传播
        └── d_lof.py           No.26  LOF 异常检测
```

---

## 评分规则

### 跳数分（基础分）

| 条件 | 得分 |
|---|---|
| 直接交互黑名单（1跳） | 100 → 直接标 CRITICAL |
| 二跳内有黑名单 | +50 |
| 三跳内有黑名单 | +25 |

### 叠加分

| 条件 | 得分 |
|---|---|
| 混币器交互（Tornado Cash / Sinbad 等） | +30 |
| 不透明跨链桥 | +20 |
| 主动转出给黑名单地址 > 2 次 | +40 |
| 主动转出给黑名单地址 = 1 次 | +20 |
| 被动收到黑名单转入 > 2 次 | +10 |
| 被动收到黑名单转入 = 1 次 | +5 |
| OFAC 制裁交易所 | +25 |
| 透明桥 + 对端有黑名单 | +15 |
| 透明桥（对端无黑名单） | +5 |
| Smurfing 拆单 | +12 |
| 猪杀盘三段式 | +15 |
| DeFi 滥用 | +10 |
| NFT 洗钱 | +8 |

### 风险等级

| 得分 | 等级 |
|---|---|
| ≥ 100 或直接命中黑名单 | 🔴 CRITICAL |
| 60 – 99 | 🟠 HIGH |
| 30 – 59 | 🟡 MEDIUM |
| 0 – 29 | 🟢 LOW |

---

## 覆盖手法

基于慢雾 AML 供应商评估框架，链上可检测手法共 27 种：

| 编号 | 手法 | 状态 |
|---|---|---|
| B5 / OFAC | 制裁实体链上操作 | ✅ |
| B4 | 猪杀盘三段式 | ✅ |
| C1 | Smurfing 拆单 | ✅ |
| C2 | Peel Chain 剥皮链 | ✅ |
| C3 | Fan-out 蜘蛛网 | ✅ |
| C4 | Bipartite 二分图 | ✅ |
| C5 | ZK Mixer 混币器交互 | ✅ |
| C8 | Mixer-first Gas 资助 | ✅ |
| D1 | 透明跨链桥 | ✅ |
| D2 | 不透明跨链桥 | ✅ |
| D3 | 多链快速跳转 | ✅ |
| E1 | DEX 多次闪兑 | ✅ |
| E2 | 流动性池快速存取 | ✅ |
| E3 | Flash Loan | ✅ |
| E4 | Yield Farming 洗白 | ✅ |
| E5 | NFT Wash Trading | ✅ |
| G1 | Dusting Attack | ✅ |
| G2 | 反向污染攻击 | ✅ |
| No.25 | PageRank 风险传播 | ✅ |
| No.26 | LOF 异常检测 | ✅ |
| A1–A8 | 链下手法（赌博/OTC/钱庄） | ❌ 需链下数据 |
| H1–H5 | 出金手法 | ❌ 需 CEX 数据 |

---

## API

启动：`python compliance_engine/db.py`

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/analyze` | POST | 分析地址 `{"address", "hops"}` |
| `/api/db/list` | GET | 所有历史记录 |
| `/api/db/get/<address>` | GET | 单个地址完整报告 |
| `/api/db/stats` | GET | 数据库统计 |
| `/api/blacklist` | GET/POST | 黑名单管理 |
| `/api/watchlist` | GET/POST | 监控名单管理 |

---

## 测试地址

```bash
# 高风险 — Lazarus Ronin Bridge（期望 CRITICAL）
python analyze.py 0x098B716B8Aaf21512996dC57EB0615e2383E2f96 3

# 灰度 — Stake.com 赌博平台（期望 MEDIUM）
python analyze.py 0x974CaA59029e46ec2393e2c454e6cc0d51e24d40 1

# 安全 — Binance 热钱包（期望 LOW）
python analyze.py 0x28c6c06298d514db089934071355e5743bf21d60 1
```

---

## 参考资料

- Vitalik et al. (2023) — [Privacy Pools](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4563364)
- BIS Bulletin No.111 (2025) — Haircut vs Poison 污染率模型
- FATF (2024) — 隐私币与虚拟资产风险评估
- 慢雾 — [Crypto AML 供应商评估 Checklist](https://github.com/slowmist/Cryptocurrency-AML-Checklist)
- tayvano — [Lazarus/DPRK 研究库](https://github.com/tayvano/lazarus-bluenoroff-research)
- Hong Kong AMLO Cap.615 / VASP 发牌制度 2023
- HKMA 港元稳定币监管框架咨询文件 2024

---

## 团队

City University of Hong Kong
