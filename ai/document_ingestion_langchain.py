"""
Professional Document Ingestion with LangChain
Semantic-aware text splitting for better RAG performance
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class LangChainDocumentLoader:
    """
    Professional document loader using LangChain's text splitters.
    
    Advantages over basic chunking:
    - Respects document structure (headers, paragraphs, sentences)
    - Semantic-aware splitting
    - Better context preservation
    - Multiple splitting strategies
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        splitter_type: str = "recursive"
    ):
        """
        Initialize with LangChain text splitters.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            splitter_type: Type of splitter ('recursive', 'token', 'semantic')
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter_type = splitter_type
        
        # Initialize appropriate splitter
        self._init_splitter()
        
        logger.info(f"LangChain Document Loader initialized (type={splitter_type}, "
                   f"chunk_size={chunk_size}, overlap={chunk_overlap})")
    
    def _init_splitter(self):
        """Initialize LangChain text splitter based on type."""
        try:
            from langchain.text_splitter import (
                RecursiveCharacterTextSplitter,
                TokenTextSplitter,
                CharacterTextSplitter
            )
            
            if self.splitter_type == "recursive":
                # Best for general text - respects structure
                self.splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    length_function=len,
                    separators=[
                        "\n\n",  # Paragraphs
                        "\n",    # Lines
                        ". ",    # Sentences
                        ", ",    # Clauses
                        " ",     # Words
                        ""       # Characters
                    ]
                )
            
            elif self.splitter_type == "token":
                # Token-based splitting (for LLM context windows)
                self.splitter = TokenTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
            
            else:  # character
                # Simple character-based (fallback)
                self.splitter = CharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separator="\n\n"
                )
            
            logger.info(f"✓ LangChain {self.splitter_type} splitter initialized")
            
        except ImportError:
            logger.warning("LangChain not installed. Install with: pip install langchain")
            logger.warning("Falling back to basic chunking")
            self.splitter = None
    
    def load_pdf(self, file_path: str) -> Optional[str]:
        """Load PDF using PyPDF2."""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_parts = []
                
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"✓ Loaded PDF: {file_path} ({len(pdf_reader.pages)} pages)")
                return full_text
                
        except ImportError:
            logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
            return None
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            return None
    
    def load_markdown(self, file_path: str) -> Optional[str]:
        """Load Markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                logger.info(f"✓ Loaded Markdown: {file_path}")
                return content
        except Exception as e:
            logger.error(f"Failed to load Markdown {file_path}: {e}")
            return None
    
    def load_html(self, file_path: str) -> Optional[str]:
        """Load HTML using BeautifulSoup."""
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
            
            logger.info(f"✓ Loaded HTML: {file_path}")
            return text
            
        except ImportError:
            logger.error("beautifulsoup4 not installed. Install with: pip install beautifulsoup4")
            return None
        except Exception as e:
            logger.error(f"Failed to load HTML {file_path}: {e}")
            return None
    
    def load_text(self, file_path: str) -> Optional[str]:
        """Load plain text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                logger.info(f"✓ Loaded text: {file_path}")
                return content
        except Exception as e:
            logger.error(f"Failed to load text {file_path}: {e}")
            return None
    
    def load_file(self, file_path: str) -> Optional[str]:
        """Auto-detect and load file."""
        ext = Path(file_path).suffix.lower()
        
        loaders = {
            '.pdf': self.load_pdf,
            '.md': self.load_markdown,
            '.html': self.load_html,
            '.htm': self.load_html,
            '.txt': self.load_text
        }
        
        loader = loaders.get(ext)
        if loader:
            return loader(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return None
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text using LangChain splitter with semantic awareness.
        
        Args:
            text: Input text
            metadata: Metadata to attach to chunks
            
        Returns:
            List of chunk dictionaries
        """
        if not text:
            return []
        
        # Use LangChain splitter if available
        if self.splitter:
            try:
                # LangChain splitting
                text_chunks = self.splitter.split_text(text)
                
                # Convert to our format with metadata
                chunks = []
                for i, chunk_text in enumerate(text_chunks):
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata['chunk_index'] = i
                    chunk_metadata['total_chunks'] = len(text_chunks)
                    chunk_metadata['chunk_method'] = self.splitter_type
                    
                    chunks.append({
                        'text': chunk_text,
                        'metadata': chunk_metadata
                    })
                
                logger.info(f"✓ Created {len(chunks)} semantic chunks using LangChain")
                return chunks
                
            except Exception as e:
                logger.error(f"LangChain chunking failed: {e}, falling back to basic")
        
        # Fallback: basic chunking
        return self._basic_chunk(text, metadata)
    
    def _basic_chunk(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Fallback basic chunking if LangChain not available."""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # Try to end at sentence boundary
            if end < text_length:
                chunk_text = text[start:end]
                last_sentence = max(
                    chunk_text.rfind('. '),
                    chunk_text.rfind('? '),
                    chunk_text.rfind('! '),
                    chunk_text.rfind('\n\n')
                )
                
                if last_sentence > self.chunk_size - 200:
                    end = start + last_sentence + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata['chunk_index'] = len(chunks)
                chunk_metadata['chunk_method'] = 'basic'
                
                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
            
            start = end - self.chunk_overlap
            if start >= end:
                start = end
        
        logger.info(f"✓ Created {len(chunks)} basic chunks")
        return chunks
    
    def load_and_chunk_file(
        self,
        file_path: str,
        metadata: Dict = None
    ) -> List[Dict]:
        """
        Load file and split into semantic chunks.
        
        Args:
            file_path: Path to file
            metadata: Optional metadata
            
        Returns:
            List of chunks with text and metadata
        """
        # Load content
        text = self.load_file(file_path)
        if text is None:
            return []
        
        # Prepare metadata
        file_metadata = {
            'source_file': os.path.basename(file_path),
            'file_path': file_path,
            'file_type': Path(file_path).suffix.lower(),
            'file_hash': hashlib.md5(text.encode()).hexdigest(),
            'ingestion_date': datetime.now().isoformat(),
            'text_length': len(text)
        }
        
        # Merge with provided metadata
        if metadata:
            file_metadata.update(metadata)
        
        # Chunk the text
        chunks = self.chunk_text(text, file_metadata)
        
        logger.info(f"✓ File chunked: {file_path} → {len(chunks)} chunks")
        
        return chunks
    
    def load_directory(
        self,
        directory: str,
        pattern: str = "**/*",
        metadata: Dict = None
    ) -> List[Dict]:
        """
        Load and chunk all files in a directory.
        
        Args:
            directory: Directory path
            pattern: Glob pattern for files
            metadata: Optional metadata for all files
            
        Returns:
            List of all chunks from all files
        """
        all_chunks = []
        directory_path = Path(directory)
        
        # Supported extensions
        supported_exts = {'.pdf', '.md', '.html', '.htm', '.txt'}
        
        # Find all matching files
        for file_path in directory_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                try:
                    chunks = self.load_and_chunk_file(str(file_path), metadata)
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
        
        logger.info(f"✓ Processed directory: {directory} → {len(all_chunks)} total chunks")
        
        return all_chunks


# Convenience function
def load_documents_with_langchain(
    file_paths: List[str],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    splitter_type: str = "recursive"
) -> List[Dict]:
    """
    Convenience function to load and chunk multiple files with LangChain.
    
    Args:
        file_paths: List of file paths
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        splitter_type: Type of splitter ('recursive', 'token', 'semantic')
        
    Returns:
        List of all chunks from all files
    """
    loader = LangChainDocumentLoader(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        splitter_type=splitter_type
    )
    
    all_chunks = []
    for file_path in file_paths:
        chunks = loader.load_and_chunk_file(file_path)
        all_chunks.extend(chunks)
    
    return all_chunks
