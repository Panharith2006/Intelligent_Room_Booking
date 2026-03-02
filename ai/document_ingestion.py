"""
Document Ingestion Pipeline for RAG System
Supports: PDF, Markdown (.md), HTML, TXT files
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
import re

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Multi-format document loader with chunking support.
    
    Supported formats:
    - PDF files (.pdf)
    - Markdown files (.md)
    - HTML files (.html, .htm)
    - Text files (.txt)
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize document loader.
        
        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(f"DocumentLoader initialized (chunk_size={chunk_size}, overlap={chunk_overlap})")
    
    def load_pdf(self, file_path: str) -> Optional[str]:
        """
        Load and extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text or None if failed
        """
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_parts = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"✓ Loaded PDF: {file_path} ({len(pdf_reader.pages)} pages, {len(full_text)} chars)")
                return full_text
                
        except ImportError:
            logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
            return None
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            return None
    
    def load_markdown(self, file_path: str) -> Optional[str]:
        """
        Load Markdown file.
        
        Args:
            file_path: Path to .md file
            
        Returns:
            File content or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                logger.info(f"✓ Loaded Markdown: {file_path} ({len(content)} chars)")
                return content
        except Exception as e:
            logger.error(f"Failed to load Markdown {file_path}: {e}")
            return None
    
    def load_html(self, file_path: str) -> Optional[str]:
        """
        Load and parse HTML file, extracting text content.
        
        Args:
            file_path: Path to .html file
            
        Returns:
            Extracted text or None if failed
        """
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            text = '\n'.join(line for line in lines if line)
            
            logger.info(f"✓ Loaded HTML: {file_path} ({len(text)} chars)")
            return text
            
        except ImportError:
            logger.error("beautifulsoup4 not installed. Run: pip install beautifulsoup4")
            return None
        except Exception as e:
            logger.error(f"Failed to load HTML {file_path}: {e}")
            return None
    
    def load_text(self, file_path: str) -> Optional[str]:
        """
        Load plain text file.
        
        Args:
            file_path: Path to .txt file
            
        Returns:
            File content or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                logger.info(f"✓ Loaded text: {file_path} ({len(content)} chars)")
                return content
        except Exception as e:
            logger.error(f"Failed to load text {file_path}: {e}")
            return None
    
    def load_file(self, file_path: str) -> Optional[str]:
        """
        Auto-detect file type and load content.
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted text or None if failed
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return self.load_pdf(file_path)
        elif ext == '.md':
            return self.load_markdown(file_path)
        elif ext in ['.html', '.htm']:
            return self.load_html(file_path)
        elif ext == '.txt':
            return self.load_text(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return None
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text into overlapping chunks for better context retrieval.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of dicts with 'text' and 'metadata' keys
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # Try to end at a sentence boundary
            if end < text_length:
                # Look for period, question mark, or exclamation within last 100 chars
                chunk_text = text[start:end]
                last_sentence = max(
                    chunk_text.rfind('. '),
                    chunk_text.rfind('? '),
                    chunk_text.rfind('! '),
                    chunk_text.rfind('\n\n')
                )
                
                if last_sentence > self.chunk_size - 200:  # Only if reasonably close to end
                    end = start + last_sentence + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata['chunk_index'] = len(chunks)
                chunk_metadata['start_char'] = start
                chunk_metadata['end_char'] = end
                
                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= end:
                start = end
        
        logger.info(f"✓ Created {len(chunks)} chunks from text ({text_length} chars)")
        return chunks
    
    def load_and_chunk_file(self, file_path: str, metadata: Dict = None) -> List[Dict]:
        """
        Load file and split into chunks.
        
        Args:
            file_path: Path to file
            metadata: Optional metadata for the file
            
        Returns:
            List of chunks with text and metadata
        """
        text = self.load_file(file_path)
        if text is None:
            return []
        
        # Prepare metadata
        file_metadata = {
            'source_file': os.path.basename(file_path),
            'file_path': file_path,
            'file_type': Path(file_path).suffix.lower(),
            'ingestion_date': datetime.now().isoformat(),
            'file_hash': self._hash_file(file_path)
        }
        
        if metadata:
            file_metadata.update(metadata)
        
        return self.chunk_text(text, file_metadata)
    
    def load_directory(
        self,
        directory: str,
        extensions: List[str] = None,
        recursive: bool = True
    ) -> List[Dict]:
        """
        Load all supported documents from a directory.
        
        Args:
            directory: Path to directory
            extensions: List of extensions to include (e.g., ['.pdf', '.md'])
            recursive: Whether to search subdirectories
            
        Returns:
            List of all chunks from all files
        """
        if extensions is None:
            extensions = ['.pdf', '.md', '.html', '.htm', '.txt']
        
        all_chunks = []
        directory_path = Path(directory)
        
        pattern = '**/*' if recursive else '*'
        
        for ext in extensions:
            for file_path in directory_path.glob(f"{pattern}{ext}"):
                if file_path.is_file():
                    logger.info(f"Processing: {file_path}")
                    chunks = self.load_and_chunk_file(str(file_path))
                    all_chunks.extend(chunks)
        
        logger.info(f"✓ Loaded {len(all_chunks)} total chunks from {directory}")
        return all_chunks
    
    def _hash_file(self, file_path: str) -> str:
        """Generate MD5 hash of file for change detection."""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception:
            return ""


class DocumentIngestionPipeline:
    """
    Complete ingestion pipeline: Load → Chunk → Embed → Store
    """
    
    def __init__(self, vector_store, document_loader: DocumentLoader = None):
        """
        Initialize ingestion pipeline.
        
        Args:
            vector_store: VectorStore instance
            document_loader: Optional custom DocumentLoader
        """
        self.vector_store = vector_store
        self.loader = document_loader or DocumentLoader()
        logger.info("DocumentIngestionPipeline initialized")
    
    def ingest_file(
        self,
        file_path: str,
        collection_name: str = "knowledge_base",
        metadata: Dict = None
    ) -> int:
        """
        Ingest a single file into vector store.
        
        Args:
            file_path: Path to file
            collection_name: Target collection
            metadata: Optional additional metadata
            
        Returns:
            Number of chunks added
        """
        logger.info(f"Ingesting file: {file_path} → {collection_name}")
        
        # Load and chunk
        chunks = self.loader.load_and_chunk_file(file_path, metadata)
        
        if not chunks:
            logger.warning(f"No chunks generated from {file_path}")
            return 0
        
        # Prepare for vector store
        documents = [chunk['text'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        ids = [
            f"{Path(file_path).stem}_{chunk['metadata']['chunk_index']}_{chunk['metadata']['file_hash'][:8]}"
            for chunk in chunks
        ]
        
        # Add to vector store
        success = self.vector_store.add_documents(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        if success:
            logger.info(f"✓ Successfully ingested {len(chunks)} chunks from {file_path}")
            return len(chunks)
        else:
            logger.error(f"Failed to ingest {file_path}")
            return 0
    
    def ingest_directory(
        self,
        directory: str,
        collection_name: str = "knowledge_base",
        extensions: List[str] = None,
        recursive: bool = True
    ) -> int:
        """
        Ingest all files from a directory.
        
        Args:
            directory: Path to directory
            collection_name: Target collection
            extensions: File extensions to include
            recursive: Search subdirectories
            
        Returns:
            Total number of chunks added
        """
        logger.info(f"Ingesting directory: {directory} → {collection_name}")
        
        # Load all chunks
        all_chunks = self.loader.load_directory(directory, extensions, recursive)
        
        if not all_chunks:
            logger.warning(f"No documents found in {directory}")
            return 0
        
        # Prepare for vector store
        documents = [chunk['text'] for chunk in all_chunks]
        metadatas = [chunk['metadata'] for chunk in all_chunks]
        ids = [
            f"{chunk['metadata']['source_file']}_{chunk['metadata']['chunk_index']}_{chunk['metadata']['file_hash'][:8]}"
            for chunk in all_chunks
        ]
        
        # Add to vector store in batches (avoid memory issues)
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            success = self.vector_store.add_documents(
                collection_name=collection_name,
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
            
            if success:
                total_added += len(batch_docs)
        
        logger.info(f"✓ Successfully ingested {total_added} chunks from {directory}")
        return total_added
