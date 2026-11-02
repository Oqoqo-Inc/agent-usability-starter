from qdrant_client import QdrantClient, models

class Catalog:
    def __init__(self, directory=None):
        self.client = QdrantClient(":memory:")
        self.collection = "catalog"
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE))

    def add(self, records):
        self.client.upsert(self.collection, points=[models.PointStruct(**r) for r in records], wait=True)

    def search(self, query, tenant, limit=3):
        raise NotImplementedError("Tenant-aware search is not implemented")

    def export(self, tenant, batch_size=2):
        raise NotImplementedError("Complete tenant export is not implemented")

    def patch(self, point_id, payload):
        raise NotImplementedError("Persistent payload update is not implemented")

    def close(self):
        self.client.close()
