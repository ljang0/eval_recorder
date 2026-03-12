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

When the command starts, it opens a small text-entry dialog so you can name the task. That task name is included in the output folder, for example `runs/run_0007_checkout-flow/`.

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
playwright show-trace runs/run_0001/trace.zip
```

## Build

Build a wheel for distribution:

```bash
python -m pip wheel --no-deps . -w dist
```
