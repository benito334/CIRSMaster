import argparse
import json
import os
from pathlib import Path
import requests

DEFAULT_SERVICES = {
    "auth": "http://localhost:8019/openapi.json",
    "feedback": "http://localhost:8014/openapi.json",
    "security_guardrails": "http://localhost:8016/openapi.json",
    "license_audit": "http://localhost:8017/openapi.json",
    "backup": "http://localhost:8018/openapi.json",
    "hybrid_retriever": "http://localhost:8002/openapi.json",
    "chat_orchestrator": "http://localhost:8003/openapi.json"
}


def merge_openapi(specs: dict[str, dict]) -> dict:
    merged = {
        "openapi": "3.0.0",
        "info": {"title": "CIRS Combined API", "version": "0.1.0"},
        "paths": {},
        "components": {"schemas": {}, "securitySchemes": {}}
    }
    for name, spec in specs.items():
        for p, ops in spec.get("paths", {}).items():
            merged["paths"][f"/{name}{p}"] = ops
        comps = spec.get("components", {})
        for k, v in comps.get("schemas", {}).items():
            merged["components"]["schemas"][f"{name}_{k}"] = v
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    collected: dict[str, dict] = {}
    for name, url in DEFAULT_SERVICES.items():
        try:
            r = requests.get(url, timeout=5)
            if r.ok:
                collected[name] = r.json()
        except Exception:
            continue
    merged = merge_openapi(collected)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
