---
icon: lucide/rocket
---

# Get started

!!! Important

    This is primarily for processing administrative boundaries in the Philippines as a utility project for [Open Data Portal Extension](https://datax-docs.jmrecondo.com), particularly manipulation and conversion of GeoJSON into PMTiles and MapLibre Tiles (MLT).

    The Dev Container makes the `mapshaper`, `tippecanoe`, and `mlt` commands available in the CLI.

## Setup

=== "Dev Container (Recommended)"

    **Prerequisites**

    - Docker

    **Steps**

    1. Open in the IDE of your choice and reopen in container. 

=== "Manual"

    **Prerequisites**

    - `git`
    - Commands installed in your PC: `mapshaper`, `tippecanoe`, `mlt`
    - `uv`

    **Steps**

    1. Clone the repository:

        ```bash
        git clone https://github.com/jmrec/ph-administrative-boundaries.git
        ```

    2. Open in the IDE of your choice.
    3. Run

        ```bash
        uv sync
        ```

## Usage

### Building with the CLI

[manifest.yml](/schema) declares each dataset's source, geometry pipeline, and outputs:

```bash
uv run cli build <dataset>
```

Finished tiles are written to `data/processed/` (override with `--output-dir`). Intermediates are dropped after each run unless you pass `--keep-intermediates`.

A dataset's `source` resolves under the manifest's `data/` directory and may be a single file or a glob (e.g. `raw/municities/*.json`). Glob matches are merged into one FeatureCollection (written to `.cache/build/raw/`) before normalization.

<!-- ## Good defaults I found

| Command | Use case | Defaults |
| --- | --- | --- |
| `mapshaper` | | |
| `tippecanoe` | | |
| `mlt` | | | -->

## Credits

Depends on https://github.com/faeldon/philippines-psgc-shapefiles.

*[CLI]: Command Line Interface