"""Smoke test for the PP-DocLayoutV3 Triton server.

Usage:
    pip install tritonclient[http] pillow
    python test_server.py path/to/page.png [path/to/page2.png ...]

Sends each image as a separate request and prints the returned LayoutItem JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tritonclient.http as httpclient


MODEL_NAME = "PP-DocLayoutV3"


def infer_one(client: httpclient.InferenceServerClient, image_path: Path) -> list[dict]:
    img_bytes = image_path.read_bytes()
    data = np.array([[img_bytes]], dtype=object)  # [batch=1, dim=1]

    infer_input = httpclient.InferInput("image_bytes", data.shape, "BYTES")
    infer_input.set_data_from_numpy(data, binary_data=True)

    requested = httpclient.InferRequestedOutput("layout_items", binary_data=True)

    response = client.infer(
        model_name=MODEL_NAME,
        inputs=[infer_input],
        outputs=[requested],
    )
    out = response.as_numpy("layout_items")  # [1, 1] object array of bytes
    payload = out[0, 0]
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    return json.loads(payload)


def main(images: list[Path], url: str) -> int:
    client = httpclient.InferenceServerClient(url=url, verbose=False)

    if not client.is_server_live():
        print(f"Server not live at {url}", file=sys.stderr)
        return 1
    if not client.is_model_ready(MODEL_NAME):
        print(f"Model '{MODEL_NAME}' not ready", file=sys.stderr)
        return 1

    exit_code = 0
    for path in images:
        if not path.is_file():
            print(f"[FAIL] {path}: not a file", file=sys.stderr)
            exit_code = 1
            continue
        try:
            items = infer_one(client, path)
        except Exception as exc:
            print(f"[FAIL] {path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        print(f"[OK]   {path}: {len(items)} items")
        for it in items[:5]:
            bb = it["bbox"]
            print(
                f"       order={it['order']:>3}  label={it['label']:<20} "
                f"score={it['score']:.3f}  bbox=({bb['x1']},{bb['y1']})-({bb['x2']},{bb['y2']})"
            )
        if len(items) > 5:
            print(f"       ... ({len(items) - 5} more)")

    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path, help="Image files to send")
    parser.add_argument("--host", default="localhost", help="Triton host")
    parser.add_argument("--port", type=int, default=8000, help="Triton HTTP port")
    args = parser.parse_args()

    url = f"{args.host}:{args.port}"
    main(args.images, url)
