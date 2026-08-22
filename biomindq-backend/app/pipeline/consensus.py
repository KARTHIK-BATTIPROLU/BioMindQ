import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def compute_consensus_meter(item_stances: List[Dict[str, Any]]) -> Dict[str, Any]:
    supports_count = 0
    contradicts_count = 0
    mentions_count = 0

    for item in item_stances:
        st = str(item.get("stance", "")).lower()
        if st in ["supports", "support"]:
            supports_count += 1
        elif st in ["contradicts", "contradict", "contrasts", "contrast"]:
            contradicts_count += 1
        elif st in ["mentions", "mention", "mixed_unclear"]:
            mentions_count += 1
        else:
            # Default fallback for unclassified items
            supports_count += 1

    total = len(item_stances)

    if total == 0:
        label = "No Evidence"
    elif contradicts_count == 0:
        if mentions_count == 0 or supports_count >= mentions_count:
            label = "Strong Consensus"
        else:
            label = "Mostly Supported"
    elif supports_count > 0 and contradicts_count > 0:
        label = "Mixed Evidence"
    elif contradicts_count > 0 and supports_count == 0:
        label = "Conflicting"
    else:
        label = "Mostly Supported"

    return {
        "label": label,
        "supports": supports_count,
        "contradicts": contradicts_count,
        "mentions": mentions_count,
        "total_sources": total
    }
