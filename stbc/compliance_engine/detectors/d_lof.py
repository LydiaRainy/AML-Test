# ============================================================
# detectors/d_lof.py
# 局部离群因子（LOF）异常检测
# 覆盖：No.26 LOF异常检测
# 基于交易频率、金额分布、对手方多样性计算离群程度
# ============================================================

import math
from collections import defaultdict


def detect(nodes, edges, target_address=None, **kwargs):
    """
    LOF 异常检测

    特征向量（每个地址）：
      1. 交易频率（tx_per_day）
      2. 平均交易金额
      3. 金额标准差
      4. 对手方多样性（唯一对手方数量）
      5. 入出比（in_count / out_count）

    算法：
      1. 计算所有地址的特征向量
      2. 计算目标地址与其他地址的距离
      3. LOF 分数 > 2.0 = 异常

    返回：
      detected:    bool
      severity:    HIGH / MEDIUM
      lof_score:   目标地址的 LOF 分数
      anomalies:   所有异常地址
    """
    if len(nodes) < 5:
        return {"detected": False}

    # 建特征向量
    features = {}
    counterparts = defaultdict(set)  # 每个地址的唯一对手方

    for (f, t, v, ts, typ) in edges:
        counterparts[f].add(t)
        counterparts[t].add(f)

    for addr, info in nodes.items():
        # 交易时间跨度（天）
        span_days = max(
            1,
            (info["last_seen"] - info["first_seen"]) / 86400
        )
        total_tx = info["in_count"] + info["out_count"]

        # 该地址的所有交易金额
        vals = [v for (f, t, v, ts, typ) in edges
                if (f == addr or t == addr) and v > 0]

        avg_val = sum(vals) / len(vals) if vals else 0
        std_val = (
            math.sqrt(sum((v - avg_val) ** 2 for v in vals) / len(vals))
            if len(vals) > 1 else 0
        )

        in_out_ratio = (
            info["in_count"] / max(1, info["out_count"])
        )

        features[addr] = {
            "tx_per_day":     total_tx / span_days,
            "avg_val":        avg_val,
            "std_val":        std_val,
            "counterparts":   len(counterparts.get(addr, set())),
            "in_out_ratio":   in_out_ratio,
        }

    def distance(a, b):
        """欧氏距离（归一化）"""
        fa, fb = features[a], features[b]
        keys   = ["tx_per_day", "avg_val", "std_val",
                  "counterparts", "in_out_ratio"]
        diffs  = []
        for k in keys:
            va, vb = fa[k], fb[k]
            maxv   = max(abs(va), abs(vb), 1)
            diffs.append(((va - vb) / maxv) ** 2)
        return math.sqrt(sum(diffs))

    def lof_score(addr, k=5):
        """计算一个地址的 LOF 分数"""
        all_addrs = [a for a in features if a != addr]
        if len(all_addrs) < k:
            return 1.0

        # k 近邻
        dists   = sorted([(distance(addr, a), a) for a in all_addrs])
        knn     = [a for _, a in dists[:k]]
        k_dist  = dists[k-1][0] if len(dists) >= k else dists[-1][0]

        # 可达距离
        def reach_dist(a, b):
            return max(distance(a, b), k_dist)

        # 局部可达密度
        def lrd(a):
            neighbors = sorted(
                [(distance(a, x), x) for x in all_addrs]
            )[:k]
            sum_rd = sum(reach_dist(a, n) for _, n in neighbors)
            return k / max(sum_rd, 1e-10)

        lrd_addr = lrd(addr)
        avg_lrd_knn = sum(lrd(n) for n in knn) / max(len(knn), 1)

        return avg_lrd_knn / max(lrd_addr, 1e-10)

    LOF_THRESHOLD = 2.0

    # 计算所有地址的 LOF 分
    anomalies = []
    target_score = 1.0

    # 只计算活跃节点（避免计算量爆炸）
    active_nodes = sorted(
        nodes.keys(),
        key=lambda a: nodes[a]["in_count"] + nodes[a]["out_count"],
        reverse=True
    )[:100]

    for addr in active_nodes:
        score = lof_score(addr)
        if score > LOF_THRESHOLD:
            anomalies.append({
                "address":   addr,
                "lof_score": round(score, 3),
                "features":  {
                    k: round(v, 2)
                    for k, v in features[addr].items()
                },
            })
        if target_address and addr == target_address.lower():
            target_score = score

    anomalies.sort(key=lambda x: x["lof_score"], reverse=True)

    if not anomalies and target_score <= LOF_THRESHOLD:
        return {"detected": False}

    severity = (
        "HIGH"   if target_score > 4.0 else
        "MEDIUM" if target_score > LOF_THRESHOLD else
        "LOW"
    )

    return {
        "detected":     True,
        "severity":     severity,
        "target_score": round(target_score, 3),
        "anomaly_count": len(anomalies),
        "anomalies":    anomalies[:5],
        "summary": (
            f"LOF 分数: {round(target_score, 3)}"
            f"，{len(anomalies)} 个异常节点"
        ),
    }
