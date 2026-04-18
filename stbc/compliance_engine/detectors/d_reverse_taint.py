# ============================================================
# detectors/d_reverse_taint.py
# 反向污染 / 被动收款检测
# 特征：目标地址被动收到来自黑名单地址的转账
#       区分主动（我去找黑名单地址）vs 被动（黑名单地址来找我）
# ============================================================

from config import BLACKLIST, KNOWN_MIXERS


def detect(nodes, edges, target_address=None, **kwargs):
    """
    检测反向污染和被动收款

    主动交互（HIGH）：目标地址主动发钱给黑名单
    被动收款（MEDIUM）：黑名单地址主动发钱给目标（可能是污染攻击）

    返回：
      detected:   bool
      severity:   HIGH / MEDIUM
      active:     主动交互记录
      passive:    被动收款记录
    """
    if not target_address:
        return {"detected": False}

    addr   = target_address.lower()
    active  = []
    passive = []

    for (f, t, v, ts, typ) in edges:
        f_is_black = f in BLACKLIST or f in KNOWN_MIXERS
        t_is_black = t in BLACKLIST or t in KNOWN_MIXERS

        # 主动：目标地址发给黑名单
        if f == addr and t_is_black:
            active.append({
                "direction": "sent_to_blacklist",
                "target":    t,
                "label":     BLACKLIST.get(t) or KNOWN_MIXERS.get(t),
                "value":     v,
                "ts":        ts,
                "type":      typ,
            })

        # 被动：黑名单发给目标地址
        if t == addr and f_is_black:
            passive.append({
                "direction": "received_from_blacklist",
                "source":    f,
                "label":     BLACKLIST.get(f) or KNOWN_MIXERS.get(f),
                "value":     v,
                "ts":        ts,
                "type":      typ,
                "note":      "可能是反向污染攻击，需人工核查",
            })

    if not active and not passive:
        return {"detected": False}

    severity = "HIGH" if active else "MEDIUM"

    return {
        "detected":      True,
        "severity":      severity,
        "active_count":  len(active),
        "passive_count": len(passive),
        "active":        active[:5],
        "passive":       passive[:5],
        "summary": (
            (f"主动交互黑名单 {len(active)} 次" if active else "")
            + (" | " if active and passive else "")
            + (f"被动收款自黑名单 {len(passive)} 次" if passive else "")
        ),
    }
