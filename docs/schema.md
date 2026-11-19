---
icon: lucide/file-json
---

The schema found in `manifest.yml` configures how the app processes your data.

```yaml
datasets:
  country:
    # Source reads inside `data/`
    source: raw/country.0.1.json

    geometry:
      # Pass mapshaper flags to override this block.
      #
      # https://mapshaper.org/docs/reference.html
      #
      # e.g., -clean -simplify visvalingam percentage=10% keep-shapes -o out.geojson precision=0.00001
      #
      # Useful if a configuration is not in this manifest.
      #
      # raw:

      clean: true
      precision: 0.00001
      simplify:
        method: visvalingam # or douglas-peucker
        percent: 10
        keep_shapes: true
    outputs:
      pmtiles: { layer: barangays, minzoom: 4, maxzoom: 14 }
        # raw:

      # mlt: { layer: barangays }
        # raw:
```