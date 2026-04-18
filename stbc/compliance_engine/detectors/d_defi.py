# ============================================================
# detectors/d_defi.py
# DeFi 滥用检测
# 覆盖：No.12 DEX闪电兑换, No.13 流动性池存取,
#       No.14 Flash Loan, No.15 Yield Farming
# ============================================================

from collections import defaultdict
from config import DETECTOR_CONFIG


# 已知 DEX 路由合约
KNOWN_DEX = {
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3 Router",
    "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "SushiSwap Router",
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch Router",
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x Exchange",
    "0x6131b5fae19ea4f9d964eac0408e4408b66337b5": "KyberSwap Router",
    "0xe66b31678d6c16e9ebf358268a790b763c133750": "Curve Router",
}

# 已知闪电贷合约
KNOWN_FLASHLOAN = {
    "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9": "Aave V2 Lending Pool",
    "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": "Aave V3 Pool",
    "0xc3d688b66703497daa19211eedff47f25384cdc3": "Compound V3",
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984": "dYdX",
}

# 已知 Yield 协议
KNOWN_YIELD = {
    "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419": "Yearn Finance",
    "0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b": "Compound",
    "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": "Aave Token",
}


def detect(nodes, edges, token_txs=None, eth_txs=None, **kwargs):
    """
    检测四种 DeFi 滥用模式

    返回：
      detected:    bool
      severity:    HIGH / MEDIUM
      dex_swap:    No.12 DEX闪电兑换结果
      rapid_lp:    No.13 流动性池快速存取结果
      flash_loan:  No.14 闪电贷结果
      yield_farm:  No.15 Yield Farming结果
    """
    results = {}

    # ── No.12 DEX 多次闪兑 ────────────────────────────────────
    results["dex_swap"] = _detect_dex_swap(nodes, edges, token_txs)

    # ── No.13 流动性池快速存取 ────────────────────────────────
    results["rapid_lp"] = _detect_rapid_lp(token_txs)

    # ── No.14 Flash Loan ─────────────────────────────────────
    results["flash_loan"] = _detect_flash_loan(nodes, edges, eth_txs)

    # ── No.15 Yield Farming ───────────────────────────────────
    results["yield_farm"] = _detect_yield_farming(nodes, edges, token_txs)

    any_detected = any(v.get("detected") for v in results.values())
    if not any_detected:
        return {"detected": False}

    severities = [v.get("severity", "LOW") for v in results.values()
                  if v.get("detected")]
    top = ("HIGH" if "HIGH" in severities else "MEDIUM")

    detected_names = [k for k, v in results.items() if v.get("detected")]

    return {
        "detected":       True,
        "severity":       top,
        "results":        results,
        "detected_types": detected_names,
        "summary":        f"DeFi 滥用：{', '.join(detected_names)}",
    }


def _detect_dex_swap(nodes, edges, token_txs):
    """No.12：1小时内换了4种以上token"""
    window       = DETECTOR_CONFIG["token_swap_window"]
    min_tokens   = DETECTOR_CONFIG["token_swap_min_tokens"]

    if not token_txs:
        return {"detected": False}

    by_addr = defaultdict(list)
    for tx in token_txs:
        addr   = tx.get("from", "").lower()
        symbol = tx.get("tokenSymbol", "?")
        ts     = int(tx.get("timeStamp", 0) or 0)
        by_addr[addr].append((symbol, ts))

    patterns = []
    for addr, txs in by_addr.items():
        txs_sorted = sorted(txs, key=lambda x: x[1])
        for i, (sym, ts) in enumerate(txs_sorted):
            window_txs = [(s, t) for s, t in txs_sorted
                          if ts <= t <= ts + window]
            tokens_in_window = set(s for s, _ in window_txs)
            if len(tokens_in_window) >= min_tokens:
                patterns.append({
                    "address":     addr,
                    "token_count": len(tokens_in_window),
                    "tokens":      list(tokens_in_window)[:8],
                    "window_txs":  len(window_txs),
                })
                break

    if not patterns:
        return {"detected": False}

    return {
        "detected":  True,
        "severity":  "MEDIUM",
        "patterns":  patterns[:3],
        "summary":   f"{len(patterns)} 个地址在1小时内频繁换币",
    }


def _detect_rapid_lp(token_txs):
    """No.13：同一地址对同一合约30分钟内存取"""
    max_hold = DETECTOR_CONFIG["rapid_lp_max_hold"]

    if not token_txs:
        return {"detected": False}

    by_pair = defaultdict(list)
    for tx in token_txs:
        frm      = tx.get("from", "").lower()
        to       = tx.get("to",   "").lower()
        ts       = int(tx.get("timeStamp", 0) or 0)
        contract = tx.get("contractAddress", "").lower()
        by_pair[(frm, contract)].append(("out", ts))
        by_pair[(to,  contract)].append(("in",  ts))

    incidents = []
    for (addr, contract), events in by_pair.items():
        ins  = sorted(t for typ, t in events if typ == "in")
        outs = sorted(t for typ, t in events if typ == "out")
        for t_in in ins:
            for t_out in outs:
                if 0 < t_out - t_in < max_hold:
                    incidents.append({
                        "address":   addr,
                        "contract":  contract,
                        "held_secs": t_out - t_in,
                    })
                    break

    if not incidents:
        return {"detected": False}

    return {
        "detected":  True,
        "severity":  "MEDIUM",
        "incidents": incidents[:3],
        "summary":   f"{len(incidents)} 次极短时间 LP 存取",
    }


def _detect_flash_loan(nodes, edges, eth_txs):
    """No.14：与已知闪电贷合约交互"""
    hits = []
    for addr in nodes:
        if addr in KNOWN_FLASHLOAN:
            hits.append({
                "contract": addr,
                "label":    KNOWN_FLASHLOAN[addr],
            })

    if not hits:
        return {"detected": False}

    return {
        "detected": True,
        "severity": "MEDIUM",
        "hits":     hits,
        "summary":  f"与 {len(hits)} 个闪电贷合约交互",
    }


def _detect_yield_farming(nodes, edges, token_txs):
    """No.15：与 Yield 协议反复存取"""
    hits = []
    for addr in nodes:
        if addr in KNOWN_YIELD:
            hits.append({
                "protocol": addr,
                "label":    KNOWN_YIELD[addr],
            })

    if not hits:
        return {"detected": False}

    # 检查是否有反复存取（同一协议交互超过3次）
    protocol_interaction_count = defaultdict(int)
    for (f, t, v, ts, typ) in edges:
        if t in KNOWN_YIELD:
            protocol_interaction_count[t] += 1
        if f in KNOWN_YIELD:
            protocol_interaction_count[f] += 1

    repeated = {p: c for p, c in protocol_interaction_count.items() if c >= 3}

    return {
        "detected": True,
        "severity": "MEDIUM" if not repeated else "HIGH",
        "hits":     hits,
        "repeated": repeated,
        "summary":  f"与 {len(hits)} 个 Yield 协议交互",
    }
