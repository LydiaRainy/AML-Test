# ============================================================
# detectors/d_pig_butchering.py
# 猪杀盘检测
# 覆盖：No.22 猪杀盘三段式
# 特征：小额初始 → 诱饵收益 → 大额归集 三段递增模式
# ============================================================

from collections import defaultdict


def detect(nodes, edges, target_address=None, **kwargs):
    """
    检测猪杀盘三段式模式

    三段特征：
      第一段：受害者收到小额初始转账（诱饵）
      第二段：受害者转出中等金额（"投资"）
      第三段：大额资金归集到特定地址

    算法：
      1. 找目标地址收到的小额入账（诱饵）
      2. 找目标地址之后的出账（投资行为）
      3. 检查出账是否流向同一汇聚节点
      4. 检查是否有递增模式（金额越来越大）

    返回：
      detected:  bool
      severity:  HIGH / MEDIUM
      stages:    三个阶段的详情
    """
    if not target_address:
        return {"detected": False}

    addr = target_address.lower()

    # 按时间排序所有和目标地址相关的交易
    related = sorted(
        [(f, t, v, ts, typ) for (f, t, v, ts, typ) in edges
         if f == addr or t == addr],
        key=lambda x: x[3]
    )

    if len(related) < 3:
        return {"detected": False}

    # 找入账和出账
    incoming = [(f, t, v, ts, typ) for (f, t, v, ts, typ) in related if t == addr]
    outgoing = [(f, t, v, ts, typ) for (f, t, v, ts, typ) in related if f == addr]

    if not incoming or not outgoing:
        return {"detected": False}

    # 检测三段式：
    # 第一段：最小的那笔入账（诱饵）
    min_in   = min(incoming, key=lambda x: x[2])
    # 第三段：最大的那笔出账（归集）
    max_out  = max(outgoing, key=lambda x: x[2])

    # 检查时序：诱饵 → 投资 → 归集
    if min_in[3] >= max_out[3]:  # 诱饵要比归集早
        return {"detected": False}

    # 检查金额递增
    out_values = sorted([v for f, t, v, ts, typ in outgoing])
    increasing = all(
        out_values[i] <= out_values[i+1]
        for i in range(len(out_values) - 1)
    )

    # 检查归集地址（多笔出账流向同一目标）
    out_targets   = defaultdict(int)
    out_target_val = defaultdict(int)
    for (f, t, v, ts, typ) in outgoing:
        out_targets[t]    += 1
        out_target_val[t] += v

    # 找最大归集节点
    top_target = max(out_target_val, key=out_target_val.get) if out_target_val else None
    top_count  = out_targets.get(top_target, 0)

    if top_count < 2 and not increasing:
        return {"detected": False}

    return {
        "detected":  True,
        "severity":  "HIGH" if increasing and top_count >= 3 else "MEDIUM",
        "stages": {
            "stage1_bait": {
                "from":  min_in[0],
                "value": min_in[2],
                "ts":    min_in[3],
            },
            "stage2_invest": {
                "tx_count":   len(outgoing),
                "total_val":  sum(v for f, t, v, ts, typ in outgoing),
                "increasing": increasing,
            },
            "stage3_collect": {
                "target":    top_target,
                "tx_count":  top_count,
                "total_val": out_target_val.get(top_target, 0),
            },
        },
        "summary": (
            f"猪杀盘疑似三段式：诱饵 {min_in[2]} → "
            f"{'递增出账' if increasing else '出账'} → "
            f"归集至 {str(top_target)[:12]}..."
        ),
    }
