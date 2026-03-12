# eval_recorder

CLI for recording human browser trajectories as Playwright traces.

## Install

```bash
pip install .
python -m playwright install
```

If you prefer `pipx`:

```bash
pipx install .
pipx run --spec playwright playwright install
```

## Usage

Use the default start URL:

```bash
human-browser-recorder
```

When the command starts, it asks for the task name in the terminal before the browser launches. The default start page is now `about:blank`, which avoids immediately hitting Google or another site that may challenge automated browsers. The task name is included in the output folder, for example `runs/run_0008_checkout-flow/`.

Start from a specific page:

```bash
human-browser-recorder https://google.com
```

Skip the prompt and set the task name directly:

```bash
human-browser-recorder --task-name "checkout flow" https://google.com
```

Set the viewport and open the trace viewer automatically afterward:

```bash
human-browser-recorder \
  --task-name "search results review" \
  --start-url https://example.com \
  --viewport 1440x960 \
  --show-trace
```

If you explicitly want Google, pass it yourself:

```bash
human-browser-recorder --task-name "gmail lookup" https://www.google.com
```

## Stop Recording

Press `Esc` anywhere to stop recording and save the trace.

If global `Esc` capture is not available on the machine, the recorder falls back to `ENTER` in the terminal. On macOS, the first run may require Input Monitoring or Accessibility permission for the terminal or Python process.

## Output

Each run creates:

```text
runs/
  run_0001_example-task/
    trace.zip
    metadata.json
```

Open a saved trace manually:

```bash
playwright show-trace runs/run_0001_example-task/trace.zip
```

## Local Runs Viewer

Use the built-in local dashboard to browse runs, inspect metadata, and launch traces:

```bash
human-browser-viewer
```

That opens a local page with:

- `Open CLI Viewer` to launch `playwright show-trace`
- `Open Web Viewer` to try Playwright's browser-based viewer against the local trace file
- `Download Trace` to save the raw `trace.zip`

## Build

Build a wheel for distribution:

```bash
python -m pip wheel --no-deps . -w dist
```
