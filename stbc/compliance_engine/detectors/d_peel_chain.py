# ============================================================
# detectors/d_peel_chain.py
# Peel Chain 剥皮链检测
# 覆盖：No.03 Peel Chain
# 特征：入度=1，出度=1，深度>10，每跳余额递减
# ============================================================

from config import DETECTOR_CONFIG


def detect(nodes, edges, **kwargs):
    """
    检测 Peel Chain 模式

    算法：
      1. 找所有入度=1且出度=1的节点（候选节点）
      2. 建 next 映射
      3. 从每个候选节点出发，沿 next 找最长连续链
      4. 链长 >= min_depth 则触发

    返回：
      detected:      bool
      severity:      HIGH / MEDIUM
      chains:        所有检测到的链
      longest_chain: 最长链的详情
    """
    min_depth  = DETECTOR_CONFIG["peel_chain_min_depth"]
    high_depth = DETECTOR_CONFIG["peel_chain_high_depth"]

    # 候选节点：入度=1且出度=1
    candidates = {
        addr for addr, info in nodes.items()
        if info["in_count"] == 1 and info["out_count"] == 1
    }

    if not candidates:
        return {"detected": False}

    # 建 next 映射（每个候选节点发出的那条边的目标）
    next_map = {}
    for (f, t, v, ts, typ) in edges:
        if f in candidates:
            next_map[f] = t

    # 找连续链
    visited = set()
    chains  = []

    for start in candidates:
        if start in visited:
            continue
        chain = [start]
        cur   = start
        while (cur in next_map
               and next_map[cur] in candidates
               and next_map[cur] not in visited):
            cur = next_map[cur]
            chain.append(cur)
            visited.add(cur)

        if len(chain) >= min_depth:
            chains.append(chain)

    if not chains:
        return {"detected": False}

    chains.sort(key=len, reverse=True)
    longest = chains[0]

    return {
        "detected":       True,
        "severity":       "HIGH" if len(longest) >= high_depth else "MEDIUM",
        "chain_count":    len(chains),
        "longest_length": len(longest),
        "longest_sample": longest[:8],
        "all_chains":     [c[:5] for c in chains[:5]],
        "summary": (
            f"检测到 {len(chains)} 条剥皮链，"
            f"最长 {len(longest)} 跳"
        ),
    }
