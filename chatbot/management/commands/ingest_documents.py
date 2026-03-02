"""
Django management command to ingest documents into vector database.

Usage:
    python manage.py ingest_documents --file path/to/file.pdf
    python manage.py ingest_documents --dir path/to/docs --collection knowledge_base
    python manage.py ingest_documents --reset  # Clear all collections
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ingest documents (PDF, MD, HTML, TXT) into vector database for RAG'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to a single file to ingest'
        )
        
        parser.add_argument(
            '--dir',
            type=str,
            help='Path to directory containing documents to ingest'
        )
        
        parser.add_argument(
            '--collection',
            type=str,
            default='knowledge_base',
            choices=['knowledge_base', 'rooms_info', 'booking_policies'],
            help='Target collection (default: knowledge_base)'
        )
        
        parser.add_argument(
            '--extensions',
            type=str,
            nargs='+',
            default=['.pdf', '.md', '.html', '.htm', '.txt'],
            help='File extensions to include (default: .pdf .md .html .htm .txt)'
        )
        
        parser.add_argument(
            '--recursive',
            action='store_true',
            default=True,
            help='Search subdirectories recursively (default: True)'
        )
        
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear all collections before ingesting'
        )
        
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show vector database statistics'
        )
        
        parser.add_argument(
            '--ingest-defaults',
            action='store_true',
            help='Ingest default project documentation'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        
        try:
            from ai.vector_store import get_vector_store
            from ai.document_ingestion import DocumentIngestionPipeline
            
            vector_store = get_vector_store()
            pipeline = DocumentIngestionPipeline(vector_store)
            
            self.stdout.write(self.style.SUCCESS('Vector store initialized ✓'))
            
            # Show stats
            if options['stats']:
                self._show_stats(vector_store)
                return
            
            # Reset collections
            if options['reset']:
                self._reset_collections(vector_store)
                return
            
            # Ingest default documentation
            if options['ingest_defaults']:
                self._ingest_defaults(pipeline)
                return
            
            # Ingest single file
            if options['file']:
                self._ingest_file(pipeline, options)
                return
            
            # Ingest directory
            if options['dir']:
                self._ingest_directory(pipeline, options)
                return
            
            # No action specified
            self.stdout.write(
                self.style.WARNING(
                    'No action specified. Use --help to see available options.'
                )
            )
            self._show_stats(vector_store)
            
        except ImportError as e:
            raise CommandError(f'Missing dependencies: {e}. Run: pip install -r requirements.txt')
        except Exception as e:
            raise CommandError(f'Error: {e}')
    
    def _ingest_file(self, pipeline, options):
        """Ingest a single file."""
        file_path = options['file']
        collection = options['collection']
        
        if not os.path.exists(file_path):
            raise CommandError(f'File not found: {file_path}')
        
        self.stdout.write(f'Ingesting file: {file_path}')
        self.stdout.write(f'Target collection: {collection}')
        
        chunks_added = pipeline.ingest_file(file_path, collection)
        
        if chunks_added > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully ingested {chunks_added} chunks')
            )
        else:
            self.stdout.write(self.style.ERROR('Failed to ingest file'))
    
    def _ingest_directory(self, pipeline, options):
        """Ingest all files from a directory."""
        directory = options['dir']
        collection = options['collection']
        extensions = options['extensions']
        recursive = options['recursive']
        
        if not os.path.exists(directory):
            raise CommandError(f'Directory not found: {directory}')
        
        self.stdout.write(f'Ingesting directory: {directory}')
        self.stdout.write(f'Target collection: {collection}')
        self.stdout.write(f'Extensions: {", ".join(extensions)}')
        self.stdout.write(f'Recursive: {recursive}')
        
        chunks_added = pipeline.ingest_directory(
            directory=directory,
            collection_name=collection,
            extensions=extensions,
            recursive=recursive
        )
        
        if chunks_added > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully ingested {chunks_added} chunks')
            )
        else:
            self.stdout.write(self.style.WARNING('No documents were ingested'))
    
    def _reset_collections(self, vector_store):
        """Reset all collections."""
        self.stdout.write(
            self.style.WARNING('⚠ This will delete all vector data. Are you sure? (yes/no)')
        )
        confirmation = input().strip().lower()
        
        if confirmation == 'yes':
            vector_store.reset_all()
            self.stdout.write(self.style.SUCCESS('✓ All collections cleared'))
        else:
            self.stdout.write('Operation cancelled')
    
    def _show_stats(self, vector_store):
        """Show vector database statistics."""
        stats = vector_store.get_collection_stats()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Vector Database Statistics'))
        self.stdout.write('='*50)
        
        for collection, count in stats.items():
            self.stdout.write(f'  {collection}: {count} documents')
        
        total = sum(stats.values())
        self.stdout.write('='*50)
        self.stdout.write(f'  Total: {total} documents')
        self.stdout.write('='*50 + '\n')
    
    def _ingest_defaults(self, pipeline):
        """Ingest default project documentation."""
        base_dir = settings.BASE_DIR
        
        self.stdout.write(self.style.SUCCESS('Ingesting default documentation...'))
        
        # Define documents to ingest
        documents_to_ingest = [
            {
                'file': os.path.join(base_dir, 'SYSTEM_KNOWLEDGE_BASE.md'),
                'collection': 'knowledge_base',
                'description': 'System knowledge base'
            },
            {
                'file': os.path.join(base_dir, 'RAG_ARCHITECTURE_GUIDE.md'),
                'collection': 'knowledge_base',
                'description': 'RAG architecture guide'
            },
            {
                'file': os.path.join(base_dir, 'RAG_ARCHITECTURE_SUMMARY.md'),
                'collection': 'knowledge_base',
                'description': 'RAG architecture summary'
            },
            {
                'file': os.path.join(base_dir, 'TELEGRAM_SETUP_GUIDE.md'),
                'collection': 'knowledge_base',
                'description': 'Telegram setup guide'
            }
        ]
        
        total_chunks = 0
        
        for doc in documents_to_ingest:
            if os.path.exists(doc['file']):
                self.stdout.write(f"  → {doc['description']}")
                chunks = pipeline.ingest_file(
                    file_path=doc['file'],
                    collection_name=doc['collection']
                )
                total_chunks += chunks
                self.stdout.write(f"    ✓ {chunks} chunks")
            else:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Not found: {doc['file']}")
                )
        
        # Ingest room data (create markdown from database)
        self.stdout.write("\n  → Generating room information document...")
        room_chunks = self._ingest_room_data(pipeline)
        total_chunks += room_chunks
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully ingested {total_chunks} total chunks')
        )
        
        # Show stats
        self._show_stats(pipeline.vector_store)
    
    def _ingest_room_data(self, pipeline):
        """Generate and ingest room data from database."""
        try:
            from booking.models import Room
            
            rooms = Room.objects.filter(is_available=True)
            
            # Generate markdown document
            room_doc = "# Room Inventory\n\n"
            room_doc += f"Total Available Rooms: {rooms.count()}\n\n"
            
            for room in rooms:
                room_doc += f"## {room.name} ({room.room_number})\n\n"
                room_doc += f"- **Capacity**: {room.capacity} people\n"
                room_doc += f"- **Type**: {room.room_type}\n"
                
                if room.equipment:
                    room_doc += f"- **Equipment**: {room.equipment}\n"
                
                if room.description:
                    room_doc += f"- **Description**: {room.description}\n"
                
                room_doc += "\n---\n\n"
            
            # Save temporarily and ingest
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                f.write(room_doc)
                temp_path = f.name
            
            chunks = pipeline.ingest_file(
                file_path=temp_path,
                collection_name='rooms_info',
                metadata={'type': 'room_inventory', 'auto_generated': True}
            )
            
            # Clean up
            os.unlink(temp_path)
            
            self.stdout.write(f"    ✓ {chunks} chunks (room inventory)")
            return chunks
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Failed to ingest room data: {e}")
            )
            return 0
