---
icon: lucide/rocket
description: "Install the library and build PMTiles and MapLibre Tiles (MLT) from Philippine administrative boundary GeoJSON, from Python or the command line."
---

# Get started

<!-- !!! Important

    This is primarily for processing administrative boundaries in the Philippines as a utility project for [Open Data Portal Extension](https://datax-docs.jmrecondo.com). However, it supports any other workflow provided you have the command installed and executable via the CLI. -->

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

To build several datasets at once, name them all:

```python
artifacts = build("<dataset>", "<another-dataset>")
```

Everything else is optional and passed by keyword:

```python
build("<dataset>", manifest="geomake.yml", output_dir="tiles", keep_intermediates=True)
```

#### Using the result

`build()` writes the finished files to disk, so you don't have to do anything with what it returns. The result is there to tell you where the files went. It's a list with one artifact per dataset, in the order you named them, and each artifact is the dataset's final output file:

- `.path` is a `pathlib.Path` to the file, for example `data/processed/country.pmtiles`.
- `.sha256` is the file's checksum.

Use it when other code needs to act on the output:

```python
from geomake import build

[tiles] = build("<dataset>")

print(tiles.path)    # where the file was written
print(tiles.sha256)  # checksum of that file
```

With several datasets, loop over the list:

```python
for artifact in build("<dataset>", "<another-dataset>"):
    print(artifact.path, artifact.sha256)
```

Typical uses are uploading or copying the file elsewhere, recording its checksum, or checking later that it hasn't changed. The list holds only final files, not the intermediate files from earlier steps. If you don't need any of this, call `build("<dataset>")` on its own line and ignore the result.

Every name is checked before anything runs, so a misspelled dataset stops the build before it starts. If a build fails partway, the datasets already finished stay cached and are skipped on the next run.

Errors are raised as `ManifestError`, `ToolError`, or `StepError`, and as `FileNotFoundError` when a source is missing.

### Building with the CLI

```bash
geomake build <dataset>
geomake build <dataset> <another-dataset>
```

### Manifest location

By default, both read `manifest.yml` from the current folder. The file can have any name, such as `geomake.yml` if `manifest.yml` is already taken. Pass it with `--manifest` (`-m`) on the CLI, or `manifest=` to `build()`:

```bash
geomake build <dataset> --manifest geomake.yml
```

### Output and caching

Finished files are written to `data/processed/` next to the manifest by default. Choose another folder with `--output-dir` (`-o`) on the CLI, or `output_dir=` to `build()`. Each step's output is cached, so rebuilding only reruns steps whose input, command, or tool version changed.

A dataset's `source` can be anywhere. A relative path starts at the manifest's folder (for example `data/raw/municities/*.json`), and an absolute path is used as written. It may be a single file or a glob, or a mapping of names to such paths. Glob matches are merged into one FeatureCollection (written to `.cache/build/raw/<dataset>/`), which is what steps read. That merged copy is deleted after each run unless you pass `--keep-intermediates`.

## Development

The repository ships a Dev Container with `mapshaper`, `tippecanoe`, and `mlt` already installed. Open it in your IDE, reopen in the container, and run `uv sync`.

<!-- ## Good defaults I found

| Command | Use case | Defaults |
| --- | --- | --- |
| `mapshaper` | | |
| `tippecanoe` | | |
| `mlt` | | | -->

<!-- ## Credits

Depends on https://github.com/faeldon/philippines-psgc-shapefiles. -->

*[CLI]: Command Line Interface
