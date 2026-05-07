#!/usr/bin/env python3
"""Aggregate Gatus check history into a compact JSON for the status page.

Reads /opt/gatus/data/gatus.db, emits hourly totals per endpoint plus
the most recent check result, and atomically writes the output to
/var/cache/quilloom-status/history.json. Designed to be invoked from a
systemd timer every 60s so the status page can render bars and uptime
numbers without pulling tens of thousands of raw rows on each load.
"""
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

DB = '/opt/gatus/data/gatus.db'
OUT = '/var/cache/quilloom-status/history.json'


def main():
    conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=10)
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT e.endpoint_key, e.endpoint_name, e.endpoint_group,
               substr(r.timestamp, 1, 13) AS h,
               COUNT(*) AS total,
               SUM(CASE WHEN r.success = 1 THEN 0 ELSE 1 END) AS failed
        FROM endpoint_results r
        JOIN endpoints e ON e.endpoint_id = r.endpoint_id
        GROUP BY e.endpoint_key, h
        ORDER BY e.endpoint_key, h
    """).fetchall()

    latest = {}
    for key, success, ts in cur.execute("""
        SELECT e.endpoint_key, r.success, r.timestamp
        FROM endpoint_results r
        JOIN endpoints e ON e.endpoint_id = r.endpoint_id
        JOIN (
            SELECT endpoint_id, MAX(endpoint_result_id) AS max_id
            FROM endpoint_results
            GROUP BY endpoint_id
        ) last ON last.endpoint_id = r.endpoint_id AND last.max_id = r.endpoint_result_id
    """).fetchall():
        latest[key] = {'success': bool(success), 'timestamp': ts}

    conn.close()

    eps = {}
    for key, name, group, h, total, failed in rows:
        if key not in eps:
            eps[key] = {
                'key': key,
                'name': name,
                'group': group,
                'hours': [],
                'latest': latest.get(key),
            }
        # h is "2026-04-23 21" → emit "2026-04-23T21:00:00Z"
        iso = f"{h[:10]}T{h[11:13]}:00:00Z"
        eps[key]['hours'].append([iso, total, failed])

    out = {
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'endpoints': list(eps.values()),
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUT), suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(out, f, separators=(',', ':'))
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.rename(tmp, OUT)
    except Exception:
        try:
            os.unlink(tmp)
        finally:
            raise


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'gatus-aggregate failed: {e}', file=sys.stderr)
        sys.exit(1)
