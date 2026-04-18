# ============================================================
# detectors/d_blacklist.py
# 黑名单直查 + 已知实体检测
# 覆盖：No.23 Lazarus模式, OFAC制裁地址
# ============================================================

from config import BLACKLIST, KNOWN_MIXERS, KNOWN_GAMBLING, KNOWN_BRIDGES


def detect(nodes, edges, **kwargs):
    """
    检测图中是否存在已知黑名单地址
    包括：OFAC制裁、Lazarus、Tornado Cash、Mixer、赌博合约、跨链桥

    返回：
      detected:  bool
      severity:  CRITICAL / HIGH / MEDIUM
      hits:      命中的地址列表
    """
    hits = []

    for addr, info in nodes.items():
        # OFAC 黑名单
        if addr in BLACKLIST:
            hits.append({
                "address":  addr,
                "type":     "BLACKLIST",
                "label":    BLACKLIST[addr],
                "severity": "CRITICAL",
            })

        # 已知 Mixer 合约
        elif addr in KNOWN_MIXERS:
            hits.append({
                "address":  addr,
                "type":     "MIXER",
                "label":    KNOWN_MIXERS[addr],
                "severity": "HIGH",
            })

        # 赌博合约
        elif addr in KNOWN_GAMBLING:
            hits.append({
                "address":  addr,
                "type":     "GAMBLING",
                "label":    KNOWN_GAMBLING[addr],
                "severity": "MEDIUM",
            })

        # 已知跨链桥
        elif addr in KNOWN_BRIDGES:
            hits.append({
                "address":  addr,
                "type":     "BRIDGE",
                "label":    KNOWN_BRIDGES[addr],
                "severity": "LOW",
            })

    if not hits:
        return {"detected": False}

    # 最高严重等级
    severities = [h["severity"] for h in hits]
    top = ("CRITICAL" if "CRITICAL" in severities
           else "HIGH" if "HIGH" in severities
           else "MEDIUM")

    return {
        "detected":  True,
        "severity":  top,
        "hits":      hits,
        "summary":   f"命中 {len(hits)} 个已知风险地址",
    }
