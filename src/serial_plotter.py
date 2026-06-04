"""
Serial Plotter for Arduino Vibe IDE.
Reads numeric data from serial port and formats it for plotting.
Supports Arduino Serial Plotter protocol (comma/whitespace/tab separated values).
"""

import re
import time
import threading
from dataclasses import dataclass, field
from typing import Optional

import serial


@dataclass
class DataPoint:
    timestamp: float
    values: list[float]
    raw_line: str


@dataclass
class PlotterData:
    points: list[DataPoint] = field(default_factory=list)
    max_points: int = 1000
    channels: int = 0
    started_at: float = 0.0

    def add_point(self, values: list[float], raw_line: str):
        point = DataPoint(timestamp=time.time(), values=values, raw_line=raw_line)
        self.points.append(point)
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]
        if values:
            self.channels = max(self.channels, len(values))

    def summary(self) -> dict:
        if not self.points:
            return {"channels": 0, "points": 0}
        stats = {}
        for ch in range(self.channels):
            vals = [p.values[ch] for p in self.points if ch < len(p.values)]
            if vals:
                stats[f"channel_{ch}"] = {"count": len(vals), "min": min(vals), "max": max(vals), "avg": sum(vals)/len(vals), "latest": vals[-1]}
        return {"channels": self.channels, "points": len(self.points), "stats": stats}


class SerialPlotter:
    def __init__(self):
        self.port: Optional[serial.Serial] = None
        self.path: str = ""
        self.baudrate: int = 115200
        self.connected: bool = False
        self.data = PlotterData()
        self._running: bool = False
        self._read_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: list = []

    def open(self, path: str, baudrate: int = 115200) -> dict:
        with self._lock:
            try:
                if self.port and self.port.is_open:
                    self.close()
                self.port = serial.Serial(port=path, baudrate=baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
                self.path = path
                self.baudrate = baudrate
                self.connected = True
                self.data = PlotterData()
                self.data.started_at = time.time()
                self._running = True
                self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
                self._read_thread.start()
                return {"status": "connected", "path": self.path, "baudrate": self.baudrate, "message": f"Plotter connected to {path}"}
            except serial.SerialException as e:
                return {"status": "error", "message": f"Serial error: {e}"}

    def _read_loop(self):
        buffer = ""
        while self._running:
            try:
                if self.port.in_waiting:
                    raw = self.port.read(self.port.in_waiting)
                    text = raw.decode("utf-8", errors="replace")
                    buffer += text
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            values = self._parse_line(line)
                            if values:
                                self.data.add_point(values, line)
            except serial.SerialException:
                self.connected = False
                break
            except Exception:
                time.sleep(0.01)

    def _parse_line(self, line: str) -> list[float]:
        tokens = re.split(r"[,\t\s]+", line.strip())
        values = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            match = re.search(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?", token)
            if match:
                try:
                    values.append(float(match.group()))
                except ValueError:
                    pass
        return values

    def read_latest(self, count: int = 50) -> dict:
        with self._lock:
            points = self.data.points[-count:] if count else self.data.points
            return {"status": "connected" if self.connected else "disconnected", "path": self.path, "points_count": len(points),
                    "points": [{"timestamp": p.timestamp, "values": p.values, "raw": p.raw_line} for p in points],
                    "summary": self.data.summary()}

    def get_summary(self) -> dict:
        with self._lock:
            return {"connected": self.connected, "path": self.path, **self.data.summary()}

    def close(self) -> dict:
        with self._lock:
            self._running = False
            if self._read_thread:
                self._read_thread.join(timeout=2)
            if self.port and self.port.is_open:
                try: self.port.close()
                except serial.SerialException: pass
            self.connected = False
            return {"status": "closed", "path": self.path, "message": f"Plotter disconnected", "data_collected": len(self.data.points)}
