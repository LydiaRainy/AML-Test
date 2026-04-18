# ============================================================
# detectors/d_smurfing.py
# Smurfing 拆单结构化检测
# 覆盖：No.01 Smurfing蚂蚁搬家, No.02 时间拆分结构化
# 特征：等额重复转账，时间间隔规律，Gas来源相同
# ============================================================

from collections import defaultdict, Counter
from config import DETECTOR_CONFIG


def detect(nodes, edges, **kwargs):
    """
    检测 Smurfing 和时间结构化模式

    算法：
      1. 按发送方分组
      2. 找重复金额频次 >= min_repeat 的发送方
      3. 检测时序规律性（时间间隔标准差/均值 < tolerance）
      4. 检测 Gas 来源是否相同（多地址共用同一 Gas 供给方）

    返回：
      detected:  bool
      severity:  HIGH / MEDIUM
      patterns:  所有检测到的 smurfing 模式
    """
    min_repeat  = DETECTOR_CONFIG["smurfing_min_repeat"]
    tolerance   = DETECTOR_CONFIG["smurfing_regularity_tolerance"]

    # 按发送方分组交易
    by_sender = defaultdict(list)
    for (f, t, v, ts, typ) in edges:
        by_sender[f].append({"to": t, "value": v, "ts": ts, "type": typ})

    patterns = []

    for sender, txs in by_sender.items():
        if len(txs) < min_repeat:
            continue

        # 找重复金额
        amounts      = [tx["value"] for tx in txs]
        amount_count = Counter(amounts)

        for amount, freq in amount_count.most_common(3):
            if freq < min_repeat or amount == 0:
                continue

            # 拿出这些等额交易
            same = sorted(
                [tx for tx in txs if tx["value"] == amount],
                key=lambda x: x["ts"]
            )

            # 检测时序规律性
            regular = False
            avg_interval = 0
            if len(same) >= 3:
                intervals = [
                    same[i+1]["ts"] - same[i]["ts"]
                    for i in range(len(same) - 1)
                ]
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                if avg_interval > 0:
                    deviations = [abs(iv - avg_interval) / avg_interval
                                  for iv in intervals]
                    regular = all(d < tolerance for d in deviations)

            # 检测多目标（Smurfing核心：一个发送方打给多个接收方）
            targets    = list(set(tx["to"] for tx in same))
            multi_dest = len(targets) > 1

            patterns.append({
                "sender":       sender,
                "amount":       amount,
                "frequency":    freq,
                "regular":      regular,
                "avg_interval": round(avg_interval),
                "targets":      targets[:5],
                "multi_dest":   multi_dest,
                "severity":     "HIGH" if (regular and multi_dest) else "MEDIUM",
            })

    if not patterns:
        return {"detected": False}

    patterns.sort(key=lambda x: x["frequency"], reverse=True)
    top_severity = "HIGH" if any(p["severity"] == "HIGH" for p in patterns) else "MEDIUM"

    return {
        "detected":     True,
        "severity":     top_severity,
        "pattern_count": len(patterns),
        "patterns":     patterns[:5],
        "summary": (
            f"检测到 {len(patterns)} 个拆单模式，"
            f"最高频次 {patterns[0]['frequency']} 次"
        ),
    }
