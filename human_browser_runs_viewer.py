#!/usr/bin/env python3
"""Serve a small local dashboard for recorded browser runs."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


VERSION = "0.3.0"
RUN_ID_PATTERN = r"^run_(\d+)(?:$|_.+)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="human-browser-viewer",
        description="Browse recorded runs and open traces locally.",
    )
    parser.add_argument(
        "--runs-dir",
        default="runs",
        help="Directory that contains recorded runs (default: runs)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for the local viewer (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for the local viewer (default: 8765)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the dashboard in a browser",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def load_metadata(run_dir: Path) -> dict:
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def extract_run_sort_key(run_dir: Path) -> tuple[int, str]:
    parts = run_dir.name.split("_", 2)
    if len(parts) >= 2 and parts[0] == "run" and parts[1].isdigit():
        return int(parts[1]), run_dir.name
    return -1, run_dir.name


def list_runs(runs_dir: Path) -> list[dict]:
    runs: list[dict] = []
    if not runs_dir.exists():
        return runs

    for run_dir in sorted(runs_dir.iterdir(), key=extract_run_sort_key, reverse=True):
        if not run_dir.is_dir():
            continue

        metadata = load_metadata(run_dir)
        trace_path = run_dir / "trace.zip"
        runs.append(
            {
                "folder_name": run_dir.name,
                "run_id": metadata.get("run_id", run_dir.name),
                "task_name": metadata.get("task_name", ""),
                "start_time": metadata.get("start_time", ""),
                "end_time": metadata.get("end_time", ""),
                "start_url": metadata.get("start_url", ""),
                "trace_exists": trace_path.exists(),
                "trace_size_mb": round(trace_path.stat().st_size / (1024 * 1024), 2)
                if trace_path.exists()
                else None,
            }
        )
    return runs


def open_trace_viewer(trace_path: Path) -> None:
    subprocess.Popen([sys.executable, "-m", "playwright", "show-trace", str(trace_path)])


def render_index(runs_dir: Path, base_url: str) -> str:
    cards: list[str] = []
    runs = list_runs(runs_dir)

    if not runs:
        empty = (
            "<div class='empty'>No runs found yet. Record one with "
            "<code>human-browser-recorder</code>.</div>"
        )
        return page_html(empty, base_url, runs_dir)

    for run in runs:
        folder_name = run["folder_name"]
        start_url = run["start_url"]
        start_url_html = (
            f"<a href='{html.escape(start_url)}' target='_blank' rel='noreferrer'>{html.escape(start_url)}</a>"
            if start_url
            else "<span class='muted'>n/a</span>"
        )
        trace_actions = "<span class='muted'>No trace.zip</span>"
        if run["trace_exists"]:
            encoded_folder = urllib.parse.quote(folder_name)
            trace_url = f"{base_url}/files/{encoded_folder}/trace.zip"
            trace_viewer_url = (
                "https://trace.playwright.dev/?trace="
                + urllib.parse.quote(trace_url, safe="")
            )
            trace_actions = (
                f"<a class='button' href='/open?run={encoded_folder}'>Open CLI Viewer</a>"
                f"<a class='button secondary' href='{html.escape(trace_viewer_url)}' "
                "target='_blank' rel='noreferrer'>Open Web Viewer</a>"
                f"<a class='button secondary' href='/files/{encoded_folder}/trace.zip'>Download Trace</a>"
            )

        cards.append(
            f"""
            <section class="card">
              <div class="card-header">
                <div>
                  <h2>{html.escape(folder_name)}</h2>
                  <div class="meta">{html.escape(run["run_id"])}{format_task_name(run["task_name"])}</div>
                </div>
              </div>
              <div class="grid">
                <div><span class="label">Start time</span><span>{html.escape(run["start_time"] or "n/a")}</span></div>
                <div><span class="label">End time</span><span>{html.escape(run["end_time"] or "n/a")}</span></div>
                <div><span class="label">Start URL</span><span>{start_url_html}</span></div>
                <div><span class="label">Trace</span><span>{format_trace_label(run["trace_exists"], run["trace_size_mb"])}</span></div>
              </div>
              <div class="actions">{trace_actions}</div>
            </section>
            """
        )

    return page_html("".join(cards), base_url, runs_dir)


def format_task_name(task_name: str) -> str:
    if not task_name:
        return ""
    return f" · {html.escape(task_name)}"


def format_trace_label(trace_exists: bool, trace_size_mb: float | None) -> str:
    if not trace_exists:
        return "<span class='muted'>missing</span>"
    if trace_size_mb is None:
        return "present"
    return f"present · {trace_size_mb} MB"


def page_html(content: str, base_url: str, runs_dir: Path) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Human Browser Runs</title>
  <style>
    :root {{
      --bg: #f6f3ea;
      --ink: #1e1a17;
      --muted: #6d6258;
      --line: #d9cdbd;
      --accent: #0c6b58;
      --card: #fffdf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(12,107,88,0.10), transparent 28rem),
        linear-gradient(180deg, #fbf8f1 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 2.5rem;
      line-height: 1;
    }}
    p {{
      color: var(--muted);
      margin: 0 0 24px;
      max-width: 56rem;
    }}
    code {{
      background: rgba(0,0,0,0.04);
      padding: 0.1rem 0.35rem;
      border-radius: 6px;
      font-size: 0.92em;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-bottom: 24px;
      color: var(--muted);
    }}
    .button {{
      display: inline-block;
      text-decoration: none;
      background: var(--accent);
      color: white;
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 0.95rem;
      border: 1px solid var(--accent);
    }}
    .button.secondary {{
      background: transparent;
      color: var(--accent);
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px 18px 16px;
      margin-bottom: 16px;
      box-shadow: 0 10px 30px rgba(30, 26, 23, 0.05);
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 16px;
      margin-bottom: 14px;
    }}
    h2 {{
      margin: 0;
      font-size: 1.35rem;
    }}
    .meta {{
      color: var(--muted);
      margin-top: 4px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px 18px;
      margin-bottom: 16px;
    }}
    .grid div {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }}
    .label {{
      color: var(--muted);
      font-size: 0.88rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .empty {{
      border: 1px dashed var(--line);
      border-radius: 18px;
      padding: 28px;
      background: rgba(255,255,255,0.65);
      color: var(--muted);
    }}
    .muted {{
      color: var(--muted);
    }}
    a {{
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <main>
    <h1>Human Browser Runs</h1>
    <p>Local dashboard for recorded trajectories. Use <code>Open CLI Viewer</code> to launch Playwright's desktop trace viewer, or <code>Open Web Viewer</code> to try the browser-based Playwright viewer against this local server.</p>
    <div class="toolbar">
      <span>Runs directory: <code>{html.escape(str(runs_dir))}</code></span>
      <span>Viewer URL: <code>{html.escape(base_url)}</code></span>
    </div>
    {content}
  </main>
</body>
</html>"""


class RunsHandler(BaseHTTPRequestHandler):
    runs_dir: Path
    base_url: str

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.respond_html(render_index(self.runs_dir, self.base_url))
            return
        if parsed.path == "/open":
            query = urllib.parse.parse_qs(parsed.query)
            self.handle_open_trace(query.get("run", [""])[0])
            return
        if parsed.path.startswith("/files/"):
            self.handle_static_file(parsed.path)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_HEAD(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.respond_html(render_index(self.runs_dir, self.base_url), include_body=False)
            return
        if parsed.path.startswith("/files/"):
            self.handle_static_file(parsed.path, include_body=False)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        return

    def handle_open_trace(self, run_name: str) -> None:
        run_dir = self.safe_run_dir(run_name)
        trace_path = run_dir / "trace.zip"
        if not trace_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Trace file not found")
            return

        open_trace_viewer(trace_path)
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/")
        self.end_headers()

    def handle_static_file(self, path: str, include_body: bool = True) -> None:
        parts = path.split("/")
        if len(parts) != 4:
            self.send_error(HTTPStatus.NOT_FOUND, "Invalid file path")
            return

        _, _, run_name, file_name = parts
        if file_name not in {"trace.zip", "metadata.json"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Unsupported file")
            return

        file_path = self.safe_run_dir(run_name) / file_name
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type = "application/zip" if file_name.endswith(".zip") else "application/json"
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if include_body:
            self.wfile.write(data)

    def safe_run_dir(self, run_name: str) -> Path:
        decoded = urllib.parse.unquote(run_name)
        run_dir = (self.runs_dir / decoded).resolve()
        runs_root = self.runs_dir.resolve()
        if runs_root not in run_dir.parents and run_dir != runs_root:
            raise PermissionError("Invalid run path")
        return run_dir

    def respond_html(self, body: str, include_body: bool = True) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if include_body:
            self.wfile.write(encoded)


def build_handler(runs_dir: Path, base_url: str):
    class ConfiguredRunsHandler(RunsHandler):
        pass

    ConfiguredRunsHandler.runs_dir = runs_dir
    ConfiguredRunsHandler.base_url = base_url
    return ConfiguredRunsHandler


def main() -> int:
    args = parse_args()
    runs_dir = Path(args.runs_dir).expanduser().resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    base_url = f"http://{args.host}:{args.port}"
    handler = build_handler(runs_dir, base_url)
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print("Human Browser Runs Viewer")
    print()
    print(f"Runs directory: {runs_dir}")
    print(f"Local URL: {base_url}")
    print()
    print("Press Ctrl+C to stop the viewer.")

    if not args.no_browser:
        webbrowser.open(base_url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopping viewer...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
