from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings
from uuid import UUID
from typing import List

COLLECTION_NAME = "incident_logs"

from fastapi import Depends

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)

def get_qdrant_service(client: QdrantClient = Depends(get_qdrant_client)) -> "QdrantService":
    return QdrantService(client)


class QdrantService:
    def __init__(self, client: QdrantClient):
        self.client = client
        self.vector_size = 1536 if settings.LLM_PROVIDER == "openai" else 768
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == COLLECTION_NAME for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
        except Exception as e:
            print(f"Failed to initialize Qdrant collection: {e}")

    def upsert_incident(self, incident_id: UUID, embedding: List[float], root_cause: str, status: str, tags: List[str] = None):
        if tags is None:
            tags = []
        point = PointStruct(
            id=str(incident_id),
            vector=embedding,
            payload={
                "incident_id": str(incident_id),
                "root_cause": root_cause,
                "status": status,
                "tags": tags
            }
        )
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )

    def search_similar_incidents(self, embedding: List[float], limit: int = 5) -> List[dict]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="status",
                    match=MatchValue(value="resolved")
                )
            ]
        )
        try:
            results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=embedding,
                query_filter=query_filter,
                limit=limit
            )
            return [hit.payload for hit in results]
        except Exception as e:
            print(f"Qdrant search failed: {e}")
            return []
