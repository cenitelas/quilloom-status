# Quilloom Status

Public status page for Quilloom services at <https://status.quilloom.com>.

## Stack

- **Checker**: [Gatus](https://github.com/TwiN/gatus) running in Docker on the Quilloom host (`/opt/gatus/config.yaml`, port `127.0.0.1:8082`).
- **Frontend**: a single static `public/index.html` styled to match `quilloom-web` (Geist, zinc-950). Talks to Gatus' JSON API for component status and history; reads manual incident banners from `public/incidents.json`.
- **Serving**: nginx on the Quilloom host serves `public/` at `status.quilloom.com`, proxies `/api/` to Gatus.

## Repository layout

```
public/
  index.html       # the status page
  incidents.json   # manual incident feed (edit this to post/resolve incidents)
  favicon.svg
nginx/
  status.quilloom.com.conf   # production nginx config
```

## Posting an incident

Edit `public/incidents.json` on the server (`/opt/quilloom-status/public/incidents.json`). No rebuild — the page polls every 60s.

Minimal entry:

```json
{
  "incidents": [
    {
      "id": "2026-04-14-api-latency",
      "status": "investigating",
      "severity": "partial",
      "title": "Elevated API latency",
      "started_at": "2026-04-14T18:02:00Z",
      "body": "We are investigating reports of slow responses from the API.",
      "updates": [
        { "at": "2026-04-14T18:15:00Z", "status": "identified", "body": "Upstream provider is rate-limiting us." },
        { "at": "2026-04-14T18:45:00Z", "status": "monitoring", "body": "Mitigation deployed; watching recovery." }
      ]
    }
  ]
}
```

`status` values: `investigating`, `identified`, `monitoring`, `resolved`, `maintenance`. Entries with `status: resolved` move to the **Past Incidents** section.

## Deploy

```
scp -r public/* root@212.19.134.104:/opt/quilloom-status/public/
```

nginx config lives in `nginx/status.quilloom.com.conf`. If it changes, copy to `/etc/nginx/sites-available/status.quilloom.com` and `nginx -t && systemctl reload nginx`.
