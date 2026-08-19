# Deploy AutoVD behind a server URL

This is the deployment path for adding AutoVD as an internal ChatGPT plugin/app by entering a remote MCP server URL instead of using a tunnel.

## Resulting endpoints

For a public hostname such as `autovd.example.com`:

```text
MCP:    https://autovd.example.com/mcp
Health: https://autovd.example.com/health
```

AutoVD speaks MCP Streamable HTTP. `/mcp` is the MCP endpoint; `/health` is a plain public liveness endpoint that returns only `{"status":"ok"}`.

## Requirements

The deployment host needs:

- inbound HTTPS through a valid public certificate;
- outbound HTTPS so temporary ChatGPT upload URLs can be fetched;
- FFmpeg;
- writable ephemeral storage for active jobs;
- a server-owned directory containing one or more permitted music tracks.

The current server is one process and keeps active job state in memory plus ephemeral workspace files. Do not configure multiple independent AutoVD workers for the MVP because jobs are not shared between processes.

## Container build

```bash
docker build -t autovd:latest .
```

The image:

- uses Python 3.13;
- installs locked Python dependencies with `uv`;
- installs FFmpeg;
- runs as an unprivileged user;
- binds AutoVD to `0.0.0.0:8000` by default;
- exposes `/health` for liveness checks.

## Music library

AutoVD intentionally does not ship copyrighted music in the repository. Mount a directory containing server-approved tracks at `/app/music/library`.

Supported renderer-library suffixes currently include AAC, FLAC, M4A, MP3, OGG, and WAV.

Example:

```bash
docker run --rm \
  -p 127.0.0.1:8000:8000 \
  -e AUTOVD_ALLOWED_HOSTS="autovd.example.com,autovd.example.com:*" \
  -v /srv/autovd/music:/app/music/library:ro \
  autovd:latest
```

Binding the published Docker port to `127.0.0.1` is appropriate when a reverse proxy on the same host terminates public HTTPS.

## Required hostname allowlist

The MCP Python SDK protects Streamable HTTP from DNS-rebinding attacks. A real public hostname must be explicitly allowlisted.

Set:

```text
AUTOVD_ALLOWED_HOSTS=autovd.example.com,autovd.example.com:*
```

AutoVD always also allows localhost Host headers for local health and development checks.

If a browser-origin client is ever required, optional origins can be supplied separately:

```text
AUTOVD_ALLOWED_ORIGINS=https://example.com
```

For the ChatGPT server-to-server MCP connection, an Origin header is normally not required.

If a reverse proxy is used, preserve the public `Host` header. Otherwise the hostname seen by AutoVD must also be included in `AUTOVD_ALLOWED_HOSTS`.

## Runtime configuration

Deployment-specific settings:

```text
AUTOVD_HOST=0.0.0.0
AUTOVD_PORT=8000
AUTOVD_ALLOWED_HOSTS=autovd.example.com,autovd.example.com:*
AUTOVD_JOB_ROOT=/tmp/autovd-jobs
AUTOVD_MUSIC_DIR=/app/music/library
```

Existing MVP resource limits remain configurable through the variables documented in `README.md`, including clip/file/duration limits, active jobs, job TTL, output bytes, motion settings, and render timeout.

## HTTPS reverse proxy

Terminate TLS in the hosting platform or a reverse proxy and forward requests to AutoVD over the private/local network.

The proxy must support normal HTTP request bodies and preserve the MCP endpoint at `/mcp`. Do not convert the endpoint to legacy SSE.

The recommended topology is:

```text
ChatGPT
  ↓ HTTPS
https://autovd.example.com/mcp
  ↓ reverse proxy / platform ingress
http://127.0.0.1:8000/mcp
  ↓
AutoVD + FFmpeg
```

## Verification before adding the plugin

Check liveness:

```bash
curl --fail https://autovd.example.com/health
```

Expected response:

```json
{"status":"ok"}
```

Then verify MCP discovery through the actual remote URL:

```bash
npx --yes @modelcontextprotocol/inspector@2.2.0 --cli \
  https://autovd.example.com/mcp \
  --transport http \
  --method tools/list
```

The tool list should include:

- `health`
- `prepare_video_analysis`
- `get_analysis_chunk`
- `render_video`
- `get_temporal_analysis_demo`

## Add the internal ChatGPT plugin

In the "New plugin" form:

```text
Name:        AutoVD
Connection:  Server URL
Server URL:  https://autovd.example.com/mcp
```

For an MVP-only internal test, use the no-auth option if the UI permits it and the deployment is intentionally temporary/restricted. The current AutoVD server does not implement OAuth yet.

A no-auth MCP URL is still reachable over the Internet even if the ChatGPT plugin itself is private. Do not treat that configuration as a production security boundary. Add proper authentication before broader or long-lived exposure.

## Stop condition

After the remote URL passes `/health` and MCP Inspector, the remaining project gate is the real ChatGPT test: connect the internal plugin, upload representative AI-generated footage, verify temporal-frame interpretation/tool selection/output handoff, then run the human-labeled cut-precision evaluation.
