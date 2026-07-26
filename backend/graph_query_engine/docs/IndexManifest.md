# IndexManifest & IndexSnapshot Documentation

## Purpose
`IndexManifest` and `IndexSnapshot` provide immutable descriptors tracking index registration, version dependencies, semver bounds, and active snapshot provenance.

---

## Model Surface
- `IndexManifest`: Registered index types, index dependencies mapping, supported graph semver version, supported schema version.
- `IndexSnapshot`: Active index snapshot identifier, source `GraphIdentity` reference, list of active index names, creation timestamp.
