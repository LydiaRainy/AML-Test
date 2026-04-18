# ============================================================
# analyze.py - main entry point
# ============================================================

import sys, json, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config    import DEFAULT_HOPS
from collector import collect_hops, summarize_tokens
from graph     import build_graph, merge_graphs, graph_to_json, graph_summary
from scorer    import score

from detectors import (
    d_blacklist, d_peel_chain, d_smurfing, d_fanout,
    d_bipartite, d_mixer, d_defi, d_nft, d_dusting,
    d_pig_butchering, d_reverse_taint, d_pagerank, d_lof,
)


def analyze(address, hops=DEFAULT_HOPS, save_json=True, output_dir=None):
    addr = address.lower()

    print(f"\n{'='*55}")
    print(f" 合规引擎 — 地址风险分析")
    print(f"{'='*55}")
    print(f" 地址: {address}")
    print(f" 深度: {hops} 跳")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")

    print(">>> Step 1: 数据采集")
    eth, int_, tok, logs, visited = collect_hops(addr, hops)
    print(f"\n    采集完成: {len(visited)} 个地址")

    print("\n>>> Step 2: 建图")
    nodes = {}
    edges = []
    for a in visited:
        a_eth = [tx for tx in eth  if tx.get("from","").lower()==a or tx.get("to","").lower()==a]
        a_int = [tx for tx in int_ if tx.get("from","").lower()==a or tx.get("to","").lower()==a]
        a_tok = [tx for tx in tok  if tx.get("from","").lower()==a or tx.get("to","").lower()==a]
        n, e  = build_graph(a_eth, a_int, a_tok)
        nodes, edges = merge_graphs(nodes, edges, n, e)

    edges = list({(f,t,v,ts,typ) for f,t,v,ts,typ in edges})
    edges.sort(key=lambda x: x[3])

    gs = graph_summary(nodes, edges)
    print(f"    节点: {gs['total_nodes']}  边: {gs['total_edges']}")
    if gs["tokens_seen"]:
        print(f"    币种: {', '.join(gs['tokens_seen'][:8])}")

    print("\n>>> Step 3: 运行检测器")
    shared = dict(nodes=nodes, edges=edges, eth_txs=eth,
                  token_txs=tok, target_address=addr)

    detector_results = {
        "blacklist":      d_blacklist.detect(**shared),
        "peel_chain":     d_peel_chain.detect(**shared),
        "smurfing":       d_smurfing.detect(**shared),
        "fanout":         d_fanout.detect(**shared),
        "bipartite":      d_bipartite.detect(**shared),
        "mixer":          d_mixer.detect(**shared),
        "defi":           d_defi.detect(**shared),
        "nft":            d_nft.detect(**shared),
        "dusting":        d_dusting.detect(**shared),
        "pig_butchering": d_pig_butchering.detect(**shared),
        "reverse_taint":  d_reverse_taint.detect(**shared),
        "pagerank":       d_pagerank.detect(**shared),
        "lof":            d_lof.detect(**shared),
    }

    hit = sum(1 for v in detector_results.values()
              if isinstance(v, dict) and v.get("detected"))
    print(f"    完成，{hit} 个检测器命中")

    print("\n>>> Step 4: 综合评分")
    score_result = score(addr, nodes, edges, detector_results, eth)

    report = {
        "meta": {
            "address":        addr,
            "analyzed_at":    datetime.now().isoformat(),
            "hops":           hops,
            "engine_version": "1.0",
        },
        "risk":      score_result,
        "graph":     {"summary": gs, "json": graph_to_json(nodes, edges)},
        "detectors": detector_results,
        "tokens":    summarize_tokens(tok),
    }

    _print_report(report)

    if save_json:
        out_dir  = output_dir or os.path.expanduser("~/Desktop/stbc")
        out_path = os.path.join(
            out_dir,
            f"report_{addr[:10]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        os.makedirs(out_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n  报告已保存 → {out_path}")

    return report


def _print_report(report):
    BADGE = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}
    r   = report["risk"]
    lvl = r["risk_level"]
    print(f"\n{'='*55}")
    print(f" 风险报告")
    print(f"{'='*55}")
    print(f" 地址:     {r['address']}")
    print(f" 风险等级: {BADGE.get(lvl,'')} {lvl}")
    print(f" 风险分:   {r['risk_score']} / 100")
    print(f" 污染率:   {r['taint_rate']}%")
    gs = report["graph"]["summary"]
    print(f" 图谱:     {gs['total_nodes']} 节点 / {gs['total_edges']} 边")
    if report["tokens"]:
        print(f" 币种:     {', '.join(list(report['tokens'].keys())[:6])}")
    print(f"{'─'*55}")
    if not r["triggered"]:
        print(f"\n {BADGE['LOW']} 未检测到已知风险模式")
    else:
        for t in r["triggered"]:
            print(f"\n {BADGE.get(t['severity'],'🟡')} [{t['severity']}] {t['detector']}")
            if t["summary"]:
                print(f"   {t['summary']}")
    print(f"\n{'='*55}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze.py <address> [hops]")
        sys.exit(1)
    analyze(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_HOPS)
