import argparse
import logging
from ai.ingest_documents import ingest_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest a file into the project's vector DB")
    parser.add_argument("--file", "-f", default="FAQ.md", help="File path relative to project root")
    parser.add_argument("--collection", "-c", default="knowledge_base", help="Target collection name")
    parser.add_argument("--verify", "-v", action="store_true", help="Print collection stats after ingestion")

    args = parser.parse_args()

    ok = ingest_document(
        file_path=args.file,
        collection_name=args.collection
    )

    if not ok:
        logger.error("Ingestion failed")
        raise SystemExit(1)

    logger.info("Ingestion completed successfully")

    if args.verify:
        try:
            from ai.vector_store import get_vector_store
            vs = get_vector_store()
            stats = vs.get_collection_stats()
            logger.info(f"Vector store stats: {stats}")
        except Exception as e:
            logger.error(f"Failed to fetch vector store stats: {e}")


if __name__ == '__main__':
    main()
