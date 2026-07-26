# APIRouteIndex Documentation

## Purpose
`APIRouteIndex` maps HTTP API endpoints (`METHOD:PATH`, e.g. `GET:/users`) to `APIRouteRecord` instances encapsulating handler functions, controllers, and framework route metadata.

---

## API Surface
- `contains(http_method: str, route_path: str) -> bool`
- `get(http_method: str, route_path: str) -> APIRouteRecord`
- `try_get(http_method: str, route_path: str) -> Optional[APIRouteRecord]`
- `routes() -> tuple[APIRouteRecord, ...]`
- `count() -> int`
