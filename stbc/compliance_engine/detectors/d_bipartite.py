# ============================================================
# detectors/d_bipartite.py
# 二分图检测
# 覆盖：No.06 Bipartite 二分图
# 特征：两组地址集合间来回流转，两侧同时首次激活
# ============================================================

from collections import defaultdict


def detect(nodes, edges, **kwargs):
    """
    检测二分图洗钱模式

    算法：
      1. 找同时首次激活的地址组（同一时间戳 ±60秒内）
      2. 检查这些地址之间是否只有跨组交互，没有组内交互
      3. 检查资金是否在两组间来回流转

    返回：
      detected: bool
      severity: HIGH / MEDIUM
      patterns: 所有检测到的二分图模式
    """
    # 按首次激活时间分组（60秒窗口内算"同时"）
    WINDOW = 60
    addr_by_time = defaultdict(list)
    for addr, info in nodes.items():
        bucket = (info["first_seen"] // WINDOW) * WINDOW
        addr_by_time[bucket].append(addr)

    patterns = []

    for ts, group in addr_by_time.items():
        if len(group) < 3:
            continue

        group_set = set(group)

        # 组内交互（不好）
        internal = [
            (f, t) for (f, t, v, ts2, typ) in edges
            if f in group_set and t in group_set
        ]

        # 跨组交互
        external_out = [
            (f, t) for (f, t, v, ts2, typ) in edges
            if f in group_set and t not in group_set
        ]
        external_in = [
            (f, t) for (f, t, v, ts2, typ) in edges
            if f not in group_set and t in group_set
        ]

        # 二分图特征：没有内部交互，有双向外部交互
        if (len(internal) == 0
                and len(external_out) >= 2
                and len(external_in) >= 2):

            # 找外部对手方
            out_targets = list(set(t for _, t in external_out))
            in_sources  = list(set(f for f, _ in external_in))

            # 检查是否有来回流转（外部地址既发给组内也从组内收）
            bidirectional = set(out_targets) & set(in_sources)

            patterns.append({
                "timestamp":        ts,
                "group_addrs":      list(group_set)[:5],
                "group_size":       len(group_set),
                "external_out":     len(external_out),
                "external_in":      len(external_in),
                "bidirectional":    list(bidirectional)[:3],
                "severity":         "HIGH" if bidirectional else "MEDIUM",
            })

    if not patterns:
        return {"detected": False}

    patterns.sort(key=lambda x: x["group_size"], reverse=True)
    top_severity = "HIGH" if any(p["severity"] == "HIGH" for p in patterns) else "MEDIUM"

    return {
        "detected":      True,
        "severity":      top_severity,
        "pattern_count": len(patterns),
        "patterns":      patterns[:3],
        "summary":       f"检测到 {len(patterns)} 个二分图模式",
    }
