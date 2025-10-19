import os
import json
from typing import Dict, Any, List

LICENSE_KEYWORDS = {
    'CC-BY-4.0': ['cc-by', 'creative commons attribution 4.0'],
    'CC0': ['cc0', 'public domain'],
    'CC-BY-NC': ['noncommercial', 'cc-by-nc'],
    'CC-BY-ND': ['no derivatives', 'cc-by-nd'],
    'AllRightsReserved': ['all rights reserved']
}

RULES = {
    'CC-BY-4.0': {'license_type': 'permissive', 'usage_restrictions': 'attribution'},
    'CC0': {'license_type': 'public_domain', 'usage_restrictions': 'none'},
    'CC-BY-NC': {'license_type': 'restricted', 'usage_restrictions': 'noncommercial'},
    'CC-BY-ND': {'license_type': 'restricted', 'usage_restrictions': 'no_derivatives'},
    'AllRightsReserved': {'license_type': 'prohibited', 'usage_restrictions': 'no_redistribution'}
}

def classify_text(text: str) -> str:
    t = text.lower()
    for spdx, keys in LICENSE_KEYWORDS.items():
        for k in keys:
            if k in t:
                return spdx
    return 'Unknown'


def scan_path(path: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for f in files:
                p = os.path.join(root, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                        data = fh.read()[:20000]
                    lic = classify_text(data)
                    results.append({'source_id': p, 'license': lic})
                except Exception:
                    continue
    else:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                data = fh.read()[:20000]
            lic = classify_text(data)
            results.append({'source_id': path, 'license': lic})
        except Exception:
            pass
    return results


def to_policy(license_id: str) -> Dict[str, Any]:
    r = RULES.get(license_id, {'license_type': 'unknown', 'usage_restrictions': 'unknown'})
    return {'license': license_id, **r}
