# ============================================================
# detectors/d_pagerank.py
# PageRank 风险传播评分
# 覆盖：No.25 多源PageRank风险评分
# 从已知黑名单地址出发，沿交易图传播风险分
# ============================================================

from config import BLACKLIST, KNOWN_MIXERS


def detect(nodes, edges, target_address=None, **kwargs):
    """
    PageRank 风险评分

    算法：
      1. 从黑名单地址出发，初始风险分 = 1.0
      2. 沿交易边传播：目标节点分数 += 来源分数 × 权重
      3. 权重 = 转账金额 / 来源地址总出账金额
      4. 迭代 N 次直到收敛
      5. 输出目标地址的最终风险分

    返回：
      detected:     bool
      severity:     HIGH / MEDIUM / LOW
      risk_score:   0.0 ~ 1.0
      top_risk_nodes: 风险最高的节点
    """
    if not nodes or not edges:
        return {"detected": False}

    DAMPING    = 0.85   # 阻尼系数
    ITERATIONS = 20     # 迭代次数
    THRESHOLD  = 0.1    # 触发阈值

    # 初始化风险分
    risk = {}
    for addr in nodes:
        if addr in BLACKLIST or addr in KNOWN_MIXERS:
            risk[addr] = 1.0
        else:
            risk[addr] = 0.0

    # 建出边权重表
    # out_weight[from][to] = 这条边的权重（金额/总出账）
    out_weight = {}
    for (f, t, v, ts, typ) in edges:
        if f not in out_weight:
            out_weight[f] = {}
        if t not in out_weight[f]:
            out_weight[f][t] = 0
        out_weight[f][t] += v

    # 归一化（转成比例）
    for f, targets in out_weight.items():
        total = sum(targets.values()) or 1
        for t in targets:
            out_weight[f][t] = out_weight[f][t] / total

    # 迭代传播
    for _ in range(ITERATIONS):
        new_risk = {addr: risk[addr] for addr in nodes}

        for (f, t, v, ts, typ) in edges:
            if f not in risk or risk[f] <= 0:
                continue
            weight      = out_weight.get(f, {}).get(t, 0)
            propagated  = risk[f] * weight * DAMPING
            new_risk[t] = min(1.0, new_risk.get(t, 0) + propagated)

        risk = new_risk

    # 目标地址风险分
    target_score = 0.0
    if target_address:
        target_score = risk.get(target_address.lower(), 0.0)

    # Top 10 高风险节点
    top_nodes = sorted(
        [(addr, score) for addr, score in risk.items() if score > THRESHOLD],
        key=lambda x: x[1],
        reverse=True
    )[:10]

    if target_score < THRESHOLD and not top_nodes:
        return {"detected": False}

    severity = (
        "HIGH"   if target_score >= 0.5 else
        "MEDIUM" if target_score >= THRESHOLD else
        "LOW"
    )

    return {
        "detected":       target_score >= THRESHOLD or bool(top_nodes),
        "severity":       severity,
        "target_score":   round(target_score, 4),
        "top_risk_nodes": [
            {"address": addr, "score": round(score, 4)}
            for addr, score in top_nodes
        ],
        "summary": (
            f"PageRank 风险分: {round(target_score, 4)}"
            f"，高风险节点: {len(top_nodes)} 个"
        ),
    }
