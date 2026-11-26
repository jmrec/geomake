# Geomake

Build geospatial datasets from a manifest of cached, ordered CLI steps.

You declare each dataset's source and the commands that process it. Geomake runs them in order, passes each step's output to the next, and skips any step whose inputs, command, or tool version haven't changed. It works with any command-line tool that reads an input file and writes an output file, such as `mapshaper`, `tippecanoe`, and `mlt`.

## Install

```bash
pip install geomake
```

The commands your manifest calls must be installed and on your `PATH`.

## Usage

Describe your datasets in a `manifest.yml`:

```yaml
datasets:
  country:
    source: data/raw/country.json
    steps:
      - run: mapshaper -i {in} -clean -o {out}
      - run: tippecanoe -o {out} -f -P --layer=country -Z4 -z14 {in}
        out: country.pmtiles
```

Then build a dataset from Python:

```python
from geomake import build

artifacts = build("country")
```

Name several datasets to build them in one go: `build("country", "regions")`.

or from the command line:

```bash
geomake build country
geomake build country regions
```

By default Geomake reads `manifest.yml` from the current folder and writes finished files to `data/processed/` next to it. Sources and outputs can live anywhere: relative source paths start at the manifest's folder, and absolute paths work too.

To use a differently named manifest or another output folder:

```bash
geomake build country --manifest geomake.yml --output-dir tiles
```

## Documentation

Full documentation, including the manifest schema, is at <https://docs.jmrecondo.com/geomake/>.

## License

MIT
