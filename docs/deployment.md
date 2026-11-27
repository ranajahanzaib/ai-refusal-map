# Deployment

Local development can run without Docker using `pnpm dev` and `uv run uvicorn arm_api.main:app`. Docker Compose provides separate web and API services and mounts local data directories. Use production builds and persistent protected volumes for any actual research deployment.

Before network exposure: set a strong `ARM_API_TOKEN`, configure allowed CORS origins, place both services behind TLS and an authenticated reverse proxy, restrict transcript routes, configure backups/retention, and review logs for accidental transcript capture. The current API does not implement complete user identity, roles, rare-group suppression or sensitive-operation audit trails, so it is not ready for a public corpus deployment.
