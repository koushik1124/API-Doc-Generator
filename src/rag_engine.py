import os
import uuid
import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import hashlib

# Set up structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEngine:
    """
    RAG engine for context retrieval with session isolation.
    Uses in-memory storage for fast, clean processing per file.
    """
    
    def __init__(self, use_persistent: bool = False, persist_directory: str = "./chroma_db"):
        """
        Args:
            use_persistent: If True, use persistent storage (slower but keeps data)
            persist_directory: Directory for persistent storage
        """
        self.use_persistent = use_persistent
        self.session_id = str(uuid.uuid4())[:8]  # Unique session identifier
        
        # Use in-memory client by default (faster, cleaner)
        if use_persistent:
            self.client = chromadb.PersistentClient(path=persist_directory)
            logger.info(f"Using persistent storage at {persist_directory}")
        else:
            self.client = chromadb.Client()  # In-memory, no disk I/O
            logger.info("Using in-memory storage (fast mode)")
        
        # Create collection with session-specific name to avoid contamination
        self.collection_name = f"docs_session_{self.session_id}"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        
        # Load embedding model once
        try:
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ SentenceTransformer loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise
        
        # Cache for embeddings to avoid recomputation
        self._embedding_cache = {}

    def reset(self):
        """
        Reset the collection for fresh processing.
        Critical for preventing cross-file contamination.
        """
        try:
            # Delete old collection
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"🗑️ Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Collection deletion warning: {e}")
        
        # Create fresh collection with new session ID
        self.session_id = str(uuid.uuid4())[:8]
        self.collection_name = f"docs_session_{self.session_id}"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        
        # Clear cache
        self._embedding_cache.clear()
        
        logger.info(f"✨ Reset complete. New session: {self.session_id}")

    def _get_cached_embedding(self, text: str) -> List[float]:
        """
        Get embedding from cache or compute and cache it.
        Speeds up repeated queries for similar text.
        """
        # Create hash of text for cache key
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash not in self._embedding_cache:
            self._embedding_cache[text_hash] = self.embedder.encode(text).tolist()
        
        return self._embedding_cache[text_hash]

    def add_documents(self, docs: List[str]):
        """
        Add documents to the vector store with batch embedding.
        
        Args:
            docs: List of document strings to index
        """
        if not docs:
            logger.warning("No documents provided to add_documents")
            return

        # Filter out empty/whitespace-only docs
        valid_docs = [d.strip() for d in docs if d and d.strip()]
        
        if not valid_docs:
            logger.warning("All documents were empty after filtering")
            return

        try:
            # Batch encode all documents at once (faster than one-by-one)
            embeddings = self.embedder.encode(valid_docs, show_progress_bar=False).tolist()
            
            # Generate unique IDs based on content hash + timestamp
            doc_ids = [
                f"{self.session_id}_{hashlib.md5(doc.encode()).hexdigest()[:8]}"
                for doc in valid_docs
            ]

            self.collection.add(
                documents=valid_docs,
                embeddings=embeddings,
                ids=doc_ids
            )
            
            logger.info(f"✅ Indexed {len(valid_docs)} documents")
            
        except Exception as e:
            logger.error(f"❌ Error adding documents: {e}")
            raise

    def query(self, text: str, n_results: int = 2) -> List[str]:
        """
        Query the vector store for relevant context.
        
        Args:
            text: Query text
            n_results: Number of results to return
            
        Returns:
            List of relevant document strings
        """
        if not text or not text.strip():
            return []

        try:
            # Use cached embedding if available
            embedding = self._get_cached_embedding(text.strip())

            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results
            )

            # Safe extraction with defaults
            retrieved_docs = results.get("documents", [[]])
            docs = retrieved_docs[0] if retrieved_docs else []
            
            logger.debug(f"Retrieved {len(docs)} documents for query")
            return docs
            
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return []

    def query_batch(self, texts: List[str], n_results: int = 2) -> List[List[str]]:
        """
        Query multiple texts at once (much faster than individual queries).
        
        Args:
            texts: List of query texts
            n_results: Number of results per query
            
        Returns:
            List of result lists, one per input text
        """
        if not texts:
            return []

        try:
            # Batch encode all queries at once
            embeddings = [self._get_cached_embedding(t.strip()) for t in texts if t.strip()]
            
            if not embeddings:
                return [[] for _ in texts]

            results = self.collection.query(
                query_embeddings=embeddings,
                n_results=n_results
            )

            # Extract documents for each query
            all_docs = results.get("documents", [])
            
            logger.info(f"✅ Batch query: {len(texts)} queries processed")
            return all_docs
            
        except Exception as e:
            logger.error(f"❌ Batch query failed: {e}")
            return [[] for _ in texts]

    def get_stats(self) -> dict:
        """
        Get statistics about the current collection.
        Useful for debugging and monitoring.
        """
        try:
            count = self.collection.count()
            return {
                "session_id": self.session_id,
                "collection_name": self.collection_name,
                "document_count": count,
                "cache_size": len(self._embedding_cache),
                "storage_type": "persistent" if self.use_persistent else "in-memory"
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def __del__(self):
        """
        Cleanup on deletion - remove temporary collections.
        """
        if not self.use_persistent:
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.info(f"🗑️ Cleaned up session: {self.session_id}")
            except:
                pass  # Ignore cleanup errors