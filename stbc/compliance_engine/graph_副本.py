# ============================================================
# graph.py
# 把原始交易数据建成图结构
# 节点 = 地址，边 = 转账关系
# ============================================================

from collections import defaultdict
from config import BLACKLIST, KNOWN_MIXERS, KNOWN_GAMBLING, KNOWN_BRIDGES


def safe_int(x):
    if x is None: return 0
    if isinstance(x, int): return x
    s = str(x).strip().lower()
    if s in ("", "0x"): return 0
    try:
        return int(s, 16) if s.startswith("0x") else int(s)
    except:
        return 0


# ============================================================
# 核心：建图
# ============================================================

def build_graph(eth_txs, int_txs, token_txs):
    """
    从三种交易数据建图

    节点结构：
      addr -> {
        first_seen:    int,   第一笔交易时间戳
        last_seen:     int,   最后一笔交易时间戳
        in_count:      int,   收款次数
        out_count:     int,   发款次数
        in_value:      int,   总收款金额（wei/最小单位）
        out_value:     int,   总发款金额
        tokens:        set,   交互过的币种
        is_blacklist:  bool,  是否在黑名单
        is_mixer:      bool,  是否是 Mixer 合约
        is_gambling:   bool,  是否是赌博合约
        is_bridge:     bool,  是否是跨链桥
        labels:        list,  所有标签
      }

    边结构：
      (from, to, value, timestamp, type/symbol)
      type: ETH / INT / USDT / USDC / ...
    """
    nodes = {}
    edges = []

    def upsert_node(addr, ts):
        """创建或更新节点"""
        a = addr.lower().strip()
        if not a or a == "0x":
            return None
        if a not in nodes:
            nodes[a] = {
                "first_seen":   ts,
                "last_seen":    ts,
                "in_count":     0,
                "out_count":    0,
                "in_value":     0,
                "out_value":    0,
                "tokens":       set(),
                "is_blacklist": a in BLACKLIST,
                "is_mixer":     a in KNOWN_MIXERS,
                "is_gambling":  a in KNOWN_GAMBLING,
                "is_bridge":    a in KNOWN_BRIDGES,
                "labels":       _get_labels(a),
            }
        else:
            nodes[a]["first_seen"] = min(nodes[a]["first_seen"], ts)
            nodes[a]["last_seen"]  = max(nodes[a]["last_seen"],  ts)
        return a

    def add_edge(frm, to, val, ts, typ):
        """添加一条边，同时更新节点统计"""
        f = upsert_node(frm, ts)
        t = upsert_node(to,  ts)
        if not f or not t:
            return
        nodes[f]["out_count"] += 1
        nodes[f]["out_value"] += val
        nodes[t]["in_count"]  += 1
        nodes[t]["in_value"]  += val
        # 记录币种（ETH和内部交易不算token）
        if typ not in ("ETH", "INT"):
            nodes[f]["tokens"].add(typ)
            nodes[t]["tokens"].add(typ)
        edges.append((f, t, val, ts, typ))

    # ETH 普通交易
    for tx in eth_txs:
        if tx.get("isError", "0") == "1":
            continue
        add_edge(
            tx.get("from", ""),
            tx.get("to",   ""),
            safe_int(tx.get("value", 0)),
            safe_int(tx.get("timeStamp", 0)),
            "ETH"
        )

    # 内部交易（合约调用产生的ETH转账）
    for tx in int_txs:
        if tx.get("isError", "0") == "1":
            continue
        add_edge(
            tx.get("from", ""),
            tx.get("to",   ""),
            safe_int(tx.get("value", 0)),
            safe_int(tx.get("timeStamp", 0)),
            "INT"
        )

    # ERC20 全币种
    for tx in token_txs:
        symbol = tx.get("tokenSymbol", "?")
        add_edge(
            tx.get("from", ""),
            tx.get("to",   ""),
            safe_int(tx.get("value", 0)),
            safe_int(tx.get("timeStamp", 0)),
            symbol
        )

    return nodes, edges


def _get_labels(addr):
    """给地址打上所有已知标签"""
    labels = []
    if addr in BLACKLIST:
        labels.append(BLACKLIST[addr])
    if addr in KNOWN_MIXERS:
        labels.append(f"Mixer: {KNOWN_MIXERS[addr]}")
    if addr in KNOWN_GAMBLING:
        labels.append(f"Gambling: {KNOWN_GAMBLING[addr]}")
    if addr in KNOWN_BRIDGES:
        labels.append(f"Bridge: {KNOWN_BRIDGES[addr]}")
    return labels


# ============================================================
# 合并多个图（多跳追踪时用）
# ============================================================

def merge_graphs(base_nodes, base_edges, new_nodes, new_edges):
    """
    把新图合并进基础图
    节点：累加统计数据
    边：直接追加（允许重复，之后去重）
    """
    for addr, info in new_nodes.items():
        if addr not in base_nodes:
            base_nodes[addr] = info
        else:
            base_nodes[addr]["in_count"]  += info["in_count"]
            base_nodes[addr]["out_count"] += info["out_count"]
            base_nodes[addr]["in_value"]  += info["in_value"]
            base_nodes[addr]["out_value"] += info["out_value"]
            base_nodes[addr]["tokens"]    |= info["tokens"]
            base_nodes[addr]["first_seen"] = min(
                base_nodes[addr]["first_seen"], info["first_seen"]
            )
            base_nodes[addr]["last_seen"] = max(
                base_nodes[addr]["last_seen"], info["last_seen"]
            )
    base_edges += new_edges
    return base_nodes, base_edges


# ============================================================
# 图分析工具函数
# ============================================================

def get_neighbors(addr, edges, direction="both"):
    """
    获取一个地址的邻居
    direction: "in"=来源, "out"=去向, "both"=全部
    """
    addr = addr.lower()
    neighbors = set()
    for (f, t, v, ts, typ) in edges:
        if direction in ("in", "both") and t == addr:
            neighbors.add(f)
        if direction in ("out", "both") and f == addr:
            neighbors.add(t)
    return neighbors


def get_subgraph(addr, edges, hops=2):
    """
    以某个地址为中心，提取 N 跳内的子图
    用于可视化和局部分析
    """
    visited = set()
    frontier = {addr.lower()}

    for _ in range(hops):
        new_frontier = set()
        for node in frontier:
            new_frontier |= get_neighbors(node, edges, "both")
        frontier = new_frontier - visited
        visited |= frontier

    visited.add(addr.lower())

    # 过滤出子图边
    sub_edges = [
        (f, t, v, ts, typ) for f, t, v, ts, typ in edges
        if f in visited and t in visited
    ]
    return visited, sub_edges


def find_linear_chains(nodes, edges):
    """
    找出所有入度=1且出度=1的线性链
    用于 C2 Peel Chain 检测
    返回：[(chain1), (chain2), ...]
    """
    # 入度=1且出度=1的候选节点
    candidates = {
        addr for addr, info in nodes.items()
        if info["in_count"] == 1 and info["out_count"] == 1
    }

    # 建 next 映射
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
        if len(chain) >= 3:
            chains.append(chain)

    return sorted(chains, key=len, reverse=True)


def find_hub_nodes(nodes, min_in=5, min_out=5, max_lifetime=3600):
    """
    找出高入度高出度且短生命周期的中转节点
    用于 C3 Fan-out 检测
    """
    hubs = []
    for addr, info in nodes.items():
        if (info["in_count"] >= min_in
                and info["out_count"] >= min_out):
            lifetime = info["last_seen"] - info["first_seen"]
            if lifetime <= max_lifetime:
                hubs.append({
                    "address":  addr,
                    "in":       info["in_count"],
                    "out":      info["out_count"],
                    "lifetime": lifetime,
                    "labels":   info["labels"],
                })
    return sorted(hubs, key=lambda x: x["in"] + x["out"], reverse=True)


def find_bipartite_pattern(nodes, edges):
    """
    找出二分图模式（C4）
    两组地址集合只在组间交互，不在组内交互
    两侧同时首次激活
    """
    # 找同时激活的地址组（同一时间戳首次出现）
    by_first_seen = defaultdict(list)
    for addr, info in nodes.items():
        by_first_seen[info["first_seen"]].append(addr)

    # 找同时激活超过3个地址的时间点
    suspicious_groups = {
        ts: addrs
        for ts, addrs in by_first_seen.items()
        if len(addrs) >= 3
    }

    results = []
    for ts, group in suspicious_groups.items():
        # 检查这组地址是否只和组外地址交互
        group_set = set(group)
        internal_edges = [
            (f, t) for f, t, *_ in edges
            if f in group_set and t in group_set
        ]
        external_edges = [
            (f, t) for f, t, *_ in edges
            if (f in group_set) != (t in group_set)  # XOR
        ]

        # 没有内部边，只有外部边 = 二分图特征
        if len(internal_edges) == 0 and len(external_edges) >= 3:
            results.append({
                "timestamp":      ts,
                "group":          list(group_set),
                "external_edges": len(external_edges),
                "severity":       "MEDIUM",
            })

    return results


def calculate_taint(address, nodes, edges, max_hops=5):
    """
    Haircut 污染率计算
    黑名单地址的污染率 = 1.0
    污染按转账比例向下游传播
    最多传播 max_hops 跳

    返回：目标地址的污染率（0.0 ~ 1.0）
    """
    addr = address.lower()

    # 初始化：黑名单地址污染率=1，其他=0
    taint = {}
    for a, info in nodes.items():
        taint[a] = 1.0 if info["is_blacklist"] else 0.0

    # 按时间顺序传播污染
    sorted_edges = sorted(edges, key=lambda x: x[3])

    for hop in range(max_hops):
        updated = False
        for (f, t, v, ts, typ) in sorted_edges:
            if f not in taint or taint[f] <= 0:
                continue
            total_out = nodes.get(f, {}).get("out_value", 1) or 1
            new_taint = taint[f] * (v / total_out)
            old_taint = taint.get(t, 0.0)
            merged    = min(1.0, old_taint + new_taint)
            if merged > old_taint:
                taint[t] = merged
                updated  = True
        if not updated:
            break

    return round(taint.get(addr, 0.0) * 100, 2)


# ============================================================
# 图转 JSON（给前端用）
# ============================================================

def graph_to_json(nodes, edges, max_nodes=200, max_edges=500):
    """
    把图结构转成前端可以直接用的 JSON 格式
    节点颜色编码：
      红色 = 黑名单
      橙色 = Mixer
      黄色 = 赌博
      蓝色 = 桥
      灰色 = 普通
    """
    def node_color(info):
        if info["is_blacklist"]: return "#ef4444"   # 红
        if info["is_mixer"]:     return "#f59e0b"   # 橙
        if info["is_gambling"]:  return "#8b5cf6"   # 紫
        if info["is_bridge"]:    return "#3b82f6"   # 蓝
        return "#64748b"                             # 灰

    def node_size(info):
        total = info["in_count"] + info["out_count"]
        return max(10, min(50, total))

    # 按活跃度排序，取前 max_nodes 个
    sorted_nodes = sorted(
        nodes.items(),
        key=lambda x: x[1]["in_count"] + x[1]["out_count"],
        reverse=True
    )[:max_nodes]

    node_set = {addr for addr, _ in sorted_nodes}

    json_nodes = [
        {
            "id":     addr,
            "name":   addr[:10] + "...",
            "color":  node_color(info),
            "size":   node_size(info),
            "labels": info["labels"],
            "stats": {
                "in_count":  info["in_count"],
                "out_count": info["out_count"],
                "tokens":    list(info["tokens"])[:5],
                "lifetime":  info["last_seen"] - info["first_seen"],
            }
        }
        for addr, info in sorted_nodes
    ]

    # 只保留两端节点都在集合内的边
    json_edges = [
        {
            "source": f,
            "target": t,
            "value":  v,
            "type":   typ,
        }
        for f, t, v, ts, typ in edges[:max_edges]
        if f in node_set and t in node_set
    ]

    return {
        "nodes": json_nodes,
        "edges": json_edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "shown_nodes": len(json_nodes),
            "shown_edges": len(json_edges),
        }
    }


# ============================================================
# 图摘要（用于报告）
# ============================================================

def graph_summary(nodes, edges):
    """
    生成图的统计摘要
    """
    blacklist_nodes = [a for a, i in nodes.items() if i["is_blacklist"]]
    mixer_nodes     = [a for a, i in nodes.items() if i["is_mixer"]]
    all_tokens      = set()
    for _, info in nodes.items():
        all_tokens |= info["tokens"]

    return {
        "total_nodes":      len(nodes),
        "total_edges":      len(edges),
        "blacklist_nodes":  len(blacklist_nodes),
        "mixer_nodes":      len(mixer_nodes),
        "tokens_seen":      list(all_tokens)[:20],
        "blacklist_list":   blacklist_nodes[:10],
    }
