"""
Django management command: python manage.py ingest_documents

Generic document ingestion for RAG system.
Replaces separate commands like ingest_policies.

Usage:
    python manage.py ingest_documents --file FAQ.md --collection knowledge_base
    python manage.py ingest_documents --file policy.md --collection booking_policies --verify
    python manage.py ingest_documents --file Room_Guide.pdf --collection rooms_info --clear
"""

from django.core.management.base import BaseCommand, CommandError
from ai.ingest_documents import ingest_document, clear_collection
from ai.vector_store import get_vector_store


class Command(BaseCommand):
    help = "Ingest any document into RAG vector store (generic)"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to document file (relative to project root)'
        )
        parser.add_argument(
            '--collection',
            type=str,
            required=True,
            choices=['knowledge_base', 'rooms_info', 'booking_policies'],
            help='Target collection'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=800,
            help='Characters per chunk (default: 800)'
        )
        parser.add_argument(
            '--chunk-overlap',
            type=int,
            default=150,
            help='Overlap between chunks (default: 150)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear collection before ingesting'
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify ingestion by checking collection stats'
        )
    
    def handle(self, *args, **options):
        file_path = options['file']
        collection_name = options['collection']
        chunk_size = options['chunk_size']
        chunk_overlap = options['chunk_overlap']
        
        self.stdout.write(self.style.SUCCESS(f" Starting document ingestion..."))
        self.stdout.write(f"   File: {file_path}")
        self.stdout.write(f"   Collection: {collection_name}")
        self.stdout.write(f"   Chunk Size: {chunk_size}")
        
        # Clear if requested
        if options.get('clear'):
            self.stdout.write(self.style.WARNING(f"\n🗑️  Clearing '{collection_name}' collection..."))
            clear_collection(collection_name)
            self.stdout.write(self.style.SUCCESS("✓ Collection cleared"))
        
        # Ingest
        self.stdout.write(self.style.SUCCESS("\n Ingesting document..."))
        success = ingest_document(
            file_path=file_path,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS("\n Document ingested successfully!"))
            
            # Verify if requested
            if options.get('verify'):
                self.stdout.write(self.style.SUCCESS("\n Collection stats:"))
                vector_store = get_vector_store()
                stats = vector_store.get_collection_stats()
                for collection, count in stats.items():
                    status = "✓" if count > 0 else "○"
                    self.stdout.write(f"   {status} {collection}: {count} chunks")
        else:
            raise CommandError("✗ Document ingestion failed")
