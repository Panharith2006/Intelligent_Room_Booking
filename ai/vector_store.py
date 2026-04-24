import os
import logging
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Production-ready vector database wrapper for ChromaDB.
    Handles knowledge base, room search, and booking policies.
    """

    def __init__(self, persist_directory: Optional[str] = None):

        self.persist_directory = persist_directory or os.getenv(
            "VECTOR_DB_PATH",
            "./vector_db"
        )

        os.makedirs(self.persist_directory, exist_ok=True)

        logger.info(f"Initializing ChromaDB at: {self.persist_directory}")

        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Collections
        self.knowledge_collection = self._get_or_create_collection("knowledge_base")
        self.rooms_collection = self._get_or_create_collection("rooms_info")
        self.policies_collection = self._get_or_create_collection("booking_policies")


        logger.info("Vector store initialized successfully")

    # =========================
    # COLLECTION HANDLING
    # =========================

    def _get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    # =========================
    # DOCUMENT INSERTION
    # =========================

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> bool:

        if not (len(documents) == len(metadatas) == len(ids)):
            raise ValueError("documents, metadatas, and ids must have same length")

        collection = self.client.get_collection(collection_name)

        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Inserted {len(documents)} documents into '{collection_name}'")
        return True

    # =========================
    # CORE SEARCH
    # =========================

    def search(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> Dict:

        collection = self.client.get_collection(collection_name)

        return collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

    # =========================
    # HIGH-LEVEL SEARCH HELPERS
    # =========================

    def search_rooms(self, query: str, n_results: int = 10) -> Dict:
        return self.search("rooms_info", query, n_results)

    def search_knowledge(self, query: str, n_results: int = 5) -> Dict:
        return self.search("knowledge_base", query, n_results)

    def search_policies(self, query: str, n_results: int = 3) -> Dict:
        return self.search("booking_policies", query, n_results)

    # =========================
    # STATS / MONITORING
    # =========================

    def get_collection_stats(self) -> Dict[str, int]:
        return {
            "knowledge_base": self.knowledge_collection.count(),
            "rooms_info": self.rooms_collection.count(),
            "booking_policies": self.policies_collection.count()
        }

    # =========================
    # MAINTENANCE
    # =========================

    def clear_collection(self, collection_name: str) -> bool:
        try:
            self.client.delete_collection(collection_name)
            self._get_or_create_collection(collection_name)
            logger.info(f"Cleared collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection '{collection_name}': {e}")
            return False

    def reset_all(self) -> bool:
        try:
            self.client.reset()

            self.knowledge_collection = self._get_or_create_collection("knowledge_base")
            self.rooms_collection = self._get_or_create_collection("rooms_info")
            self.policies_collection = self._get_or_create_collection("booking_policies")

            logger.warning("Vector store fully reset")
            return True

        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            return False


# =========================
# SAFE PRODUCTION SINGLETON
# =========================

from functools import lru_cache


@lru_cache()
def get_vector_store() -> VectorStore:
    """
    Thread-safe singleton (production safe alternative to global variable)
    """
    return VectorStore()