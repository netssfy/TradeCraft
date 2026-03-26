from __future__ import annotations

import json
import sys
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def create_trader() -> None:
    payload = json.dumps({
        "id": "test",
        "market": "HK",
        "initial_cash": 1000000,
        "allowed_symbols": ["1810.HK"],
        "commission_rate": 0.001,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/traders",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if line:
                print(line)
                sys.stdout.flush()


if __name__ == "__main__":
    create_trader()
