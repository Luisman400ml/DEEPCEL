#!/usr/bin/env python3
"""DEEPCEL serial telemetry dashboard.

Reads the MKR Vidor serial stream, asks the sketch for CSV mode, stores a CSV
log, and serves a small browser dashboard with live plots.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import queue
import socket
import sys
import threading
import time
import urllib.parse
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:  # pragma: no cover - handled at runtime.
    raise SystemExit(
        "pyserial is required. Install it with: python3 -m pip install pyserial"
    ) from exc


DEFAULT_BAUD = 9600
DEFAULT_WEB_PORT = 8501
CSV_HEADER_PREFIXES = (
    "record,time_ms,temperature_c",
    "record,time_ms,temperature_history_c",
)

SAMPLE_FIELDS = (
    "sequence",
    "host_time_iso",
    "host_time_s",
    "device_time_ms",
    "temperature_c",
    "humidity_pct",
    "dht_status",
    "dht_error_count",
    "dht_last_status",
    "prediction_temperature_c",
    "light_adc",
    "prediction_light_model",
    "temperature_q4_4",
    "light_q4_4",
    "prediction_temperature_q4_4",
    "prediction_light_q4_4",
    "light_status",
    "light_sensor",
    "temperature_history_c",
    "light_history_adc",
)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_array(value: str) -> list[float]:
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    numbers: list[float] = []
    for item in parsed:
        try:
            numbers.append(float(item))
        except (TypeError, ValueError):
            continue
    return numbers


def clean_line(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").strip()


class DeepcelParser:
    """Parse either the preferred CSV stream or the fallback text stream."""

    def __init__(self) -> None:
        self._text_record: dict[str, Any] = {}

    def parse(self, line: str) -> dict[str, Any] | None:
        if line.startswith("DATA,"):
            self._text_record.clear()
            return self._parse_csv(line)
        if line.startswith(CSV_HEADER_PREFIXES):
            self._text_record.clear()
            return None
        return self._parse_text(line)

    def _parse_csv(self, line: str) -> dict[str, Any] | None:
        try:
            row = next(csv.reader([line]))
        except csv.Error:
            return None
        if row[0] != "DATA":
            return None

        if len(row) >= 5 and row[2].strip() and not row[2].lstrip("-+.").startswith("["):
            record = {
                "device_time_ms": parse_int(row[1]),
                "temperature_c": parse_float(row[2]),
                "humidity_pct": parse_float(row[3]),
            }
            if len(row) >= 6:
                record["light_adc"] = parse_float(row[4])
                record["prediction_temperature_c"] = parse_float(row[5])
            else:
                record["prediction_temperature_c"] = parse_float(row[4])
            return record

        if len(row) < 11:
            return None

        temperature_history = parse_array(row[2])
        has_dht_status = len(row) >= 16 and not row[4].strip().startswith("[")
        if has_dht_status:
            light_history_index = 7
            prediction_index = 8
            q_index = 10
            light_status_index = 14
            dht_status = row[4].strip() or None
            dht_error_count = parse_int(row[5])
            dht_last_status = parse_int(row[6])
        else:
            light_history_index = 4
            prediction_index = 5
            q_index = 7
            light_status_index = 11
            dht_status = None
            dht_error_count = None
            dht_last_status = None

        if len(row) <= q_index + 3:
            return None

        light_history = parse_array(row[light_history_index])
        temperature_c = temperature_history[-1] if temperature_history else None
        light_adc = light_history[-1] if light_history else None

        return {
            "device_time_ms": parse_int(row[1]),
            "temperature_history_c": temperature_history,
            "humidity_pct": parse_float(row[3]),
            "dht_status": dht_status,
            "dht_error_count": dht_error_count,
            "dht_last_status": dht_last_status,
            "light_history_adc": light_history,
            "temperature_c": temperature_c,
            "light_adc": light_adc,
            "prediction_temperature_c": parse_float(row[prediction_index]),
            "prediction_light_model": parse_float(row[prediction_index + 1]),
            "temperature_q4_4": parse_int(row[q_index]),
            "light_q4_4": parse_int(row[q_index + 1]),
            "prediction_temperature_q4_4": parse_int(row[q_index + 2]),
            "prediction_light_q4_4": parse_int(row[q_index + 3]),
            "light_status": row[light_status_index].strip() if len(row) > light_status_index else None,
            "light_sensor": row[light_status_index + 1].strip() if len(row) > light_status_index + 1 else None,
        }

    def _parse_text(self, line: str) -> dict[str, Any] | None:
        if not line:
            if self._text_record:
                record = self._text_record
                self._text_record = {}
                return record
            return None

        if "\t" in line and line.count(":") >= 2:
            return self._parse_inline_text(line)

        if ":" not in line:
            return None
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if key == "TemperatureHistory_C":
            history = parse_array(value)
            self._text_record["temperature_history_c"] = history
            if history:
                self._text_record["temperature_c"] = history[-1]
        elif key in ("LightHistory_ADC", "LightHistory_value"):
            history = parse_array(value)
            self._text_record["light_history_adc"] = history
            if history:
                self._text_record["light_adc"] = history[-1]
        elif key == "Temperature_C":
            self._text_record["temperature_c"] = parse_float(value)
        elif key in ("Light_ADC", "Light_value"):
            self._text_record["light_adc"] = parse_float(value)
        elif key == "PredictionTemperature_C":
            self._text_record["prediction_temperature_c"] = parse_float(value)
        elif key == "PredictionLight_model":
            self._text_record["prediction_light_model"] = parse_float(value)
        elif key == "LightStatus":
            status, _, rest = value.partition(" sensor=")
            self._text_record["light_status"] = status.strip() or None
            self._text_record["light_sensor"] = rest.strip() or None
        elif key == "DHTStatus":
            self._parse_dht_status(value, self._text_record)
        elif key == "Humidity_pct":
            self._text_record["humidity_pct"] = parse_float(value)
            record = self._text_record
            self._text_record = {}
            return record

        return None

    def _parse_dht_status(self, value: str, record: dict[str, Any]) -> None:
        parts = value.split()
        record["dht_status"] = parts[0].strip() if parts else None
        for item in parts[1:]:
            key, _, raw = item.partition("=")
            if key == "code":
                record["dht_last_status"] = parse_int(raw)
            elif key == "errors":
                record["dht_error_count"] = parse_int(raw)

    def _parse_inline_text(self, line: str) -> dict[str, Any] | None:
        record: dict[str, Any] = {}
        for chunk in line.split("\t"):
            if ":" not in chunk:
                continue
            key, value = chunk.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in ("Temperatura_C", "Temperature_C"):
                record["temperature_c"] = parse_float(value)
            elif key in ("Prediccion_C", "PredictionTemperature_C"):
                record["prediction_temperature_c"] = parse_float(value)
            elif key in ("Humedad_pct", "Humidity_pct"):
                record["humidity_pct"] = parse_float(value)
            elif key in ("Light_ADC", "Light_value"):
                record["light_adc"] = parse_float(value)
            elif key == "PredictionLight_model":
                record["prediction_light_model"] = parse_float(value)
            elif key == "LightStatus":
                status, _, rest = value.partition(" sensor=")
                record["light_status"] = status.strip() or None
                record["light_sensor"] = rest.strip() or None
            elif key == "DHTStatus":
                self._parse_dht_status(value, record)

        return record if record else None


@dataclass
class SerialStatus:
    state: str = "stopped"
    port: str | None = None
    baud: int = DEFAULT_BAUD
    message: str = ""
    connected_at: str | None = None
    last_line_at: str | None = None
    last_sample_at: str | None = None
    samples: int = 0
    log_path: str | None = None


class TelemetryStore:
    def __init__(self, max_samples: int) -> None:
        self._lock = threading.RLock()
        self._samples: deque[dict[str, Any]] = deque(maxlen=max_samples)
        self._raw_lines: deque[str] = deque(maxlen=240)
        self._events: list[queue.Queue[dict[str, Any]]] = []
        self._status = SerialStatus()
        self._sequence = 0

    def set_status(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._status, key):
                    setattr(self._status, key, value)
            data = self.status()
        self.publish("status", data)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status.__dict__)

    def add_raw(self, line: str) -> None:
        status_payload = None
        with self._lock:
            self._raw_lines.append(line)
            self._status.last_line_at = now_iso()
            if line.startswith(("DHT20 read error", "ERROR:", "WARN:")):
                self._status.message = line
                status_payload = self.status()
        self.publish("raw", {"line": line})
        if status_payload:
            self.publish("status", status_payload)

    def add_sample(self, fields: dict[str, Any], raw: str) -> dict[str, Any]:
        timestamp = time.time()
        with self._lock:
            self._sequence += 1
            sample = {
                "sequence": self._sequence,
                "host_time_iso": now_iso(),
                "host_time_s": timestamp,
                "device_time_ms": fields.get("device_time_ms"),
                "temperature_c": fields.get("temperature_c"),
                "humidity_pct": fields.get("humidity_pct"),
                "dht_status": fields.get("dht_status"),
                "dht_error_count": fields.get("dht_error_count"),
                "dht_last_status": fields.get("dht_last_status"),
                "light_adc": fields.get("light_adc"),
                "prediction_temperature_c": fields.get("prediction_temperature_c"),
                "prediction_light_model": fields.get("prediction_light_model"),
                "temperature_q4_4": fields.get("temperature_q4_4"),
                "light_q4_4": fields.get("light_q4_4"),
                "prediction_temperature_q4_4": fields.get("prediction_temperature_q4_4"),
                "prediction_light_q4_4": fields.get("prediction_light_q4_4"),
                "light_status": fields.get("light_status"),
                "light_sensor": fields.get("light_sensor"),
                "temperature_history_c": fields.get("temperature_history_c", []),
                "light_history_adc": fields.get("light_history_adc", []),
                "raw": raw,
            }
            self._samples.append(sample)
            self._status.samples = self._sequence
            self._status.last_sample_at = sample["host_time_iso"]
        self.publish("sample", sample)
        return sample

    def samples(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._samples)
        if limit is None or limit >= len(items):
            return items
        return items[-limit:]

    def raw_lines(self) -> list[str]:
        with self._lock:
            return list(self._raw_lines)

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=200)
        with self._lock:
            self._events.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if subscriber in self._events:
                self._events.remove(subscriber)

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        event = {"type": event_type, "data": data}
        with self._lock:
            subscribers = list(self._events)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                continue

    def csv_bytes(self) -> bytes:
        rows = self.samples()
        output_lines: list[str] = []
        sink = CsvStringSink(output_lines)
        writer = csv.DictWriter(sink, fieldnames=SAMPLE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row_for_csv(row))
        return "".join(output_lines).encode("utf-8")


class CsvStringSink:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def write(self, value: str) -> int:
        self.lines.append(value)
        return len(value)


def row_for_csv(sample: dict[str, Any]) -> dict[str, Any]:
    row = {field: sample.get(field) for field in SAMPLE_FIELDS}
    row["temperature_history_c"] = json.dumps(sample.get("temperature_history_c", []))
    row["light_history_adc"] = json.dumps(sample.get("light_history_adc", []))
    return row


class CsvLogger:
    def __init__(self, log_dir: Path, enabled: bool) -> None:
        self._log_dir = log_dir
        self._enabled = enabled
        self._file: Any = None
        self._writer: csv.DictWriter[Any] | None = None
        self.path: Path | None = None

    def open(self) -> Path | None:
        if not self._enabled:
            return None
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self._log_dir / f"deepcel_{datetime.now():%Y%m%d_%H%M%S}.csv"
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=SAMPLE_FIELDS)
        self._writer.writeheader()
        self._file.flush()
        return self.path

    def write(self, sample: dict[str, Any]) -> None:
        if not self._writer:
            return
        self._writer.writerow(row_for_csv(sample))
        self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()
        self._file = None
        self._writer = None


class SerialReader:
    def __init__(
        self,
        store: TelemetryStore,
        port: str | None,
        baud: int,
        log_dir: Path,
        log_enabled: bool,
        send_csv_command: bool,
    ) -> None:
        self.store = store
        self.requested_port = port
        self.active_port: str | None = None
        self.baud = baud
        self.log_dir = log_dir
        self.log_enabled = log_enabled
        self.send_csv_command = send_csv_command
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._serial_lock = threading.Lock()
        self._restart_lock = threading.Lock()
        self._serial: serial.Serial | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="deepcel-serial", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._serial_lock:
            if self._serial:
                self._serial.close()
                self._serial = None
        if self._thread:
            self._thread.join(timeout=3)

    def restart(self) -> dict[str, Any]:
        with self._restart_lock:
            self.store.set_status(
                state="restarting",
                message="resetting serial connection",
                connected_at=None,
            )
            self.stop()
            self.start()
            self.store.set_status(
                state="connecting",
                port=self.requested_port,
                baud=self.baud,
                message="reopening serial port",
                connected_at=None,
            )
            return self.store.status()

    def board_reset(self) -> dict[str, Any]:
        with self._restart_lock:
            port = self.active_port or self.requested_port or detect_port()
            self.store.set_status(
                state="resetting",
                port=port,
                baud=self.baud,
                message="resetting MKR board through 1200 baud touch",
                connected_at=None,
            )
            self.stop()
            if not port:
                self.start()
                self.store.set_status(
                    state="waiting",
                    port=self.requested_port,
                    baud=self.baud,
                    message="no serial port available for board reset",
                    connected_at=None,
                )
                return self.store.status()

            try:
                with serial.Serial(port, 1200, timeout=0.25, write_timeout=0.25) as ser:
                    ser.dtr = False
                    time.sleep(0.25)
            except (OSError, serial.SerialException) as exc:
                self.start()
                self.store.set_status(
                    state="error",
                    port=port,
                    baud=self.baud,
                    message=f"board reset failed: {exc}",
                    connected_at=None,
                )
                return self.store.status()

            time.sleep(3.0)
            self.start()
            self.store.set_status(
                state="connecting",
                port=self.requested_port or port,
                baud=self.baud,
                message="board reset requested; reopening serial port",
                connected_at=None,
            )
            return self.store.status()

    def send_command(self, command: str) -> bool:
        payload = command.encode("ascii", errors="ignore")[:1]
        if not payload:
            return False
        with self._serial_lock:
            if not self._serial or not self._serial.is_open:
                return False
            self._serial.write(payload)
            self._serial.flush()
        return True

    def _run(self) -> None:
        parser = DeepcelParser()
        logger = CsvLogger(self.log_dir, self.log_enabled)
        log_path = logger.open()
        self.store.set_status(
            state="connecting",
            port=self.requested_port,
            baud=self.baud,
            message="opening serial port",
            log_path=str(log_path) if log_path else None,
        )

        try:
            while not self._stop.is_set():
                selected_port = self._selected_port()
                if not selected_port:
                    self.store.set_status(
                        state="waiting",
                        port=self.requested_port,
                        message="waiting for MKR serial port",
                        connected_at=None,
                    )
                    time.sleep(2)
                    continue
                try:
                    self.active_port = selected_port
                    self._read_forever(selected_port, parser, logger)
                except serial.SerialException as exc:
                    self.store.set_status(
                        state="error",
                        message=f"serial error: {exc}",
                        connected_at=None,
                    )
                    time.sleep(2)
                except OSError as exc:
                    self.store.set_status(
                        state="error",
                        message=f"port error: {exc}",
                        connected_at=None,
                    )
                    time.sleep(2)
        finally:
            logger.close()
            self.store.set_status(state="stopped", message="serial reader stopped")

    def _selected_port(self) -> str | None:
        if self.requested_port and Path(self.requested_port).exists():
            return self.requested_port
        return detect_port()

    def _read_forever(self, port: str, parser: DeepcelParser, logger: CsvLogger) -> None:
        with serial.Serial(port, self.baud, timeout=1.0, write_timeout=1.0) as ser:
            with self._serial_lock:
                self._serial = ser
            try:
                time.sleep(1.5)
                if self.send_csv_command:
                    ser.write(b"C")
                    ser.flush()
                self.store.set_status(
                    state="connected",
                    port=port,
                    message="reading telemetry",
                    connected_at=now_iso(),
                )

                while not self._stop.is_set():
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = clean_line(raw)
                    self.store.add_raw(line)
                    sample_fields = parser.parse(line)
                    if sample_fields is None:
                        continue
                    sample = self.store.add_sample(sample_fields, line)
                    logger.write(sample)
            finally:
                with self._serial_lock:
                    if self._serial is ser:
                        self._serial = None
                self.active_port = None


def detect_port() -> str | None:
    ports = list(list_ports.comports())
    for item in ports:
        vid = f"{item.vid:04x}" if item.vid is not None else ""
        text = " ".join(
            str(part)
            for part in (item.device, item.description, item.manufacturer, item.product, vid)
            if part
        ).lower()
        if "mkr" in text or "vidor" in text or "2341" in text:
            return item.device
    for item in ports:
        if item.device.startswith(("/dev/ttyACM", "/dev/ttyUSB")):
            return item.device
    return None


class DeepcelHttpServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        store: TelemetryStore,
        reader: SerialReader,
    ) -> None:
        super().__init__(address, handler_class)
        self.store = store
        self.reader = reader


class RequestHandler(BaseHTTPRequestHandler):
    server: DeepcelHttpServer

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/status":
            self.send_json(self.server.store.status())
        elif path == "/api/samples":
            limit = parse_int(query.get("limit", [""])[0])
            self.send_json({"samples": self.server.store.samples(limit)})
        elif path == "/api/raw":
            self.send_json({"raw": self.server.store.raw_lines()})
        elif path == "/api/ports":
            ports = [
                {
                    "device": item.device,
                    "description": item.description,
                    "manufacturer": item.manufacturer,
                    "product": item.product,
                    "vid": item.vid,
                    "pid": item.pid,
                }
                for item in list_ports.comports()
            ]
            self.send_json({"ports": ports})
        elif path == "/events":
            self.handle_events()
        elif path == "/download.csv":
            body = self.server.store.csv_bytes()
            filename = f"deepcel_capture_{datetime.now():%Y%m%d_%H%M%S}.csv"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/command":
            length = int(self.headers.get("Content-Length", "0") or "0")
            payload = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                data = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                data = {}
            command = str(data.get("command", ""))[:1]
            ok = self.server.reader.send_command(command)
            self.send_json({"ok": ok, "command": command})
        elif parsed.path == "/api/reset":
            status = self.server.reader.restart()
            self.send_json({"ok": True, "status": status})
        elif parsed.path == "/api/board-reset":
            status = self.server.reader.board_reset()
            self.send_json({"ok": True, "status": status})
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def handle_events(self) -> None:
        subscriber = self.server.store.subscribe()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            self.write_sse("status", self.server.store.status())
            for sample in self.server.store.samples(200):
                self.write_sse("sample", sample)
            while True:
                try:
                    event = subscriber.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self.write_sse(event["type"], event["data"])
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.server.store.unsubscribe(subscriber)

    def write_sse(self, event_type: str, data: dict[str, Any]) -> None:
        payload = json.dumps(data, separators=(",", ":"))
        self.wfile.write(f"event: {event_type}\n".encode("utf-8"))
        self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
        self.wfile.flush()

    def send_json(self, payload: dict[str, Any]) -> None:
        self.send_bytes(
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DEEPCEL Telemetry</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --panel: #ffffff;
      --text: #16202a;
      --muted: #607080;
      --line: #d9e0e7;
      --teal: #0f7d78;
      --blue: #315f9e;
      --amber: #ad7418;
      --rose: #b8475a;
      --green: #27865a;
      --shadow: 0 10px 28px rgba(20, 32, 44, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
      position: sticky;
      top: 0;
      z-index: 5;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      line-height: 1.1;
      font-weight: 760;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    button, a.button {
      border: 1px solid var(--line);
      color: var(--text);
      background: #ffffff;
      border-radius: 7px;
      padding: 9px 12px;
      font-size: 14px;
      line-height: 1;
      cursor: pointer;
      text-decoration: none;
      min-height: 34px;
    }
    button:hover, a.button:hover { border-color: #9eb0bf; }
    button:disabled {
      cursor: wait;
      color: #80909f;
      background: #f0f3f6;
    }
    button.primary {
      background: var(--teal);
      border-color: var(--teal);
      color: #ffffff;
    }
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 20px 24px 36px;
    }
    .status-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
    }
    .status {
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
      min-width: 0;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--amber);
      flex: 0 0 auto;
    }
    .dot.connected { background: var(--green); }
    .dot.error { background: var(--rose); }
    .pill {
      border: 1px solid var(--line);
      background: #ffffff;
      border-radius: 999px;
      padding: 6px 10px;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    nav.tabs {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 18px;
    }
    .tab {
      border: 0;
      border-bottom: 3px solid transparent;
      background: transparent;
      border-radius: 0;
      padding: 12px 14px 10px;
      color: var(--muted);
      min-height: 40px;
    }
    .tab.active {
      color: var(--text);
      border-bottom-color: var(--teal);
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }
    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 13px 14px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .metric strong {
      display: block;
      font-size: clamp(20px, 2vw, 28px);
      line-height: 1;
      font-weight: 760;
      min-height: 30px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
      min-width: 0;
    }
    .panel.full { grid-column: 1 / -1; }
    .latest-panel { margin-bottom: 14px; }
    .panel-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
    }
    .panel h2 {
      margin: 0;
      font-size: 15px;
      font-weight: 720;
    }
    .legend {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
    }
    .legend i {
      display: inline-block;
      width: 10px;
      height: 3px;
      border-radius: 2px;
      margin-right: 5px;
      vertical-align: middle;
    }
    canvas {
      display: block;
      width: 100%;
      height: 280px;
    }
    .details-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr));
    }
    .detail {
      min-width: 0;
      padding: 10px 12px;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }
    .detail span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 5px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .detail strong {
      display: block;
      font-size: 13px;
      font-weight: 650;
      overflow-wrap: anywhere;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: right;
      white-space: nowrap;
    }
    th:first-child, td:first-child { text-align: left; }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      background: #fbfcfd;
    }
    .table-wrap {
      overflow-x: auto;
      max-height: 520px;
    }
    pre {
      margin: 0;
      padding: 14px;
      min-height: 420px;
      max-height: 620px;
      overflow: auto;
      background: #101820;
      color: #e4edf4;
      font-size: 12px;
      line-height: 1.45;
    }
    .hidden { display: none; }
    @media (max-width: 980px) {
      header, .status-row { grid-template-columns: 1fr; }
      header { align-items: flex-start; }
      .toolbar { justify-content: flex-start; }
      .metrics { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      .details-grid { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 620px) {
      header, main { padding-left: 14px; padding-right: 14px; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .details-grid { grid-template-columns: 1fr; }
      .metric { padding: 11px; }
      canvas { height: 230px; }
      h1 { font-size: 20px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>DEEPCEL Telemetry</h1>
    <div class="toolbar">
      <button class="primary" id="csvBtn" type="button">CSV</button>
      <button id="testBtn" type="button">Test</button>
      <button id="resetBtn" type="button">Reset Serial</button>
      <button id="boardResetBtn" type="button">Reset Board</button>
      <a class="button" href="/download.csv">Export</a>
    </div>
  </header>
  <main>
    <div class="status-row">
      <div class="status">
        <span id="statusDot" class="dot"></span>
        <span id="statusText">starting</span>
      </div>
      <div class="toolbar">
        <span class="pill" id="portPill">port -</span>
        <span class="pill" id="samplePill">0 samples</span>
        <span class="pill" id="logPill">no log</span>
      </div>
    </div>

    <nav class="tabs">
      <button class="tab active" data-tab="live" type="button">Live</button>
      <button class="tab" data-tab="data" type="button">Data</button>
      <button class="tab" data-tab="raw" type="button">Serial</button>
    </nav>

    <section id="tab-live">
      <div class="metrics">
        <div class="metric"><span>Temperature</span><strong id="mTemp">-</strong></div>
        <div class="metric"><span>Pred. temp.</span><strong id="mPredTemp">-</strong></div>
        <div class="metric"><span>Humidity</span><strong id="mHum">-</strong></div>
        <div class="metric"><span>DHT20 status</span><strong id="mDhtStatus">-</strong></div>
        <div class="metric"><span>Light</span><strong id="mLight">-</strong></div>
        <div class="metric"><span>Pred. light</span><strong id="mPredLight">-</strong></div>
        <div class="metric"><span>Light status</span><strong id="mLightStatus">-</strong></div>
        <div class="metric"><span>Last sample</span><strong id="mLast">-</strong></div>
      </div>

      <section class="panel latest-panel">
        <div class="panel-head">
          <h2>Latest received data</h2>
          <span class="pill">all serial fields</span>
        </div>
        <div class="details-grid" id="latestDetails"></div>
      </section>

      <div class="grid">
        <section class="panel">
          <div class="panel-head">
            <h2>Temperature</h2>
            <div class="legend">
              <span><i style="background: var(--teal)"></i>sensor</span>
              <span><i style="background: var(--blue)"></i>FPGA</span>
            </div>
          </div>
          <canvas id="tempChart"></canvas>
        </section>
        <section class="panel">
          <div class="panel-head">
            <h2>Humidity</h2>
            <div class="legend">
              <span><i style="background: var(--rose)"></i>DHT20</span>
            </div>
          </div>
          <canvas id="humChart"></canvas>
        </section>
        <section class="panel full">
          <div class="panel-head">
            <h2>Light</h2>
            <div class="legend">
              <span><i style="background: var(--amber)"></i>I2C sensor</span>
              <span><i style="background: var(--blue)"></i>FPGA</span>
            </div>
          </div>
          <canvas id="lightChart"></canvas>
        </section>
      </div>
    </section>

    <section id="tab-data" class="hidden">
      <section class="panel">
        <div class="panel-head">
          <h2>Latest samples</h2>
          <span class="pill" id="rowsPill">0 rows</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>t MCU</th>
                <th>Temp C</th>
                <th>Temp history</th>
                <th>Pred C</th>
                <th>Humidity</th>
                <th>DHT20 status</th>
                <th>DHT20 errors</th>
                <th>Light</th>
                <th>Light history</th>
                <th>Pred light</th>
                <th>Light status</th>
                <th>Light sensor</th>
                <th>Temp Q4.4</th>
                <th>Light Q4.4</th>
                <th>Pred temp Q4.4</th>
                <th>Pred light Q4.4</th>
              </tr>
            </thead>
            <tbody id="dataRows"></tbody>
          </table>
        </div>
      </section>
    </section>

    <section id="tab-raw" class="hidden">
      <section class="panel">
        <div class="panel-head">
          <h2>Serial port</h2>
          <span class="pill" id="rawPill">0 lines</span>
        </div>
        <pre id="rawLog"></pre>
      </section>
    </section>
  </main>

  <script>
    const samples = [];
    const rawLines = [];
    const maxSamples = 720;
    const maxRawLines = 240;

    const $ = (id) => document.getElementById(id);
    const fmt = (value, digits = 2, suffix = "") => {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return `${Number(value).toFixed(digits)}${suffix}`;
    };
    const arrFmt = (value, digits = 2) => {
      if (!Array.isArray(value) || !value.length) return "-";
      return `[${value.map((item) => fmt(item, digits)).join(", ")}]`;
    };
    const escapeHtml = (value) => String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
    const fmtAny = (value, digits = 2, suffix = "") => {
      if (value === null || value === undefined || value === "") return "-";
      if (Array.isArray(value)) return arrFmt(value, digits);
      const number = Number(value);
      if (!Number.isNaN(number) && String(value).trim() !== "") {
        return `${number.toFixed(digits)}${suffix}`;
      }
      return String(value);
    };
    const statusWithSensor = (status, sensor) => {
      const cleanStatus = status || "-";
      return sensor ? `${cleanStatus} / ${sensor}` : cleanStatus;
    };
    const localClock = (iso) => {
      if (!iso) return "-";
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "-";
      return d.toLocaleTimeString();
    };

    class LineChart {
      constructor(canvasId, series) {
        this.canvas = $(canvasId);
        this.ctx = this.canvas.getContext("2d");
        this.series = series;
        this.resizeObserver = new ResizeObserver(() => this.draw(samples));
        this.resizeObserver.observe(this.canvas);
      }

      draw(data) {
        const rect = this.canvas.getBoundingClientRect();
        const ratio = window.devicePixelRatio || 1;
        const width = Math.max(320, Math.floor(rect.width * ratio));
        const height = Math.max(220, Math.floor(rect.height * ratio));
        if (this.canvas.width !== width || this.canvas.height !== height) {
          this.canvas.width = width;
          this.canvas.height = height;
        }

        const ctx = this.ctx;
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);

        const pad = { left: 52 * ratio, right: 18 * ratio, top: 20 * ratio, bottom: 34 * ratio };
        const plotW = width - pad.left - pad.right;
        const plotH = height - pad.top - pad.bottom;
        const rows = data.slice(-120);

        ctx.strokeStyle = "#d9e0e7";
        ctx.lineWidth = 1 * ratio;
        ctx.beginPath();
        for (let i = 0; i <= 4; i++) {
          const y = pad.top + (plotH * i) / 4;
          ctx.moveTo(pad.left, y);
          ctx.lineTo(width - pad.right, y);
        }
        ctx.stroke();

        const values = [];
        for (const sample of rows) {
          for (const item of this.series) {
            const value = Number(sample[item.field]);
            if (!Number.isNaN(value)) values.push(value);
          }
        }

        ctx.fillStyle = "#607080";
        ctx.font = `${11 * ratio}px ui-sans-serif, system-ui`;
        if (!rows.length || !values.length) {
          ctx.fillText("No data", pad.left, pad.top + 24 * ratio);
          return;
        }

        let min = Math.min(...values);
        let max = Math.max(...values);
        if (min === max) {
          min -= 1;
          max += 1;
        } else {
          const margin = (max - min) * 0.08;
          min -= margin;
          max += margin;
        }

        for (let i = 0; i <= 4; i++) {
          const y = pad.top + (plotH * i) / 4;
          const value = max - ((max - min) * i) / 4;
          ctx.fillText(value.toFixed(1), 8 * ratio, y + 4 * ratio);
        }

        const xFor = (index) => pad.left + (rows.length === 1 ? plotW : (plotW * index) / (rows.length - 1));
        const yFor = (value) => pad.top + plotH - ((value - min) / (max - min)) * plotH;

        for (const item of this.series) {
          ctx.strokeStyle = item.color;
          ctx.lineWidth = 2.2 * ratio;
          ctx.beginPath();
          let started = false;
          rows.forEach((sample, index) => {
            const value = Number(sample[item.field]);
            if (Number.isNaN(value)) return;
            const x = xFor(index);
            const y = yFor(value);
            if (!started) {
              ctx.moveTo(x, y);
              started = true;
            } else {
              ctx.lineTo(x, y);
            }
          });
          ctx.stroke();
        }

        const first = rows[0];
        const last = rows[rows.length - 1];
        ctx.fillStyle = "#607080";
        ctx.fillText(localClock(first.host_time_iso), pad.left, height - 10 * ratio);
        const rightLabel = localClock(last.host_time_iso);
        const textW = ctx.measureText(rightLabel).width;
        ctx.fillText(rightLabel, width - pad.right - textW, height - 10 * ratio);
      }
    }

    const tempChart = new LineChart("tempChart", [
      { field: "temperature_c", color: "#0f7d78" },
      { field: "prediction_temperature_c", color: "#315f9e" },
    ]);
    const humChart = new LineChart("humChart", [
      { field: "humidity_pct", color: "#b8475a" },
    ]);
    const lightChart = new LineChart("lightChart", [
      { field: "light_adc", color: "#ad7418" },
      { field: "prediction_light_model", color: "#315f9e" },
    ]);
    const latestFields = [
      ["sequence", "Sequence", 0],
      ["host_time_iso", "Host time", 0],
      ["device_time_ms", "Board time ms", 0],
      ["temperature_c", "Temperature C", 2],
      ["temperature_history_c", "Temperature history C", 2],
      ["humidity_pct", "Humidity %", 2],
      ["dht_status", "DHT20 status", 0],
      ["dht_error_count", "DHT20 errors", 0],
      ["dht_last_status", "DHT20 last code", 0],
      ["light_adc", "Light value", 2],
      ["light_history_adc", "Light history", 2],
      ["light_status", "Light status", 0],
      ["light_sensor", "Light sensor", 0],
      ["prediction_temperature_c", "Predicted temperature C", 2],
      ["prediction_light_model", "Predicted light", 2],
      ["temperature_q4_4", "Temperature Q4.4", 0],
      ["light_q4_4", "Light Q4.4", 0],
      ["prediction_temperature_q4_4", "Predicted temp Q4.4", 0],
      ["prediction_light_q4_4", "Predicted light Q4.4", 0],
      ["raw", "Raw sample", 0],
    ];

    function updateStatus(status) {
      const dot = $("statusDot");
      dot.className = `dot ${status.state || ""}`;
      $("statusText").textContent = `${status.state || "unknown"} - ${status.message || ""}`;
      $("portPill").textContent = `${status.port || "-"} - ${status.baud || "-"} baud`;
      $("samplePill").textContent = `${status.samples || samples.length} samples`;
      $("logPill").textContent = status.log_path ? status.log_path.split("/").slice(-2).join("/") : "no log";
    }

    function upsertSample(sample) {
      if (samples.length && samples[samples.length - 1].sequence === sample.sequence) return;
      samples.push(sample);
      while (samples.length > maxSamples) samples.shift();
      render();
    }

    function addRaw(line) {
      rawLines.push(line);
      while (rawLines.length > maxRawLines) rawLines.shift();
      $("rawLog").textContent = rawLines.join("\n");
      $("rawLog").scrollTop = $("rawLog").scrollHeight;
      $("rawPill").textContent = `${rawLines.length} lines`;
    }

    function render() {
      const last = samples[samples.length - 1];
      if (last) {
        $("mTemp").textContent = fmt(last.temperature_c, 2, " C");
        $("mPredTemp").textContent = fmt(last.prediction_temperature_c, 2, " C");
        $("mHum").textContent = fmt(last.humidity_pct, 2, " %");
        $("mDhtStatus").textContent = last.dht_status || "-";
        $("mLight").textContent = fmt(last.light_adc, 2);
        $("mPredLight").textContent = fmt(last.prediction_light_model, 2);
        $("mLightStatus").textContent = statusWithSensor(last.light_status, last.light_sensor);
        $("mLast").textContent = localClock(last.host_time_iso);
        renderLatestDetails(last);
      }
      $("samplePill").textContent = `${samples.length} samples`;
      $("rowsPill").textContent = `${samples.length} rows`;
      renderRows();
      tempChart.draw(samples);
      humChart.draw(samples);
      lightChart.draw(samples);
    }

    function renderLatestDetails(sample) {
      $("latestDetails").innerHTML = latestFields.map(([field, label, digits]) => `
        <div class="detail">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(fmtAny(sample[field], digits))}</strong>
        </div>
      `).join("");
    }

    function renderRows() {
      const rows = samples.slice(-80).reverse().map((s) => `
        <tr>
          <td>${escapeHtml(localClock(s.host_time_iso))}</td>
          <td>${escapeHtml(fmtAny(s.device_time_ms, 0))}</td>
          <td>${fmt(s.temperature_c, 2)}</td>
          <td>${escapeHtml(arrFmt(s.temperature_history_c, 2))}</td>
          <td>${fmt(s.prediction_temperature_c, 2)}</td>
          <td>${fmt(s.humidity_pct, 2)}</td>
          <td>${escapeHtml(fmtAny(s.dht_status, 0))}</td>
          <td>${escapeHtml(fmtAny(s.dht_error_count, 0))}</td>
          <td>${fmt(s.light_adc, 2)}</td>
          <td>${escapeHtml(arrFmt(s.light_history_adc, 2))}</td>
          <td>${fmt(s.prediction_light_model, 2)}</td>
          <td>${escapeHtml(fmtAny(s.light_status, 0))}</td>
          <td>${escapeHtml(fmtAny(s.light_sensor, 0))}</td>
          <td>${escapeHtml(fmtAny(s.temperature_q4_4, 0))}</td>
          <td>${escapeHtml(fmtAny(s.light_q4_4, 0))}</td>
          <td>${escapeHtml(fmtAny(s.prediction_temperature_q4_4, 0))}</td>
          <td>${escapeHtml(fmtAny(s.prediction_light_q4_4, 0))}</td>
        </tr>
      `);
      $("dataRows").innerHTML = rows.join("");
    }

    async function command(value) {
      await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: value }),
      });
    }

    async function resetSerial() {
      const button = $("resetBtn");
      button.disabled = true;
      button.textContent = "Resetting";
      try {
        const response = await fetch("/api/reset", { method: "POST" });
        const result = await response.json();
        if (result.status) updateStatus(result.status);
      } finally {
        setTimeout(() => {
          button.disabled = false;
          button.textContent = "Reset Serial";
        }, 800);
      }
    }

    async function resetBoard() {
      const button = $("boardResetBtn");
      button.disabled = true;
      button.textContent = "Resetting Board";
      try {
        const response = await fetch("/api/board-reset", { method: "POST" });
        const result = await response.json();
        if (result.status) updateStatus(result.status);
      } finally {
        setTimeout(() => {
          button.disabled = false;
          button.textContent = "Reset Board";
        }, 2200);
      }
    }

    document.querySelectorAll(".tab").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
        button.classList.add("active");
        ["live", "data", "raw"].forEach((name) => {
          $(`tab-${name}`).classList.toggle("hidden", name !== button.dataset.tab);
        });
      });
    });

    $("csvBtn").addEventListener("click", () => command("C"));
    $("testBtn").addEventListener("click", () => command("T"));
    $("resetBtn").addEventListener("click", resetSerial);
    $("boardResetBtn").addEventListener("click", resetBoard);

    async function loadInitialData() {
      const status = await fetch("/api/status").then((r) => r.json());
      updateStatus(status);
      const data = await fetch("/api/samples?limit=500").then((r) => r.json());
      for (const sample of data.samples || []) upsertSample(sample);
      const raw = await fetch("/api/raw").then((r) => r.json());
      for (const line of raw.raw || []) addRaw(line);
      render();
    }

    function connectEvents() {
      const events = new EventSource("/events");
      events.addEventListener("status", (event) => updateStatus(JSON.parse(event.data)));
      events.addEventListener("sample", (event) => upsertSample(JSON.parse(event.data)));
      events.addEventListener("raw", (event) => addRaw(JSON.parse(event.data).line));
      events.onerror = () => {
        $("statusText").textContent = "reconnecting events";
      };
    }

    loadInitialData().then(connectEvents);
  </script>
</body>
</html>
"""


def local_ip_hint() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "localhost"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DEEPCEL serial telemetry dashboard")
    parser.add_argument("--serial-port", default=None, help="Serial port, for example /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="Serial baud rate")
    parser.add_argument("--host", default="0.0.0.0", help="Web server bind address")
    parser.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT, help="Web server port")
    parser.add_argument("--max-samples", type=int, default=7200, help="Samples kept in memory")
    parser.add_argument(
        "--log-dir",
        default=str(Path(__file__).resolve().parent / "logs"),
        help="Directory for CSV logs",
    )
    parser.add_argument("--no-log", action="store_true", help="Disable CSV logging")
    parser.add_argument(
        "--no-csv-command",
        action="store_true",
        help="Do not send the C command when opening the serial port",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    serial_port = args.serial_port or detect_port()

    store = TelemetryStore(max_samples=max(100, args.max_samples))
    reader = SerialReader(
        store=store,
        port=serial_port,
        baud=args.baud,
        log_dir=Path(args.log_dir),
        log_enabled=not args.no_log,
        send_csv_command=not args.no_csv_command,
    )
    reader.start()

    server = DeepcelHttpServer((args.host, args.web_port), RequestHandler, store, reader)
    ip_hint = local_ip_hint()
    print(f"Serial: {serial_port or 'auto'} @ {args.baud} baud")
    print(f"Dashboard local: http://localhost:{args.web_port}")
    print(f"Network dashboard: http://{ip_hint}:{args.web_port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
    finally:
        server.server_close()
        reader.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
