---
icon: lucide/rocket
description: "Install the library and build PMTiles and MapLibre Tiles (MLT) from Philippine administrative boundary GeoJSON, from Python or the command line."
---

# Get started

!!! Important

    This is primarily for processing administrative boundaries in the Philippines as a utility project for [Open Data Portal Extension](https://datax-docs.jmrecondo.com). However, it supports any other workflow provided you have the command installed and executable via the CLI.

## Prerequisites

- The commands your manifest's steps call, installed and accessible on your `PATH`. The default workflow uses `mapshaper`, `tippecanoe`, and `mlt`.

## Install

```bash
pip install geomake
```

## Usage

### Building with Python

```python
from geomake import build

artifacts = build("<dataset>")
```

That's it. It reads `manifest.yml` from the current folder, runs the dataset's steps, and returns the built artifacts (each has `.path` and `.sha256`). See the [manifest schema](schema.md) for how to declare datasets.

Everything else is optional:

```python
build("<dataset>", "path/to/manifest.yml", output_dir="tiles", keep_intermediates=True)
```

Errors are raised as `ManifestError`, `ToolError`, or `StepError`, and as `FileNotFoundError` when a source is missing.

### Building with the CLI

```bash
geomake build <dataset>
```

### Manifest location

By default, both read `manifest.yml` from the current folder. Pass `--manifest` (`-m`) to the CLI, or a path as `build()`'s second argument, to use another file.

### Output and caching

Finished tiles are written to `data/processed/` next to the manifest (override with `--output-dir`). Each step's output is cached, so rebuilding only reruns steps whose input, command, or tool version changed.

A dataset's `source` resolves under the manifest's `data/` directory and may be a single file or a glob (e.g. `raw/municities/*.json`), or a mapping of names to such paths. Glob matches are merged into one FeatureCollection (written to `.cache/build/raw/<dataset>/`), which is what steps read. That merged copy is deleted after each run unless you pass `--keep-intermediates`.

## Development

The repository ships a Dev Container with `mapshaper`, `tippecanoe`, and `mlt` already installed. Open it in your IDE, reopen in the container, and run `uv sync`.

<!-- ## Good defaults I found

| Command | Use case | Defaults |
| --- | --- | --- |
| `mapshaper` | | |
| `tippecanoe` | | |
| `mlt` | | | -->

## Credits

Depends on https://github.com/faeldon/philippines-psgc-shapefiles.

*[CLI]: Command Line Interface
