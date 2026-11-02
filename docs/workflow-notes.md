

## Local application workflow notes (Oqoqo evaluation revision)

These notes apply to qdrant-client 1.15.1 local mode. They add workflow guidance to the unchanged upstream README above.

- Use `QdrantClient(path=directory)` when data must survive a closed client and a new process. `":memory:"` is temporary. Close the client before another client opens the same directory.
- On startup, check whether a collection exists. Create it only when missing; recreating a collection removes its stored points.
- Similarity retrieval can use `query_points(...).points`. Pass a payload filter in `query_filter` to restrict candidate points before ranking. Filtering an already limited result list can omit valid matches.
- A complete export can use `scroll`. Its response is a pair: records and the next offset. Pass the returned offset into the next request and stop when it is `None`. A page-size limit is not a total-result limit. Keep the filter unchanged on every page.
- `set_payload` updates the supplied payload keys for selected existing points. It preserves their vectors and other payload keys; deleting and rebuilding a collection to change one field risks losing unrelated records.
- Local mode is useful for a deterministic SDK fixture. It does not establish server authentication, network, strict-mode indexing, or production scaling behavior.
