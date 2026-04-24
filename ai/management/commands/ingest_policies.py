"""
Django management command: python manage.py ingest_policies

Loads policy.md into the RAG vector store (booking_policies collection).
Run once after initial setup.
"""

from django.core.management.base import BaseCommand
from ai.ingest_policies import ingest_policy_document, verify_policy_ingestion


class Command(BaseCommand):
    help = "Ingest policy.md into the RAG vector store for chatbot"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify ingestion by running test queries'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing policies before ingesting'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting policy ingestion..."))
        
        # Clear if requested
        if options.get('clear'):
            self.stdout.write(self.style.WARNING("Clearing existing policies..."))
            from ai.vector_store import get_vector_store
            get_vector_store().clear_collection("booking_policies")
            self.stdout.write(self.style.SUCCESS("✓ Policies cleared"))
        
        # Ingest
        success = ingest_policy_document()
        
        if success:
            self.stdout.write(self.style.SUCCESS("✓ Policy document ingested successfully!"))
            
            # Verify if requested
            if options.get('verify'):
                self.stdout.write(self.style.SUCCESS("\nVerifying ingestion..."))
                verify_policy_ingestion()
                self.stdout.write(self.style.SUCCESS("✓ Verification complete!"))
        else:
            self.stdout.write(self.style.ERROR("✗ Policy ingestion failed"))
