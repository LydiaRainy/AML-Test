# ============================================================
# Compliance Engine v3 — Jupyter
# ============================================================

import requests, time
from datetime import datetime
from collections import defaultdict, Counter

# ─── 配置 ───────────────────────────────────────────────────
API_KEY        = "YourKey"
TARGET_ADDRESS = "0x098B716B8Aaf21512996dC57EB0615e2383E2f96"
HOPS           = 2
# ────────────────────────────────────────────────────────────

# V2 接口 + chainid=1 (以太坊主网)
BASE    = "https://api.etherscan.io/v2/api"
CHAIN   = "1"
SESS    = requests.Session()
SESS.headers.update({"User-Agent": "compliance-engine/1.0"})

TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# ─── 黑名单 ──────────────────────────────────────────────────
BLACKLIST = {
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash Deployer",
    "0x12d66f87a04a9e220c9d6b6c3c99b4fc0c8a3c4c": "Tornado Cash 0.1 ETH",
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash 1 ETH",
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": "Tornado Cash 10 ETH",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": "Tornado Cash 100 ETH",
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96": "Lazarus Group (OFAC)",
    "0xa0e1c89ef1a489c9c7de96311ed5ce5d32c20e4b": "Lazarus Group (OFAC)",
    "0x308ed4b7b49797e1a98d3818bff6fe5385410370": "Huione Group (OFAC)",
    "0x7f367cc41522ce07553e823bf3be79a889debe1b": "Darknet Market",
    "0x3cbded43efdaf0fc77b9c55f6fc9988fcc9b37d9": "Bitfinex Hack",
}

# ============================================================
# 工具
# ============================================================

def safe_int(x):
    if x is None: return 0
    if isinstance(x, int): return x
    s = str(x).strip().lower()
    if s in ("", "0x"): return 0
    try:
        return int(s, 16) if s.startswith("0x") else int(s)
    except:
        return 0

def _get(params, retry=5):
    """V2 API — result 是 list 就返回，不管 message"""
    params["chainid"] = CHAIN  # V2 必须带 chainid
    params["apikey"]  = API_KEY
    for i in range(retry):
        try:
            r = SESS.get(BASE, params=params, timeout=30)
            if r.status_code == 200:
                j      = r.json()
                result = j.get("result", [])
                if isinstance(result, list):
                    return j
                if isinstance(result, str):
                    if "rate limit" in result.lower():
                        print("  [限速] 等3秒...")
                        time.sleep(3)
                        continue
                    print(f"  [API错误] {result[:80]}")
                    return {"result": []}
        except Exception as e:
            print(f"  [retry {i+1}] {e}")
        time.sleep(0.5 * (1.5 ** i))
    return {"result": []}

# ============================================================
# 数据采集
# ============================================================

def fetch_txlist(address):
    res = _get({"module":"account","action":"txlist",
                "address":address,"sort":"asc"}).get("result",[])
    return res if isinstance(res, list) else []

def fetch_internaltx(address):
    res = _get({"module":"account","action":"txlistinternal",
                "address":address,"sort":"asc"}).get("result",[])
    return res if isinstance(res, list) else []

def fetch_tokentx(address):
    res = _get({"module":"account","action":"tokentx",
                "address":address,"sort":"asc"}).get("result",[])
    return res if isinstance(res, list) else []

def fetch_logs(address):
    padded = "0x" + address.lower().replace("0x","").zfill(64)
    logs   = []
    for pos in ["topic1","topic2"]:
        batch = _get({
            "module":"logs","action":"getLogs",
            "fromBlock":"0","toBlock":"latest",
            "topic0": TOPIC_TRANSFER,
            pos: padded
        }).get("result",[])
        if isinstance(batch, list):
            logs.extend(batch)
        time.sleep(0.25)
    return logs

def fetch_all(address):
    addr = address.lower()
    print(f"  拉取 ETH 交易...")
    eth = fetch_txlist(addr)
    print(f"    → {len(eth)} 笔")
    time.sleep(0.25)

    print(f"  拉取内部交易...")
    int_ = fetch_internaltx(addr)
    print(f"    → {len(int_)} 笔")
    time.sleep(0.25)

    print(f"  拉取 ERC20 转账（全币种）...")
    tok = fetch_tokentx(addr)
    print(f"    → {len(tok)} 笔")
    time.sleep(0.25)

    print(f"  拉取原始事件...")
    logs = fetch_logs(addr)
    print(f"    → {len(logs)} 条")

    return eth, int_, tok, logs

# ============================================================
# 建图
# ============================================================

def build_graph(eth_txs, int_txs, token_txs):
    nodes = {}
    edges = []

    def upsert(a, ts):
        a = a.lower()
        if a not in nodes:
            nodes[a] = {"first_seen":ts,"last_seen":ts,
                        "in_count":0,"out_count":0,
                        "in_value":0,"out_value":0,"tokens":set()}
        else:
            nodes[a]["first_seen"] = min(nodes[a]["first_seen"], ts)
            nodes[a]["last_seen"]  = max(nodes[a]["last_seen"],  ts)
        return a

    def add(frm, to, val, ts, typ):
        if not frm or not to: return
        f = upsert(frm, ts); t = upsert(to, ts)
        nodes[f]["out_count"] += 1; nodes[f]["out_value"] += val
        nodes[t]["in_count"]  += 1; nodes[t]["in_value"]  += val
        if typ not in ("ETH","INT"):
            nodes[f]["tokens"].add(typ)
            nodes[t]["tokens"].add(typ)
        edges.append((f, t, val, ts, typ))

    for tx in eth_txs:
        if tx.get("isError","0") == "1": continue
        add(tx.get("from",""), tx.get("to",""),
            safe_int(tx.get("value",0)), safe_int(tx.get("timeStamp",0)), "ETH")

    for tx in int_txs:
        if tx.get("isError","0") == "1": continue
        add(tx.get("from",""), tx.get("to",""),
            safe_int(tx.get("value",0)), safe_int(tx.get("timeStamp",0)), "INT")

    for tx in token_txs:
        add(tx.get("from",""), tx.get("to",""),
            safe_int(tx.get("value",0)), safe_int(tx.get("timeStamp",0)),
            tx.get("tokenSymbol","?"))

    return nodes, edges

# ============================================================
# 检测器
# ============================================================

def detect_blacklist(nodes):
    return [{"address":a,"label":BLACKLIST[a]}
            for a in nodes if a in BLACKLIST]

def detect_peel_chain(nodes, edges):
    cands = {a for a,i in nodes.items()
             if i["in_count"]==1 and i["out_count"]==1}
    nxt   = {f:t for f,t,*_ in edges if f in cands}
    visited, chains = set(), []
    for start in cands:
        if start in visited: continue
        chain, cur = [start], start
        while cur in nxt and nxt[cur] in cands and nxt[cur] not in visited:
            cur = nxt[cur]; chain.append(cur); visited.add(cur)
        if len(chain) >= 5: chains.append(chain)
    if not chains: return {"detected":False}
    best = max(chains, key=len)
    return {"detected":True,"chain_length":len(best),"sample":best[:5],
            "severity":"HIGH" if len(best)>=10 else "MEDIUM"}

def detect_smurfing(nodes, edges):
    by_sender = defaultdict(list)
    for f,t,v,ts,typ in edges: by_sender[f].append((v,ts))
    results = []
    for sender, txs in by_sender.items():
        if len(txs) < 5: continue
        mc, freq = Counter(v for v,_ in txs).most_common(1)[0]
        if freq < 5 or mc == 0: continue
        same = sorted([(v,ts) for v,ts in txs if v==mc], key=lambda x:x[1])
        if len(same) >= 5:
            ivs = [same[i+1][1]-same[i][1] for i in range(len(same)-1)]
            avg = sum(ivs)/len(ivs) if ivs else 1
            reg = avg>0 and all(abs(iv-avg)<avg*0.3 for iv in ivs)
            results.append({"sender":sender,"amount":mc,"freq":freq,
                            "regular":reg,"severity":"HIGH" if reg else "MEDIUM"})
    return {"detected":bool(results),"patterns":results[:3]} if results else {"detected":False}

def detect_fanout(nodes, edges):
    results = []
    for addr, info in nodes.items():
        if info["in_count"]>=5 and info["out_count"]>=5:
            lt = info["last_seen"] - info["first_seen"]
            if lt < 3600:
                results.append({"address":addr,"in":info["in_count"],
                                "out":info["out_count"],"lifetime":lt,
                                "severity":"HIGH"})
    return {"detected":bool(results),"hubs":results[:3]} if results else {"detected":False}

def detect_rapid_lp(token_txs):
    by_pair = defaultdict(list)
    for tx in token_txs:
        ts = safe_int(tx.get("timeStamp",0))
        c  = tx.get("contractAddress","").lower()
        by_pair[(tx.get("from","").lower(), c)].append(("out",ts))
        by_pair[(tx.get("to","").lower(),   c)].append(("in", ts))
    results = []
    for (addr,contract), events in by_pair.items():
        ins  = sorted(ts for typ,ts in events if typ=="in")
        outs = sorted(ts for typ,ts in events if typ=="out")
        for ti in ins:
            for to in outs:
                if 0 < to-ti < 1800:
                    results.append({"address":addr,"contract":contract,
                                   "held_secs":to-ti,"severity":"MEDIUM"})
                    break
    return {"detected":bool(results),"incidents":results[:3]} if results else {"detected":False}

def detect_multi_token_swap(token_txs):
    by_addr = defaultdict(list)
    for tx in token_txs:
        by_addr[tx.get("from","").lower()].append(
            (tx.get("tokenSymbol","?"), safe_int(tx.get("timeStamp",0))))
    results = []
    for addr, txs in by_addr.items():
        txs = sorted(txs, key=lambda x:x[1])
        for i,(sym,ts) in enumerate(txs):
            window  = {s for s,t in txs if ts <= t <= ts+3600}
            if len(window) >= 4:
                results.append({"address":addr,"token_count":len(window),
                                "tokens":list(window),"severity":"MEDIUM"})
                break
    return {"detected":bool(results),"patterns":results[:3]} if results else {"detected":False}

def detect_gas_source(address, eth_txs):
    addr = address.lower()
    incoming = sorted([tx for tx in eth_txs
                       if tx.get("to","").lower()==addr],
                      key=lambda x: safe_int(x.get("blockNumber",0)))
    if not incoming: return {"detected":False}
    src = incoming[0].get("from","").lower()
    if src in BLACKLIST:
        return {"detected":True,"source":src,
                "label":BLACKLIST[src],"severity":"HIGH"}
    return {"detected":False}

def detect_reverse_taint(address, edges):
    addr = address.lower()
    hits = [{"from":f,"label":BLACKLIST[f],"value":v}
            for f,t,v,ts,typ in edges
            if t==addr and f in BLACKLIST]
    return {"detected":bool(hits),"incidents":hits,"severity":"MEDIUM"} if hits else {"detected":False}

def calculate_taint(address, nodes, edges):
    addr  = address.lower()
    taint = {a: (1.0 if a in BLACKLIST else 0.0) for a in nodes}
    for f,t,v,ts,typ in sorted(edges, key=lambda x:x[3]):
        if taint.get(f,0) > 0:
            total = nodes[f]["out_value"] or 1
            taint[t] = min(1.0, taint.get(t,0) + taint[f]*(v/total))
    return round(taint.get(addr,0.0)*100, 2)

# ============================================================
# 多跳追踪
# ============================================================

def trace_hops(address, hops=2):
    all_eth, all_int, all_tok, all_logs = [], [], [], []
    all_nodes, all_edges = {}, []
    visited = set()
    queue   = [(address.lower(), 0)]

    while queue:
        addr, depth = queue.pop(0)
        if addr in visited or depth > hops: continue
        visited.add(addr)
        print(f"\n  {'  '*depth}[深度{depth}] {addr[:22]}...")

        eth, int_, tok, logs = fetch_all(addr)
        nodes, edges = build_graph(eth, int_, tok)

        all_eth  += eth;  all_int  += int_
        all_tok  += tok;  all_logs += logs

        for a, info in nodes.items():
            if a not in all_nodes:
                all_nodes[a] = info
            else:
                for k in ("in_count","out_count","in_value","out_value"):
                    all_nodes[a][k] += info[k]
                all_nodes[a]["tokens"] |= info["tokens"]
        all_edges += edges

        # 往上追来源
        sources = list(set(
            tx.get("from","").lower()
            for tx in eth+tok
            if tx.get("to","").lower() == addr
        ))
        for src in sources[:5]:
            if src and src not in visited:
                queue.append((src, depth+1))
        time.sleep(0.2)

    return all_nodes, all_edges, all_eth, all_int, all_tok, all_logs

# ============================================================
# 主分析
# ============================================================

def analyze(address=TARGET_ADDRESS, hops=HOPS):
    addr = address.lower()
    print(f"\n{'='*55}")
    print(f" 合规引擎 v3 — 地址风险分析")
    print(f"{'='*55}")
    print(f" 地址: {address}")
    print(f" 深度: {hops} 跳")
    print(f"{'='*55}\n")

    print(">>> Step 1: 数据采集")
    nodes, edges, eth, int_, tok, logs = trace_hops(addr, hops)
    tokens_seen = set(e[4] for e in edges if e[4] not in ("ETH","INT"))
    print(f"\n    图谱:  {len(nodes)} 地址 / {len(edges)} 笔交易")
    if tokens_seen:
        print(f"    币种:  {', '.join(list(tokens_seen)[:10])}")

    print("\n>>> Step 2: 检测规则")
    R = {
        "blacklist":        detect_blacklist(nodes),
        "peel_chain":       detect_peel_chain(nodes, edges),
        "smurfing":         detect_smurfing(nodes, edges),
        "fanout":           detect_fanout(nodes, edges),
        "rapid_lp":         detect_rapid_lp(tok),
        "multi_token_swap": detect_multi_token_swap(tok),
        "gas_source":       detect_gas_source(addr, eth),
        "reverse_taint":    detect_reverse_taint(addr, edges),
    }

    taint = calculate_taint(addr, nodes, edges)
    bl    = len(R["blacklist"])
    highs = sum(1 for v in R.values()
                if isinstance(v,dict) and v.get("detected") and v.get("severity")=="HIGH")
    meds  = sum(1 for v in R.values()
                if isinstance(v,dict) and v.get("detected") and v.get("severity")=="MEDIUM")

    if   bl>0 or highs>=2 or taint>30: risk = "CRITICAL"
    elif highs>=1 or taint>10:          risk = "HIGH"
    elif meds>=1  or taint>5:           risk = "MEDIUM"
    else:                                risk = "LOW"

    print_report(addr, risk, taint, R, nodes, edges)
    return {"risk":risk,"taint":taint,"results":R,
            "nodes":nodes,"edges":edges,"token_txs":tok}

def print_report(addr, risk, taint, R, nodes, edges):
    B = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}
    tokens = set(e[4] for e in edges if e[4] not in ("ETH","INT"))

    print(f"\n{'='*55}")
    print(f" 风险报告  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")
    print(f" 地址:     {addr}")
    print(f" 风险等级: {B.get(risk,'')} {risk}")
    print(f" 污染率:   {taint}%")
    print(f" 图谱:     {len(nodes)} 地址 / {len(edges)} 笔交易")
    if tokens:
        print(f" 币种:     {', '.join(list(tokens)[:8])}")
    print(f"{'─'*55}")

    bl = R["blacklist"]
    if bl:
        print(f"\n 🔴 [CRITICAL] 直接黑名单命中")
        for h in bl:
            print(f"   ✗ {h['address'][:26]}  →  {h['label']}")

    METHODS = {
        "peel_chain":       ("C2","Peel Chain 剥皮链"),
        "smurfing":         ("C1","Smurfing 拆单"),
        "fanout":           ("C3","Fan-out 蜘蛛网"),
        "rapid_lp":         ("E2","流动性池快速存取"),
        "multi_token_swap": ("E1","DEX 多次闪兑换币"),
        "gas_source":       ("C8","Mixer Gas 资助"),
        "reverse_taint":    ("G2","反向污染攻击"),
    }
    any_hit = False
    for key,(code,name) in METHODS.items():
        r = R.get(key,{})
        if not r.get("detected"): continue
        any_hit = True
        sev = r.get("severity","MEDIUM")
        print(f"\n {B.get(sev,'🟡')} [{sev}] {code} — {name}")
        if key == "peel_chain":
            print(f"   链长: {r['chain_length']} 跳")
            print(f"   样本: {' → '.join(a[:12]+'...' for a in r['sample'])}")
        elif key == "smurfing":
            for p in r.get("patterns",[]):
                print(f"   发送方: {p['sender'][:22]}...")
                print(f"   重复金额: {p['amount']} | 频次: {p['freq']} | 时序规律: {'是' if p['regular'] else '否'}")
        elif key == "fanout":
            for h in r.get("hubs",[]):
                print(f"   地址: {h['address'][:22]}... 入{h['in']}/出{h['out']} 存活{h['lifetime']}秒")
        elif key == "rapid_lp":
            for i in r.get("incidents",[]):
                print(f"   {i['address'][:22]}... 持仓{i['held_secs']}秒")
        elif key == "multi_token_swap":
            for p in r.get("patterns",[]):
                print(f"   {p['address'][:22]}... 1小时换了{p['token_count']}种币: {','.join(p['tokens'][:5])}")
        elif key == "gas_source":
            print(f"   来源: {r['source'][:22]}... ({r['label']})")
        elif key == "reverse_taint":
            for i in r.get("incidents",[]):
                print(f"   来自: {i['from'][:22]}... ({i['label']})")

    if not bl and not any_hit:
        print(f"\n 🟢 未检测到已知风险模式")
    print(f"\n{'='*55}")

# ============================================================
# 运行
# ============================================================
report = analyze(TARGET_ADDRESS, HOPS)
