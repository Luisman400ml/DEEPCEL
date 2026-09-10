#!/usr/bin/env python3
"""DEEPCEL desktop serial plotter.

Tkinter app for plotting MKR Vidor telemetry directly on the Raspberry display.
It uses only the standard library plus pyserial.
"""

from __future__ import annotations

import argparse
import queue
import serial
import sys
import threading
import time
import tkinter as tk
from collections import deque
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Any

from deepcel_serial_dashboard import CsvLogger, DeepcelParser, detect_port


DEFAULT_BAUD = 9600
MAX_SAMPLES = 720
MAX_RAW_LINES = 240


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def fmt(value: Any, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "-"


def clock_label(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).strftime("%H:%M:%S")
    except ValueError:
        return "-"


class SerialWorker:
    def __init__(
        self,
        events: queue.Queue[tuple[str, Any]],
        commands: queue.Queue[str],
        requested_port: str | None,
        baud: int,
        log_dir: Path,
        log_enabled: bool,
    ) -> None:
        self.events = events
        self.commands = commands
        self.requested_port = requested_port
        self.baud = baud
        self.log_dir = log_dir
        self.log_enabled = log_enabled
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name="deepcel-tk-serial", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=3)

    def selected_port(self) -> str | None:
        if self.requested_port and Path(self.requested_port).exists():
            return self.requested_port
        return detect_port()

    def emit(self, kind: str, data: Any) -> None:
        self.events.put((kind, data))

    def run(self) -> None:
        parser = DeepcelParser()
        logger = CsvLogger(self.log_dir, self.log_enabled)
        log_path = logger.open()
        self.emit(
            "status",
            {
                "state": "starting",
                "message": "opening serial",
                "port": self.requested_port or "auto",
                "log_path": str(log_path) if log_path else None,
            },
        )

        try:
            while not self.stop_event.is_set():
                port = self.selected_port()
                if not port:
                    self.emit(
                        "status",
                        {
                            "state": "waiting",
                            "message": "waiting for MKR serial port",
                            "port": self.requested_port or "auto",
                        },
                    )
                    time.sleep(2)
                    continue

                try:
                    self.read_port(port, parser, logger)
                except (OSError, serial.SerialException) as exc:
                    self.emit(
                        "status",
                        {"state": "error", "message": str(exc), "port": port},
                    )
                    time.sleep(2)
        finally:
            logger.close()
            self.emit("status", {"state": "stopped", "message": "serial stopped"})

    def read_port(self, port: str, parser: DeepcelParser, logger: CsvLogger) -> None:
        with serial.Serial(port, self.baud, timeout=1.0, write_timeout=1.0) as ser:
            time.sleep(1.5)
            ser.write(b"C")
            ser.flush()
            self.emit(
                "status",
                {
                    "state": "connected",
                    "message": "reading telemetry",
                    "port": port,
                    "connected_at": now_iso(),
                },
            )

            while not self.stop_event.is_set():
                self.flush_commands(ser)
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                self.emit("raw", line)
                if line.startswith(("DHT20 read error", "ERROR:")):
                    self.emit("status", {"state": "connected", "message": line, "port": port})
                sample_fields = parser.parse(line)
                if sample_fields is None:
                    continue
                sample = {
                    "host_time_iso": now_iso(),
                    "host_time_s": time.time(),
                    **sample_fields,
                }
                logger.write(sample)
                self.emit("sample", sample)

    def flush_commands(self, ser: serial.Serial) -> None:
        while True:
            try:
                command = self.commands.get_nowait()
            except queue.Empty:
                return
            payload = command.encode("ascii", errors="ignore")[:1]
            if payload:
                ser.write(payload)
                ser.flush()


class LineChart(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        series: list[tuple[str, str, str]],
        height: int = 220,
    ) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.series = series
        self.height = height
        head = ttk.Frame(self, style="Panel.TFrame")
        head.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(head, text=title, style="PanelTitle.TLabel").pack(side="left")
        legend = ttk.Frame(head, style="Panel.TFrame")
        legend.pack(side="right")
        for _, label, color in self.series:
            item = ttk.Label(legend, text=f"-- {label}", foreground=color, style="Legend.TLabel")
            item.pack(side="left", padx=(10, 0))
        self.canvas = tk.Canvas(self, height=height, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", lambda _event: self.draw([]))
        self._last_samples: list[dict[str, Any]] = []

    def draw(self, samples: list[dict[str, Any]]) -> None:
        if samples:
            self._last_samples = samples
        else:
            samples = self._last_samples

        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), self.height)
        left, right, top, bottom = 58, 16, 16, 30
        plot_w = width - left - right
        plot_h = height - top - bottom

        rows = samples[-120:]
        values: list[float] = []
        for sample in rows:
            for field, _label, _color in self.series:
                value = self.number(sample.get(field))
                if value is not None:
                    values.append(value)

        for index in range(5):
            y = top + plot_h * index / 4
            canvas.create_line(left, y, width - right, y, fill="#d9e0e7")

        if not rows or not values:
            canvas.create_text(left, top + 24, text="No data", anchor="w", fill="#607080")
            return

        ymin = min(values)
        ymax = max(values)
        if ymin == ymax:
            ymin -= 1
            ymax += 1
        else:
            margin = (ymax - ymin) * 0.08
            ymin -= margin
            ymax += margin

        for index in range(5):
            y = top + plot_h * index / 4
            value = ymax - (ymax - ymin) * index / 4
            canvas.create_text(8, y, text=f"{value:.1f}", anchor="w", fill="#607080", font=("TkDefaultFont", 9))

        def x_at(index: int) -> float:
            if len(rows) == 1:
                return left + plot_w
            return left + plot_w * index / (len(rows) - 1)

        def y_at(value: float) -> float:
            return top + plot_h - ((value - ymin) / (ymax - ymin)) * plot_h

        for field, _label, color in self.series:
            points: list[float] = []
            for index, sample in enumerate(rows):
                value = self.number(sample.get(field))
                if value is None:
                    continue
                points.extend([x_at(index), y_at(value)])
            if len(points) >= 4:
                canvas.create_line(*points, fill=color, width=2.2, smooth=True)
            elif len(points) == 2:
                x, y = points
                canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline=color)

        first = clock_label(rows[0].get("host_time_iso"))
        last = clock_label(rows[-1].get("host_time_iso"))
        canvas.create_text(left, height - 10, text=first, anchor="w", fill="#607080", font=("TkDefaultFont", 9))
        canvas.create_text(width - right, height - 10, text=last, anchor="e", fill="#607080", font=("TkDefaultFont", 9))

    @staticmethod
    def number(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class DeepcelTkApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root = root
        self.args = args
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.commands: queue.Queue[str] = queue.Queue()
        self.samples: deque[dict[str, Any]] = deque(maxlen=MAX_SAMPLES)
        self.raw_lines: deque[str] = deque(maxlen=MAX_RAW_LINES)
        self.worker = SerialWorker(
            self.events,
            self.commands,
            args.serial_port,
            args.baud,
            Path(args.log_dir),
            not args.no_log,
        )

        self.root.title("DEEPCEL Telemetry")
        self.root.geometry("1180x760")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.setup_styles()
        self.build_ui()
        self.worker.start()
        self.root.after(100, self.process_events)

    def setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("TkDefaultFont", 10), background="#f4f6f8", foreground="#16202a")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Header.TFrame", background="#fbfcfd")
        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"), background="#fbfcfd")
        style.configure("PanelTitle.TLabel", font=("TkDefaultFont", 11, "bold"), background="#ffffff")
        style.configure("Legend.TLabel", background="#ffffff")
        style.configure("Metric.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("MetricName.TLabel", background="#ffffff", foreground="#607080", font=("TkDefaultFont", 9))
        style.configure("MetricValue.TLabel", background="#ffffff", font=("TkDefaultFont", 17, "bold"))
        style.configure("Status.TLabel", background="#f4f6f8", foreground="#607080")
        style.configure("TButton", padding=(10, 6))

    def build_ui(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="DEEPCEL Telemetry", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="CSV", command=lambda: self.commands.put("C")).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="Test", command=lambda: self.commands.put("T")).pack(side="right", padx=(6, 0))

        body = ttk.Frame(self.root, padding=(16, 14))
        body.pack(fill="both", expand=True)

        status_row = ttk.Frame(body)
        status_row.pack(fill="x", pady=(0, 12))
        self.status_dot = tk.Canvas(status_row, width=14, height=14, bg="#f4f6f8", highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 8))
        self.status_label = ttk.Label(status_row, text="starting", style="Status.TLabel")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.port_label = ttk.Label(status_row, text="-", style="Status.TLabel")
        self.port_label.pack(side="right")
        self.draw_status_dot("#ad7418")

        metrics = ttk.Frame(body)
        metrics.pack(fill="x", pady=(0, 12))
        self.metric_labels: dict[str, ttk.Label] = {}
        metric_defs = [
            ("temperature_c", "Temperature"),
            ("prediction_temperature_c", "Pred. temp."),
            ("humidity_pct", "Humidity"),
            ("light_adc", "Light"),
            ("prediction_light_model", "Pred. light"),
            ("last", "Last sample"),
        ]
        for col, (key, label) in enumerate(metric_defs):
            metrics.columnconfigure(col, weight=1)
            card = ttk.Frame(metrics, style="Metric.TFrame", padding=(12, 10))
            card.grid(row=0, column=col, padx=4, sticky="ew")
            ttk.Label(card, text=label, style="MetricName.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="-", style="MetricValue.TLabel")
            value.pack(anchor="w", pady=(5, 0))
            self.metric_labels[key] = value

        panes = ttk.PanedWindow(body, orient="vertical")
        panes.pack(fill="both", expand=True)

        top = ttk.Frame(panes)
        panes.add(top, weight=3)
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)
        top.rowconfigure(0, weight=1)
        top.rowconfigure(1, weight=1)

        self.temp_chart = LineChart(
            top,
            "Temperature",
            [
                ("temperature_c", "sensor", "#0f7d78"),
                ("prediction_temperature_c", "FPGA", "#315f9e"),
            ],
        )
        self.temp_chart.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 7))
        self.humidity_chart = LineChart(top, "Humidity", [("humidity_pct", "DHT20", "#b8475a")])
        self.humidity_chart.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 7))
        self.light_chart = LineChart(
            top,
            "Light",
            [
                ("light_adc", "I2C sensor", "#ad7418"),
                ("prediction_light_model", "FPGA", "#315f9e"),
            ],
        )
        self.light_chart.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(7, 0))

        bottom = ttk.Notebook(panes)
        panes.add(bottom, weight=1)

        table_frame = ttk.Frame(bottom)
        bottom.add(table_frame, text="Data")
        columns = ("time", "mcu", "temp", "pred_temp", "humidity", "light", "pred_light", "light_status")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        labels = {
            "time": "Time",
            "mcu": "t MCU",
            "temp": "Temp C",
            "pred_temp": "Pred C",
            "humidity": "Humidity",
            "light": "Light",
            "pred_light": "Pred light",
            "light_status": "Light status",
        }
        widths = {
            "time": 95,
            "mcu": 80,
            "temp": 80,
            "pred_temp": 80,
            "humidity": 80,
            "light": 80,
            "pred_light": 90,
            "light_status": 90,
        }
        for col in columns:
            self.table.heading(col, text=labels[col])
            self.table.column(col, width=widths[col], anchor="e")
        self.table.column("time", anchor="w")
        self.table.pack(fill="both", expand=True)

        raw_frame = ttk.Frame(bottom)
        bottom.add(raw_frame, text="Serial")
        self.raw_text = tk.Text(raw_frame, height=8, bg="#101820", fg="#e4edf4", insertbackground="#e4edf4")
        self.raw_text.pack(fill="both", expand=True)

    def draw_status_dot(self, color: str) -> None:
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline=color)

    def process_events(self) -> None:
        while True:
            try:
                kind, data = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self.update_status(data)
            elif kind == "raw":
                self.add_raw(data)
            elif kind == "sample":
                self.add_sample(data)
        self.root.after(100, self.process_events)

    def update_status(self, status: dict[str, Any]) -> None:
        state = status.get("state", "-")
        message = status.get("message", "")
        self.status_label.configure(text=f"{state} - {message}")
        self.port_label.configure(text=f"{status.get('port', '-')} @ {self.args.baud} baud")
        if state == "connected" and message.startswith(("DHT20 read error", "ERROR:")):
            self.draw_status_dot("#b8475a")
        elif state == "connected":
            self.draw_status_dot("#27865a")
        elif state == "error":
            self.draw_status_dot("#b8475a")
        else:
            self.draw_status_dot("#ad7418")

    def add_raw(self, line: str) -> None:
        self.raw_lines.append(line)
        self.raw_text.configure(state="normal")
        self.raw_text.delete("1.0", "end")
        self.raw_text.insert("end", "\n".join(self.raw_lines))
        self.raw_text.see("end")

    def add_sample(self, sample: dict[str, Any]) -> None:
        self.samples.append(sample)
        self.metric_labels["temperature_c"].configure(text=fmt(sample.get("temperature_c"), 2, " C"))
        self.metric_labels["prediction_temperature_c"].configure(
            text=fmt(sample.get("prediction_temperature_c"), 2, " C")
        )
        self.metric_labels["humidity_pct"].configure(text=fmt(sample.get("humidity_pct"), 2, " %"))
        self.metric_labels["light_adc"].configure(text=fmt(sample.get("light_adc"), 2))
        self.metric_labels["prediction_light_model"].configure(text=fmt(sample.get("prediction_light_model"), 2))
        self.metric_labels["last"].configure(text=clock_label(sample.get("host_time_iso")))

        values = (
            clock_label(sample.get("host_time_iso")),
            sample.get("device_time_ms") or "-",
            fmt(sample.get("temperature_c")),
            fmt(sample.get("prediction_temperature_c")),
            fmt(sample.get("humidity_pct")),
            fmt(sample.get("light_adc"), 2),
            fmt(sample.get("prediction_light_model"), 2),
            sample.get("light_status") or "-",
        )
        self.table.insert("", 0, values=values)
        for item in self.table.get_children()[80:]:
            self.table.delete(item)

        rows = list(self.samples)
        self.temp_chart.draw(rows)
        self.humidity_chart.draw(rows)
        self.light_chart.draw(rows)

    def close(self) -> None:
        self.worker.stop()
        self.root.destroy()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DEEPCEL desktop serial plotter")
    parser.add_argument("--serial-port", default=None, help="Serial port, for example /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument(
        "--log-dir",
        default=str(Path(__file__).resolve().parent / "logs"),
        help="Directory for CSV logs",
    )
    parser.add_argument("--no-log", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = tk.Tk()
    DeepcelTkApp(root, args)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
