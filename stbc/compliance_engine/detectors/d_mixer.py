# ============================================================
# detectors/d_mixer.py
# 混币器交互检测
# 覆盖：No.07 链上混币器, No.08 Mixer-first Gas资助
# ============================================================

from config import KNOWN_MIXERS, BLACKLIST


def detect(nodes, edges, eth_txs=None, target_address=None, **kwargs):
    """
    检测两种混币相关模式：

    No.07 直接与 Mixer 合约交互
    No.08 首笔 Gas ETH 来自 Mixer 输出地址

    返回：
      detected:      bool
      severity:      HIGH
      mixer_interactions: 直接与 Mixer 交互记录
      gas_funding:   Gas 来源分析
    """
    results = {}

    # ── No.07 直接 Mixer 交互 ─────────────────────────────────
    mixer_hits = []
    for (f, t, v, ts, typ) in edges:
        if t in KNOWN_MIXERS:
            mixer_hits.append({
                "direction": "deposit",
                "mixer":     t,
                "label":     KNOWN_MIXERS[t],
                "from":      f,
                "value":     v,
                "ts":        ts,
            })
        if f in KNOWN_MIXERS:
            mixer_hits.append({
                "direction": "withdraw",
                "mixer":     f,
                "label":     KNOWN_MIXERS[f],
                "to":        t,
                "value":     v,
                "ts":        ts,
            })

    results["mixer_interactions"] = {
        "detected": bool(mixer_hits),
        "count":    len(mixer_hits),
        "hits":     mixer_hits[:5],
    }

    # ── No.08 Mixer-first Gas 资助 ────────────────────────────
    gas_result = {"detected": False}

    if eth_txs and target_address:
        addr = target_address.lower()
        # 找第一笔收到 ETH 的交易
        incoming = sorted(
            [tx for tx in eth_txs
             if tx.get("to", "").lower() == addr
             and int(tx.get("value", 0) or 0) > 0],
            key=lambda x: int(x.get("blockNumber", 0) or 0)
        )
        if incoming:
            first_src = incoming[0].get("from", "").lower()
            if first_src in KNOWN_MIXERS:
                gas_result = {
                    "detected": True,
                    "source":   first_src,
                    "label":    KNOWN_MIXERS[first_src],
                    "severity": "HIGH",
                }
            elif first_src in BLACKLIST:
                gas_result = {
                    "detected": True,
                    "source":   first_src,
                    "label":    BLACKLIST[first_src],
                    "severity": "HIGH",
                }

    results["gas_funding"] = gas_result

    # 综合判断
    any_detected = (
        results["mixer_interactions"]["detected"]
        or results["gas_funding"]["detected"]
    )

    if not any_detected:
        return {"detected": False}

    return {
        "detected":  True,
        "severity":  "HIGH",
        "results":   results,
        "summary": (
            f"混币器交互 {len(mixer_hits)} 次"
            + (" + Gas来源可疑" if gas_result["detected"] else "")
        ),
    }
