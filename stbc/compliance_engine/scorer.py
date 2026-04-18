# ============================================================
# scorer.py
# 汇总所有检测器结果，输出最终风险评分
# ============================================================

from graph import calculate_taint
from config import TAINT_THRESHOLD_HIGH, TAINT_THRESHOLD_MEDIUM

# 每个检测器的权重（影响最终风险分）
DETECTOR_WEIGHTS = {
    "blacklist":       40,   # 最高，直接黑名单
    "mixer":           30,   # 混币器交互
    "reverse_taint":   20,   # 与黑名单交互
    "peel_chain":      15,   # Peel Chain
    "fanout":          15,   # 蜘蛛网
    "smurfing":        12,   # 拆单
    "bipartite":       12,   # 二分图
    "pagerank":        10,   # PageRank分
    "defi":            8,    # DeFi滥用
    "pig_butchering":  8,    # 猪杀盘
    "nft":             6,    # NFT洗钱
    "dusting":         5,    # 尘埃攻击
    "lof":             5,    # LOF异常
}


def score(address, nodes, edges, detector_results, eth_txs=None):
    """
    综合所有检测器结果，输出：
      risk_level:    CRITICAL / HIGH / MEDIUM / LOW
      risk_score:    0 ~ 100
      taint_rate:    Haircut 污染率 %
      triggered:     命中的检测器列表
      summary:       摘要
    """
    # 1. 污染率
    taint = calculate_taint(address, nodes, edges)

    # 2. 从检测器结果累积风险分
    raw_score = 0
    triggered = []

    for name, result in detector_results.items():
        if not isinstance(result, dict) or not result.get("detected"):
            continue

        weight   = DETECTOR_WEIGHTS.get(name, 5)
        severity = result.get("severity", "MEDIUM")

        multiplier = {"CRITICAL": 1.0, "HIGH": 0.8,
                      "MEDIUM": 0.5, "LOW": 0.2}.get(severity, 0.5)

        raw_score += weight * multiplier
        triggered.append({
            "detector": name,
            "severity": severity,
            "summary":  result.get("summary", ""),
        })

    # 3. 污染率加分
    if taint > TAINT_THRESHOLD_HIGH:
        raw_score += 30
    elif taint > TAINT_THRESHOLD_MEDIUM:
        raw_score += 15

    # 4. 归一化到 0~100
    risk_score = min(99, int(raw_score))

    # 5. 风险等级
    if risk_score >= 70 or taint > TAINT_THRESHOLD_HIGH:
        risk_level = "CRITICAL"
    elif risk_score >= 40 or taint > TAINT_THRESHOLD_MEDIUM:
        risk_level = "HIGH"
    elif risk_score >= 15:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # 直接黑名单命中强制 CRITICAL
    if detector_results.get("blacklist", {}).get("detected"):
        risk_level = "CRITICAL"
        risk_score = max(risk_score, 90)

    triggered.sort(
        key=lambda x: {"CRITICAL": 0, "HIGH": 1,
                       "MEDIUM": 2, "LOW": 3}.get(x["severity"], 4)
    )

    return {
        "address":    address.lower(),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "taint_rate": taint,
        "triggered":  triggered,
        "summary": (
            f"{risk_level} | 风险分 {risk_score}/100 "
            f"| 污染率 {taint}% "
            f"| {len(triggered)} 个手法命中"
        ),
    }
