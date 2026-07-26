# ImportIndex Documentation

## Purpose
`ImportIndex` tracks file-to-file and module import dependencies across repository files and packages.

---

## API Surface
- `imports_by_file(file_id: FileId | str) -> tuple[ImmutableNodeView, ...]`
- `files_importing_package(package_id: PackageId | str) -> tuple[FileId, ...]`
