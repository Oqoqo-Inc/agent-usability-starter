# Catalog storage adapter

This starter uses qdrant-client 1.15.1 and supplied three-dimensional vectors. No embedding model, network service, account, or credential is needed. The app's `Catalog` class in `store.py` is its integration boundary.

Records contain integer `id`, `vector`, and `payload` with `tenant` and `label` fields. `search(query, tenant, limit)` returns point IDs ordered by similarity within the tenant. `export(tenant, batch_size)` returns all of that tenant's point IDs. `patch(point_id, payload)` updates payload fields while preserving the existing point and other records. A catalog opened with a directory must reuse saved data after closing and reopening.

`python checks.py smoke` confirms the environment. `python checks.py search`, `python checks.py export`, and `python checks.py persistence` exercise each workflow. The checks use fresh temporary directories and generated records. Keep this fixture and its tests intact when fixing the adapter; leave the implementation and a short summary of observed checks.
