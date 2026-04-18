# ============================================================
# detectors/d_fanout.py
# Fan-in → Fan-out 蜘蛛网检测
# 覆盖：No.04 Fan-in → Fan-out
# 特征：高入度高出度，中转地址生命周期<1小时
# ============================================================

from config import DETECTOR_CONFIG


def detect(nodes, edges, **kwargs):
    """
    检测蜘蛛网中转模式

    算法：
      1. 找入度 >= min_in 且出度 >= min_out 的节点
      2. 计算生命周期（last_seen - first_seen）
      3. 生命周期 < max_lifetime 的节点触发
      4. 额外检查：所有目标地址是否同时首次出现

    返回：
      detected: bool
      severity: HIGH / MEDIUM
      hubs:     所有检测到的中转节点
    """
    min_in      = DETECTOR_CONFIG["fanout_min_in"]
    min_out     = DETECTOR_CONFIG["fanout_min_out"]
    max_lt      = DETECTOR_CONFIG["fanout_max_lifetime"]

    hubs = []

    for addr, info in nodes.items():
        if info["in_count"] < min_in or info["out_count"] < min_out:
            continue

        lifetime = info["last_seen"] - info["first_seen"]
        if lifetime > max_lt:
            continue

        # 找这个节点的所有目标地址
        targets = list(set(
            t for (f, t, v, ts, typ) in edges
            if f == addr
        ))

        # 找所有来源地址
        sources = list(set(
            f for (f, t, v, ts, typ) in edges
            if t == addr
        ))

        # 检查目标地址是否同时首次出现（更强的信号）
        target_first_seen = [
            nodes.get(t, {}).get("first_seen", 0)
            for t in targets
        ]
        simultaneous = (
            len(set(target_first_seen)) <= 2
            and len(target_first_seen) >= 3
        )

        hubs.append({
            "address":     addr,
            "in_count":    info["in_count"],
            "out_count":   info["out_count"],
            "lifetime":    lifetime,
            "sources":     sources[:5],
            "targets":     targets[:5],
            "simultaneous_activation": simultaneous,
            "severity":    "HIGH" if simultaneous else "MEDIUM",
        })

    if not hubs:
        return {"detected": False}

    hubs.sort(key=lambda x: x["in_count"] + x["out_count"], reverse=True)
    top_severity = "HIGH" if any(h["severity"] == "HIGH" for h in hubs) else "MEDIUM"

    return {
        "detected":  True,
        "severity":  top_severity,
        "hub_count": len(hubs),
        "hubs":      hubs[:5],
        "summary":   f"检测到 {len(hubs)} 个蜘蛛网中转节点",
    }
