#!/usr/bin/env python3
"""Record a human browser trajectory as a Playwright trace."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


DEFAULT_START_URL = "https://google.com"
DEFAULT_VIEWPORT = (1280, 900)
RUN_ID_PATTERN = re.compile(r"^run_(\d{4})$")
VERSION = "0.2.2"


def timestamp_now() -> str:
    """Return an ISO 8601 timestamp in the local timezone."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_viewport(value: str) -> tuple[int, int]:
    """Parse a viewport string such as 1280x900."""
    match = re.fullmatch(r"(\d+)x(\d+)", value.strip())
    if not match:
        raise argparse.ArgumentTypeError("viewport must look like WIDTHxHEIGHT, e.g. 1280x900")

    width, height = (int(part) for part in match.groups())
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("viewport dimensions must be positive integers")
    return width, height


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="human-browser-recorder",
        description="Record a human browser session as a Playwright trace.",
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Optional starting URL. Equivalent to --start-url.",
    )
    parser.add_argument(
        "--start-url",
        default=DEFAULT_START_URL,
        help=f"Starting URL to open in the browser (default: {DEFAULT_START_URL})",
    )
    parser.add_argument(
        "--viewport",
        type=parse_viewport,
        default=DEFAULT_VIEWPORT,
        help="Viewport size in WIDTHxHEIGHT format (default: 1280x900)",
    )
    parser.add_argument(
        "--runs-dir",
        default="runs",
        help="Directory used to store recorded runs (default: runs)",
    )
    parser.add_argument(
        "--task-name",
        help="Task name used in the output folder and metadata. If omitted, a terminal prompt appears.",
    )
    parser.add_argument(
        "--show-trace",
        action="store_true",
        help="Open the saved trace in Playwright Trace Viewer after recording",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


def parse_args() -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args()

    if args.url:
        if args.start_url != DEFAULT_START_URL:
            parser.error("use either the positional URL or --start-url, not both")
        args.start_url = args.url

    return args


def ensure_runs_dir(runs_dir: Path) -> Path:
    """Create the runs directory when it does not already exist."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


def slugify_task_name(task_name: str, max_length: int = 80) -> str:
    """Convert a human-readable task name into a filesystem-safe slug."""
    normalized = unicodedata.normalize("NFKD", task_name)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "task"


def generate_run_id(runs_dir: Path) -> str:
    """Return the next run ID using a zero-padded sequence."""
    highest_run_number = 0

    for child in runs_dir.iterdir():
        if not child.is_dir():
            continue
        match = RUN_ID_PATTERN.fullmatch(child.name)
        if match:
            highest_run_number = max(highest_run_number, int(match.group(1)))

    return f"run_{highest_run_number + 1:04d}"


def create_run_folder(runs_dir: Path, task_name: str) -> tuple[str, Path]:
    """Create a new run folder and return the run ID with its path."""
    ensure_runs_dir(runs_dir)
    run_id = generate_run_id(runs_dir)
    task_slug = slugify_task_name(task_name)
    run_dir = runs_dir / f"{run_id}_{task_slug}"
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_id, run_dir


def save_metadata(
    run_dir: Path,
    run_id: str,
    task_name: str,
    start_time: str,
    end_time: str,
    start_url: str,
    viewport: tuple[int, int],
) -> Path:
    """Write run metadata next to the trace archive."""
    metadata = {
        "run_id": run_id,
        "task_name": task_name,
        "start_time": start_time,
        "end_time": end_time,
        "start_url": start_url,
        "browser": "chromium",
        "viewport": list(viewport),
    }
    metadata_path = run_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata_path


def launch_browser(playwright):
    """Launch Chrome when available and otherwise fall back to Chromium."""
    try:
        browser = playwright.chromium.launch(channel="chrome", headless=False)
        print("Browser channel: chrome")
        return browser
    except PlaywrightError as exc:
        print(f"Chrome launch unavailable ({exc}). Falling back to bundled Chromium.")
        browser = playwright.chromium.launch(headless=False)
        print("Browser channel: chromium")
        return browser


def open_trace_viewer(trace_path: Path) -> None:
    """Open the saved trace in the Playwright Trace Viewer."""
    subprocess.Popen([sys.executable, "-m", "playwright", "show-trace", str(trace_path)])


def prompt_for_task_name() -> str | None:
    """Ask the user for a task name in the terminal."""
    while True:
        try:
            task_name = input("Task name for this run: ").strip()
        except EOFError:
            return None
        if task_name:
            return task_name
        print("Task name cannot be empty.")


def wait_for_stop_signal() -> None:
    """Block until the user presses ESC globally, with a terminal fallback."""
    try:
        from pynput import keyboard
    except ImportError:
        print("Global ESC capture is unavailable because pynput is not installed.")
        print("Press ENTER here to finish the task.")
        input()
        return

    print("Press ESC anywhere to finish the task.")
    print("Press Ctrl+C in the terminal if you need to interrupt early.")
    print()

    def on_press(key):
        if key == keyboard.Key.esc:
            return False
        return True

    try:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except Exception as exc:
        print(f"Warning: could not start the global ESC listener: {exc}")
        print("Falling back to ENTER in the terminal.")
        input()


def main() -> int:
    args = parse_args()
    runs_dir = Path(args.runs_dir).expanduser().resolve()
    task_name = args.task_name.strip() if args.task_name else prompt_for_task_name()
    if not task_name:
        print("Recording cancelled before launch.")
        return 1

    run_id, run_dir = create_run_folder(runs_dir, task_name)
    trace_path = run_dir / "trace.zip"
    start_time = timestamp_now()
    end_time = start_time
    browser = None
    context = None
    playwright = None
    trace_saved = False
    exit_code = 0

    print("Human Browser Trajectory Recorder")
    print()
    print(f"Task name: {task_name}")
    print(f"Start URL: {args.start_url}")
    print(f"Run ID: {run_id}")
    print(f"Run folder: {run_dir}")
    print()
    print("A browser window will open.")
    print("Use it normally.")
    print()
    print("Press ESC anywhere when you finish the task.")
    print()

    try:
        playwright = sync_playwright().start()
        browser = launch_browser(playwright)
        context = browser.new_context(viewport={"width": args.viewport[0], "height": args.viewport[1]})

        # Record screenshots, DOM snapshots, and sources so the trace can be replayed later.
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()
        try:
            page.goto(args.start_url, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            print(f"Warning: could not fully load {args.start_url}: {exc}")
        page.bring_to_front()

        wait_for_stop_signal()
    except EOFError:
        print()
        print("EOF received. Finalizing the trace...")
    except KeyboardInterrupt:
        print()
        print("Interrupt received. Finalizing the trace...")
    except PlaywrightError as exc:
        print(f"Playwright error: {exc}")
        print("If browser binaries are missing, run: python -m playwright install")
        exit_code = 1
    finally:
        end_time = timestamp_now()

        if context is not None and not trace_saved:
            try:
                context.tracing.stop(path=str(trace_path))
                trace_saved = True
            except PlaywrightError as exc:
                print(f"Warning: failed to save trace: {exc}")

        save_metadata(
            run_dir=run_dir,
            run_id=run_id,
            task_name=task_name,
            start_time=start_time,
            end_time=end_time,
            start_url=args.start_url,
            viewport=args.viewport,
        )

        if context is not None:
            try:
                context.close()
            except PlaywrightError:
                pass

        if browser is not None:
            try:
                browser.close()
            except PlaywrightError:
                pass

        if playwright is not None:
            try:
                playwright.stop()
            except PlaywrightError:
                pass

    if trace_saved:
        print(f"Trace saved to: {trace_path}")
    else:
        print(f"Trace was not saved successfully. Check the run folder: {run_dir}")

    print(f"Metadata saved to: {run_dir / 'metadata.json'}")

    if trace_saved and args.show_trace:
        print("Opening Playwright Trace Viewer...")
        open_trace_viewer(trace_path)

    return exit_code if trace_saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
