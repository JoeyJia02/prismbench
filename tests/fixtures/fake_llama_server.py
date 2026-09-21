"""Protocol integration fixture. This program never loads a model or GPU."""

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int)
parser.add_argument("--ctx-size", type=int)
parser.add_argument("--api-key")
args, _ = parser.parse_known_args()
mode = os.environ.get("PRISMBENCH_TEST_MODE", "ok")
if mode == "oom_start":
    print("CUDA error: out of memory during model allocation", file=sys.stderr, flush=True)
    sys.exit(1)
if mode == "failed_start":
    print("Unsupported model architecture", file=sys.stderr, flush=True)
    sys.exit(1)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, value, status=200):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/health" and self.headers.get("Authorization") != "Bearer " + args.api_key:
            self.reply({"error": "unauthorized"}, 401)
        elif self.path == "/health":
            self.reply({"status": "ok"})
        elif self.path == "/slots":
            self.reply([{"id": 0, "n_ctx": args.ctx_size + (1 if mode == "wrong_context" else 0)}])
        else:
            self.reply({"model_path": "fixture.gguf"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/tokenize":
            self.reply({"tokens": list(range(len(body["content"].split()) + 1))})
            return
        if self.path.startswith("/slots/"):
            self.reply({"id_slot": 0, "n_erased": 3})
            return
        if mode in ("oom_request", "http500"):
            self.reply({"error": "CUDA out of memory" if mode == "oom_request" else "internal error"}, 500)
            return
        if not body.get("stream"):
            self.reply({"content": "42", "truncated": mode == "probe_truncated",
                        "timings": {"prompt_n": len(body["prompt"]),
                                    "cache_n": 1 if mode == "probe_cached" else 0}})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        if mode == "slow_drip":
            try:
                for _ in range(300):
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    time.sleep(.02)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            return
        events = [{"content": "", "stop": False}, {"content": "Hello", "stop": False},
                  {"content": " world", "stop": False}]
        if mode == "terminal_text_only":
            events = []
        if mode != "missing_terminal":
            events.append({"content": "aggregate text" if mode == "terminal_text_only" else "",
                           "stop": True, "truncated": False,
                           "timings": {"prompt_n": len(body["prompt"]), "cache_n": 0,
                                       "prompt_ms": 10, "prompt_per_second": len(body["prompt"]) * 100,
                                       "predicted_n": body["n_predict"], "predicted_ms": 100,
                                       "predicted_per_second": body["n_predict"] * 10}})
        for event in events:
            self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
            self.wfile.flush()
            time.sleep(.01)


print("load_tensors: offloaded 5/7 layers to GPU", file=sys.stderr, flush=True)
ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
