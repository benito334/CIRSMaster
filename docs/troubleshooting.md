# Troubleshooting

- **GPU not visible in containers**: ensure NVIDIA Container Toolkit is installed; check `--gpus all` and compose device reservations.
- **Postgres connection errors**: verify `DB_URL`, ports, and that the `db` service is healthy.
- **Qdrant not reachable**: check port mapping and logs.
- **Auth failures**: confirm `AUTH_JWT_SECRET` set and tokens are not expired.
- **OpenAPI merge missing services**: ensure services are running and accessible at listed URLs.
