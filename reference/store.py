from qdrant_client import QdrantClient, models

class Catalog:
    def __init__(self, directory=None):
        self.client = QdrantClient(path=directory) if directory is not None else QdrantClient(":memory:")
        self.collection = "catalog"
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE))

    def add(self, records):
        self.client.upsert(self.collection, points=[models.PointStruct(**r) for r in records], wait=True)

    def search(self, query, tenant, limit=3):
        return [p.id for p in self.client.query_points(self.collection, query=query, query_filter=models.Filter(must=[models.FieldCondition(key="tenant", match=models.MatchValue(value=tenant))]), limit=limit).points]

    def export(self, tenant, batch_size=2):
        result, offset = [], None
        while True:
            points, offset = self.client.scroll(self.collection, scroll_filter=models.Filter(must=[models.FieldCondition(key="tenant", match=models.MatchValue(value=tenant))]), limit=batch_size, offset=offset)
            result.extend(p.id for p in points)
            if offset is None:
                return result

    def patch(self, point_id, payload):
        self.client.set_payload(self.collection, payload=payload, points=[point_id], wait=True)

    def close(self):
        self.client.close()
