import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
import copy

logger = logging.getLogger(__name__)


class LangChainDocumentLoader:
    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 300,
        splitter_type: str = "recursive"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter_type = splitter_type

        self.splitter = self._init_splitter()

        logger.info(
            f"Document Loader initialized | "
            f"chunk_size={chunk_size}, overlap={chunk_overlap}, type={splitter_type}"
        )

    # =========================
    # SPLITTER INIT
    # =========================
    def _init_splitter(self):
        try:
            # Try new import path (langchain >= 0.1.0)
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                # Fallback to old import path (langchain < 0.1.0)
                from langchain.text_splitter import RecursiveCharacterTextSplitter

            return RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=[
                    "\n\n",
                    "\n",
                    ". ",
                    ", ",
                    " ",
                    ""
                ]
            )
        except ImportError as e:
            logger.error(f"LangChain imports failed: {e}")
            logger.error("Run: pip install langchain langchain-text-splitters")
            raise

    # =========================
    # FILE LOADERS
    # =========================
    def load_pdf(self, file_path: str) -> str:
        try:
            import PyPDF2

            text_parts = []

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)

                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            text = "\n\n".join(text_parts).strip()

            if not text:
                raise ValueError("Empty PDF content")

            return text

        except Exception as e:
            raise RuntimeError(f"PDF load failed: {file_path} | {e}")

    def load_text(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().strip()

            if not text:
                raise ValueError("Empty text file")

            return text

        except Exception as e:
            raise RuntimeError(f"Text load failed: {file_path} | {e}")

    def load_html(self, file_path: str) -> str:
        try:
            from bs4 import BeautifulSoup

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            # remove noise
            for tag in soup(["script", "style", "meta", "link"]):
                tag.decompose()

            text = soup.get_text(separator="\n")

            # clean lines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned = "\n".join(lines)

            if not cleaned:
                raise ValueError("Empty HTML content")

            return cleaned

        except Exception as e:
            raise RuntimeError(f"HTML load failed: {file_path} | {e}")

    def load_file(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()

        loaders = {
            ".pdf": self.load_pdf,
            ".txt": self.load_text,
            ".md": self.load_text,
            ".html": self.load_html,
            ".htm": self.load_html,
        }

        if ext not in loaders:
            raise ValueError(f"Unsupported file type: {ext}")

        return loaders[ext](file_path)

    # =========================
    # CHUNKING
    # =========================
    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        chunks = self.splitter.split_text(text)

        results = []

        for i, chunk in enumerate(chunks):

            # better ID (stable + unique)
            raw_id = f"{metadata.get('source_file','file')}:{i}:{chunk[:50]}"
            chunk_id = hashlib.sha256(raw_id.encode()).hexdigest()

            chunk_metadata = copy.deepcopy(metadata)
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_length": len(chunk),
                "created_at": datetime.utcnow().isoformat()
            })

            results.append({
                "id": chunk_id,
                "text": chunk,
                "metadata": chunk_metadata
            })

        return results

    # =========================
    # MAIN INGESTION
    # =========================
    def load_and_chunk_file(
        self,
        file_path: str,
        user_id: Optional[int] = None,
        extra_metadata: Optional[Dict] = None
    ) -> List[Dict]:

        text = self.load_file(file_path)

        metadata = {
            "source_file": os.path.basename(file_path),
            "file_path": file_path,
            "file_type": Path(file_path).suffix.lower(),
            "file_hash": hashlib.sha256(text.encode()).hexdigest(),
            "ingestion_time": datetime.utcnow().isoformat(),
            "text_length": len(text),
        }

        # user isolation (VERY IMPORTANT for chatbot apps)
        if user_id is not None:
            metadata["user_id"] = user_id

        if extra_metadata:
            metadata.update(extra_metadata)

        return self.chunk_text(text, metadata)

    # =========================
    # DIRECTORY LOADER
    # =========================
    def load_directory(
        self,
        directory: str,
        user_id: Optional[int] = None
    ) -> List[Dict]:

        all_chunks = []

        supported = {".pdf", ".txt", ".md", ".html", ".htm"}

        for file_path in Path(directory).rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported:
                try:
                    chunks = self.load_and_chunk_file(
                        str(file_path),
                        user_id=user_id
                    )
                    all_chunks.extend(chunks)

                except Exception as e:
                    logger.error(f"Skipping {file_path}: {e}")

        logger.info(f"Loaded {len(all_chunks)} chunks from {directory}")
        return all_chunks


# =========================
# CONVENIENCE FUNCTION
# =========================
def load_documents_with_langchain(
    file_paths: List[str],
    user_id: Optional[int] = None
) -> List[Dict]:

    loader = LangChainDocumentLoader()
    all_chunks = []

    for path in file_paths:
        try:
            chunks = loader.load_and_chunk_file(path, user_id=user_id)
            all_chunks.extend(chunks)

        except Exception as e:
            logger.error(f"Skipping {path}: {e}")

    return all_chunks