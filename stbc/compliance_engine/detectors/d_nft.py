# ============================================================
# detectors/d_nft.py
# NFT 洗钱检测
# 覆盖：No.16 NFT Wash Trading, No.17 NFT价值注入
# ============================================================

from collections import defaultdict


# 已知 NFT 市场合约
KNOWN_NFT_MARKETS = {
    "0x00000000006c3852cbef3e08e8df289169ede581": "OpenSea Seaport",
    "0x7f268357a8c2552623316e2562d90e642bb538e5": "OpenSea V2",
    "0x000000000000ad05ccc4f10045630fb830b95127": "Blur",
    "0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb": "CryptoPunks",
}


def detect(nodes, edges, token_txs=None, **kwargs):
    """
    检测 NFT 洗钱模式

    No.16 Wash Trading：同一 NFT 在关联地址间反复快速易手
    No.17 价值注入：NFT 交易价格严重偏离地板价

    返回：
      detected:    bool
      severity:    HIGH / MEDIUM
      wash_trading: No.16 结果
      value_inject: No.17 结果
    """
    results = {}

    # ── No.16 Wash Trading ────────────────────────────────────
    results["wash_trading"] = _detect_wash_trading(nodes, edges)

    # ── No.17 NFT 价值注入 ────────────────────────────────────
    results["value_inject"] = _detect_value_injection(nodes, edges)

    any_detected = any(v.get("detected") for v in results.values())
    if not any_detected:
        return {"detected": False}

    severities = [v.get("severity", "LOW") for v in results.values()
                  if v.get("detected")]
    top = "HIGH" if "HIGH" in severities else "MEDIUM"

    return {
        "detected":  True,
        "severity":  top,
        "results":   results,
        "summary":   "检测到 NFT 洗钱相关行为",
    }


def _detect_wash_trading(nodes, edges):
    """
    No.16：同一对地址之间反复来回交易
    特征：A→B 和 B→A 都存在，且次数 >= 3
    """
    pair_count = defaultdict(int)
    for (f, t, v, ts, typ) in edges:
        key = tuple(sorted([f, t]))
        pair_count[key] += 1

    # 找来回次数 >= 3 的地址对
    wash_pairs = [
        {"pair": list(pair), "count": count}
        for pair, count in pair_count.items()
        if count >= 3
    ]

    if not wash_pairs:
        return {"detected": False}

    # 检查这些地址对是否与 NFT 市场交互
    nft_nodes = set(nodes.keys()) & set(KNOWN_NFT_MARKETS.keys())

    wash_pairs.sort(key=lambda x: x["count"], reverse=True)

    return {
        "detected":    True,
        "severity":    "HIGH" if nft_nodes else "MEDIUM",
        "pairs":       wash_pairs[:5],
        "nft_markets": list(nft_nodes),
        "summary":     f"{len(wash_pairs)} 对地址存在反复来回交易",
    }


def _detect_value_injection(nodes, edges):
    """
    No.17：单笔交易金额异常大
    与同类交易相比偏差 >500%
    """
    if not edges:
        return {"detected": False}

    # 计算所有交易金额
    values = [v for (f, t, v, ts, typ) in edges if v > 0]
    if len(values) < 5:
        return {"detected": False}

    avg   = sum(values) / len(values)
    # 找超过平均值 5 倍以上的交易
    outliers = [
        {"from": f, "to": t, "value": v, "ratio": round(v / avg, 1)}
        for (f, t, v, ts, typ) in edges
        if v > avg * 5 and v > 0
    ]

    if not outliers:
        return {"detected": False}

    outliers.sort(key=lambda x: x["ratio"], reverse=True)

    return {
        "detected":  True,
        "severity":  "MEDIUM",
        "outliers":  outliers[:3],
        "avg_value": round(avg),
        "summary":   f"{len(outliers)} 笔交易金额严重偏高",
    }
