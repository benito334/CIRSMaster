# API Reference

- Combined OpenAPI: `docs/api/openapi_combined.json` (generated)
- To regenerate, run:

```bash
python backend/docs_generator/main.py --output docs/api/openapi_combined.json
```

Services queried by default:
- Auth: http://localhost:8019/openapi.json
- Feedback: http://localhost:8014/openapi.json
- Security Guardrails: http://localhost:8016/openapi.json
- License Audit: http://localhost:8017/openapi.json
- Backup: http://localhost:8018/openapi.json
- Hybrid Retriever: http://localhost:8002/openapi.json
- Chat Orchestrator: http://localhost:8003/openapi.json
