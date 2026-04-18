import sys, json
sys.path.insert(0, "/Users/lydia/Desktop/stbc/compliance_engine")

from collector import fetch_all, summarize_tokens, get_first_funder
from config import BLACKLIST

TARGET = "0x098B716B8Aaf21512996dC57EB0615e2383E2f96"
print(f"分析地址: {TARGET}\n")

eth, int_, tok, logs = fetch_all(TARGET)

result = {
    "address": TARGET.lower(),
    "summary": {
        "eth_tx_count":   len(eth),
        "internal_count": len(int_),
        "token_tx_count": len(tok),
        "log_count":      len(logs),
        "tokens_seen":    summarize_tokens(tok),
    },
    "blacklist_hit":   TARGET.lower() in BLACKLIST,
    "blacklist_label": BLACKLIST.get(TARGET.lower(), None),
    "first_funder":    get_first_funder(TARGET, eth),
    "sample_eth_txs":   eth[:3],
    "sample_token_txs": tok[:3],
}

print(json.dumps(result, indent=2, ensure_ascii=False))

out = "/Users/lydia/Desktop/stbc/test_output.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(f"\n已保存到 {out}")
