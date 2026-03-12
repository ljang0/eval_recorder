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

Start from a specific page:

```bash
human-browser-recorder https://google.com
```

Set the viewport and open the trace viewer automatically afterward:

```bash
human-browser-recorder \
  --start-url https://example.com \
  --viewport 1440x960 \
  --show-trace
```

## Output

Each run creates:

```text
runs/
  run_0001/
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
