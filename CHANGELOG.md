## v0.1.0 (2026-11-26)

### Feat

- **api**: build several datasets at once
- **manifest**: resolve sources from the manifest's folder
- **api**: add one-call build entry point
- **docs**: enable zensical plugins
- **docs**: postprocess built site with mkdocs-ultralytics-plugin
- **logging**: emit structured logs with structlog
- **manifest**: combine all five boundary levels into one pmtiles
- **manifest**: add dataset manifest
- **cli**: add Typer tile build pipeline
- **url**: serve benguet-mlt pmtiles
- **config**: add benguet source

### Fix

- **release**: push the version tag explicitly

### Refactor

- **package**: rename to geomake
- **validation**: use pydantic
- **pipeline**: drive builds from ordered manifest steps
- **martin**: move Martin configs into martin/
- **compose**: allow extra args in command
