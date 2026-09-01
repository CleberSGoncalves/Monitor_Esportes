import os
import time
from threading import Lock

class PerfLogger:

    def __init__(self, path="logs/detector_timing.log"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.lock = Lock()

    def log(self, data: dict):

        line = " | ".join(
            f"{k}={v:.2f}ms" if isinstance(v, (int, float)) else f"{k}={v}"
            for k, v in data.items()
        )

        with self.lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")