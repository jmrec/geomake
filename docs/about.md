---
icon: lucide/lightbulb
description: "Why Geomake exists, and why a manifest and some Python instead of a Justfile."
---

# About

Geomake started with a practical job: turning the Philippines' administrative boundaries into vector tiles. That meant taking shapefiles, cleaning and simplifying them, and building tiles, for several datasets at several levels, from the country down to the barangay.

Each step is a command-line tool that reads a file and writes a file. Geomake runs those steps in order from a manifest, and skips any step whose input, command, or tool version hasn't changed.

## Why not just a Justfile?

I tried it myself first. For a simple workflow, a Justfile is the better choice: it's a few lines, there's nothing to install beyond `just`, and it's easy to read.

It doesn't scale with the number of datasets, though. As the workflow grows, you end up writing Justfile logic for each dataset: the same steps with different paths, flags, and intermediate files. Then the Justfile gets hard to read, and hard to change without breaking something else.

What a manifest and Python give you instead:

- **One description per dataset.** Each dataset lists its source and its steps. The tool handles the plumbing: passing one step's output to the next, naming files, and branching and merging.
- **Work that isn't repeated.** A step reruns only when its input, its command, or its tool's version changes. `just` is a command runner, so it doesn't track whether anything changed.
- **Mistakes caught before anything runs.** The manifest is validated up front. An unknown key, a step that never uses `{out}`, or a misspelled dataset name is reported immediately, rather than halfway through a long build.
- **Tests.** You can't test a Justfile. Geomake is Python, so the logic that decides what runs and what's cached is covered by unit tests and by integration tests that run the real tools.
- **Types, and everything else Python brings.** The manifest schema is typed and checked, and you get editor support, packaging, and a normal way to install and version it.
- **A library as well as a CLI.** `from geomake import build` lets other Python code run a build, not only a shell.

## When a Justfile is still the right tool

If your whole workflow is two or three commands that you run occasionally, use a Justfile. Geomake is for the point where you'd otherwise be copying and adjusting recipes for every dataset. The two also work together: a Justfile recipe can call `geomake build`.
