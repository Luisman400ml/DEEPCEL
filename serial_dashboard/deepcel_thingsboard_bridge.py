#!/usr/bin/env python3
"""Forward DEEPCEL local dashboard samples to ThingsBoard.

The bridge subscribes to the local offline dashboard Server-Sent Events stream
and publishes live samples to ThingsBoard using the HTTP telemetry API. It does
not open the MKR serial port, so it can run alongside the offline dashboard.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SOURCE = "http://127.0.0.1:8501"
DEFAULT_THINGSBOARD_HOST = "https://thingsboard.cloud"
TELEMETRY_KEYS = (
    "temperature_c",
    "humidity_pct",
    "prediction_temperature_c",
    "device_time_ms",
    "sequence",
)


def normalize_host(host: str) -> str:
    host = host.strip().rstrip("/")
    if not host:
        raise ValueError("ThingsBoard host is empty")
    if "://" not in host:
        host = f"http://{host}"
    return host


def env_first(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def numeric_or_none(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def telemetry_payload(sample: dict[str, Any]) -> dict[str, Any] | None:
    values: dict[str, int | float] = {}
    for key in TELEMETRY_KEYS:
        value = numeric_or_none(sample.get(key))
        if value is not None:
            values[key] = value

    if not values:
        return None

    host_time_s = numeric_or_none(sample.get("host_time_s"))
    if host_time_s is None:
        return {"values": values}
    return {"ts": int(float(host_time_s) * 1000), "values": values}


class ThingsBoardPublisher:
    def __init__(self, host: str, access_token: str, timeout_s: float, dry_run: bool) -> None:
        self.host = normalize_host(host)
        self.access_token = access_token.strip()
        self.timeout_s = timeout_s
        self.dry_run = dry_run

        token = urllib.parse.quote(self.access_token, safe="")
        self.endpoint = f"{self.host}/api/v1/{token}/telemetry"

    def publish(self, sample: dict[str, Any]) -> bool:
        payload = telemetry_payload(sample)
        if payload is None:
            return False

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if self.dry_run:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return True

        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            if response.status >= 400:
                raise urllib.error.HTTPError(
                    self.endpoint,
                    response.status,
                    response.reason,
                    response.headers,
                    response,
                )
        return True


def iter_sse_events(source: str, timeout_s: float) -> Iterable[tuple[str, str]]:
    events_url = urllib.parse.urljoin(source.rstrip("/") + "/", "events")
    request = urllib.request.Request(
        events_url,
        headers={"Accept": "text/event-stream"},
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        event_type = "message"
        data_lines: list[str] = []
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                if data_lines:
                    yield event_type, "\n".join(data_lines)
                event_type = "message"
                data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_type = line[6:].strip() or "message"
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())


def stream_samples(source: str, timeout_s: float) -> Iterable[dict[str, Any]]:
    for event_type, payload in iter_sse_events(source, timeout_s):
        if event_type != "sample":
            continue
        try:
            sample = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(sample, dict):
            yield sample


def replay_csv(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            yield dict(row)


def run_live(args: argparse.Namespace, publisher: ThingsBoardPublisher) -> int:
    source = args.source.rstrip("/")
    print(f"Source dashboard: {source}")
    print(f"ThingsBoard endpoint: {publisher.host}/api/v1/<token>/telemetry")
    print("Waiting for live samples. Stop with Ctrl+C.")

    sent = 0
    backoff_s = 1.0
    while True:
        try:
            for sample in stream_samples(source, args.timeout):
                if publisher.publish(sample):
                    sent += 1
                    seq = sample.get("sequence", sent)
                    print(f"sent sample {seq} ({sent} total)")
                if args.max_samples and sent >= args.max_samples:
                    return 0
            backoff_s = 1.0
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            print(f"source/publish error: {exc}; retrying in {backoff_s:.1f}s", file=sys.stderr)
            time.sleep(backoff_s)
            backoff_s = min(backoff_s * 1.7, 20.0)


def run_replay(args: argparse.Namespace, publisher: ThingsBoardPublisher) -> int:
    if not args.replay_csv:
        return 0
    path = Path(args.replay_csv)
    sent = 0
    for sample in replay_csv(path):
        if publisher.publish(sample):
            sent += 1
        if args.max_samples and sent >= args.max_samples:
            break
        if args.replay_delay > 0:
            time.sleep(args.replay_delay)
    print(f"replayed {sent} samples from {path}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forward DEEPCEL samples to ThingsBoard")
    parser.add_argument(
        "--source",
        default=env_first("DEEPCEL_DASHBOARD_URL") or DEFAULT_SOURCE,
        help="Local DEEPCEL dashboard URL, default http://127.0.0.1:8501",
    )
    parser.add_argument(
        "--thingsboard-host",
        default=env_first("DEEPCEL_TB_HOST", "THINGSBOARD_HOST") or DEFAULT_THINGSBOARD_HOST,
        help="ThingsBoard base URL, for example https://thingsboard.cloud or http://localhost:8080",
    )
    parser.add_argument(
        "--access-token",
        default=env_first("DEEPCEL_TB_TOKEN", "THINGSBOARD_ACCESS_TOKEN"),
        help="Device access token. Prefer env DEEPCEL_TB_TOKEN instead of writing it in shell history.",
    )
    parser.add_argument("--timeout", type=float, default=35.0, help="HTTP timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads instead of posting them")
    parser.add_argument("--max-samples", type=int, default=0, help="Stop after N samples; 0 means forever")
    parser.add_argument("--replay-csv", default=None, help="Replay a local dashboard CSV log instead of live SSE")
    parser.add_argument("--replay-delay", type=float, default=0.0, help="Delay between replayed CSV samples")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.access_token and not args.dry_run:
        print(
            "Missing ThingsBoard device token. Set DEEPCEL_TB_TOKEN or pass --access-token.",
            file=sys.stderr,
        )
        return 2

    publisher = ThingsBoardPublisher(
        host=args.thingsboard_host,
        access_token=args.access_token or "dry-run-token",
        timeout_s=args.timeout,
        dry_run=args.dry_run,
    )

    if args.replay_csv:
        return run_replay(args, publisher)
    return run_live(args, publisher)


if __name__ == "__main__":
    raise SystemExit(main())
