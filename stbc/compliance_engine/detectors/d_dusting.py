# ============================================================
# detectors/d_dusting.py
# 尘埃攻击检测
# 覆盖：No.20 Dusting Attack
# 特征：收到大量来自同一来源的微额转账
# ============================================================

from collections import defaultdict
from config import DETECTOR_CONFIG


def detect(nodes, edges, target_address=None, **kwargs):
    """
    检测尘埃攻击

    算法：
      1. 找发向目标地址的微额转账（< max_value_eth）
      2. 按来源地址分组
      3. 同一来源发出 >= min_count 笔微额转账 = 尘埃攻击
      4. 额外检查：目标地址之后是否有归并操作（暴露关联）

    返回：
      detected:   bool
      severity:   MEDIUM
      dustings:   检测到的尘埃攻击
      merged:     是否发生了归并操作（更高风险）
    """
    # 1 ETH = 1e18 wei
    max_val   = int(DETECTOR_CONFIG["dusting_max_value_eth"] * 1e18)
    min_count = DETECTOR_CONFIG["dusting_min_count"]

    # 找所有微额入账
    dust_by_source = defaultdict(list)
    for (f, t, v, ts, typ) in edges:
        if v <= max_val and v > 0:
            if target_address and t == target_address.lower():
                dust_by_source[f].append({
                    "value": v, "ts": ts, "type": typ
                })

    # 找来源发了 >= min_count 笔微额的
    dustings = []
    for source, txs in dust_by_source.items():
        if len(txs) >= min_count:
            dustings.append({
                "source":    source,
                "count":     len(txs),
                "total_val": sum(tx["value"] for tx in txs),
                "txs":       txs[:3],
            })

    if not dustings:
        return {"detected": False}

    # 检查归并操作（目标地址之后是否把这些小额转出去了）
    merged = False
    if target_address:
        addr = target_address.lower()
        outgoing_after_dust = [
            (f, t, v, ts, typ) for (f, t, v, ts, typ) in edges
            if f == addr and v > 0
        ]
        if outgoing_after_dust:
            merged = True  # 有出账行为，可能发生了归并

    return {
        "detected":     True,
        "severity":     "HIGH" if merged else "MEDIUM",
        "dustings":     dustings[:3],
        "merged":       merged,
        "total_dust_tx": sum(d["count"] for d in dustings),
        "summary": (
            f"检测到 {len(dustings)} 个尘埃攻击来源"
            + ("，已发生归并操作（高风险）" if merged else "")
        ),
    }
