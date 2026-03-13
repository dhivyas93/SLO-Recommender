"""
RAG Engine for Retrieval-Augmented Generation

This module implements the RAG engine for retrieving relevant knowledge from
historical data, runbooks, and best practices to ground LLM recommendations.

Technology:
- Embeddings: sentence-transformers with all-MiniLM-L6-v2 (free, local, 86MB)
- Vector Search: Simple cosine similarity for POC (no external dependencies)
"""

import logging
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    RAG Engine for embedding generation and knowledge retrieval.
    
    This engine handles:
    - Loading sentence-transformers embedding model
    - Generating embeddings for text
    - Vector search using cosine similarity
    - Knowledge base retrieval
    
    The model is lazily loaded on first use to avoid unnecessary initialization.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG engine.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
                       Default is "all-MiniLM-L6-v2" (86MB, fast on CPU).
        """
        self.model_name = model_name
        self._model = None  # Lazy loading
        logger.info(f"RAGEngine initialized with model: {model_name}")
    
    def load_model(self):
        """
        Load the sentence-transformers model.
        
        This method downloads the model if not cached and loads it into memory.
        The model is cached by sentence-transformers in ~/.cache/torch/sentence_transformers/
        
        Raises:
            ImportError: If sentence-transformers is not installed
            Exception: If model loading fails (network issues, invalid model name, etc.)
        """
        if self._model is not None:
            logger.debug("Model already loaded, skipping")
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            logger.info("This may take a moment on first run (downloading ~86MB model)")
            
            # Load the model - this will download if not cached
            self._model = SentenceTransformer(self.model_name)
            
            logger.info(f"Model {self.model_name} loaded successfully")
            logger.info(f"Model max sequence length: {self._model.max_seq_length}")
            
        except ImportError as e:
            error_msg = (
                "sentence-transformers is not installed. "
                "Please install it with: pip install sentence-transformers"
            )
            logger.error(error_msg)
            raise ImportError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Failed to load model {self.model_name}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    @property
    def model(self):
        """
        Get the embedding model, loading it if necessary.
        
        Returns:
            SentenceTransformer: The loaded embedding model
            
        Raises:
            Exception: If model loading fails
        """
        if self._model is None:
            self.load_model()
        return self._model
    
    def is_model_loaded(self) -> bool:
        """
        Check if the model is currently loaded.
        
        Returns:
            bool: True if model is loaded, False otherwise
        """
        return self._model is not None

    def chunk_document(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split document into overlapping chunks.
        
        This method splits long documents into smaller chunks that fit within
        the model's max sequence length (256 tokens for all-MiniLM-L6-v2).
        
        The chunking strategy:
        1. Split on paragraph boundaries (double newlines) when possible
        2. If paragraphs are too long, split on sentence boundaries
        3. If sentences are too long, split on word boundaries
        4. Use overlap between chunks to preserve context
        
        Args:
            text: The document text to chunk
            chunk_size: Maximum chunk size in characters (default: 500)
                       Note: 500 chars ≈ 125 tokens, well under 256 token limit
            overlap: Number of characters to overlap between chunks (default: 50)
                    This preserves context across chunk boundaries
        
        Returns:
            List of text chunks, each <= chunk_size characters
            
        Examples:
            >>> engine = RAGEngine()
            >>> text = "First paragraph.\\n\\nSecond paragraph.\\n\\nThird paragraph."
            >>> chunks = engine.chunk_document(text, chunk_size=30, overlap=10)
            >>> len(chunks) >= 1
            True
        """
        if not text or not text.strip():
            return []
        
        # If text is already small enough, return as single chunk
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        
        # Try to split on paragraph boundaries first (double newlines)
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph would exceed chunk_size
            if len(current_chunk) + len(paragraph) + 2 > chunk_size:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap from previous chunk
                    if overlap > 0 and len(current_chunk) > overlap:
                        # Take last 'overlap' characters from previous chunk
                        overlap_text = current_chunk[-overlap:].strip()
                        current_chunk = overlap_text + "\n\n"
                    else:
                        current_chunk = ""
                
                # If paragraph itself is too long, split it further
                if len(paragraph) > chunk_size:
                    # Split on sentence boundaries
                    sentences = self._split_into_sentences(paragraph)
                    
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 > chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                
                                # Add overlap
                                if overlap > 0 and len(current_chunk) > overlap:
                                    overlap_text = current_chunk[-overlap:].strip()
                                    current_chunk = overlap_text + " "
                                else:
                                    current_chunk = ""
                            
                            # If sentence itself is too long, split on words
                            if len(sentence) > chunk_size:
                                word_chunks = self._split_long_text(sentence, chunk_size, overlap)
                                chunks.extend(word_chunks[:-1])  # Add all but last
                                current_chunk = word_chunks[-1] if word_chunks else ""
                            else:
                                current_chunk = sentence
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
                else:
                    current_chunk = paragraph
            else:
                # Add paragraph to current chunk
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Uses simple heuristics to split on sentence boundaries:
        - Period followed by space and capital letter
        - Question mark or exclamation mark followed by space
        - Newlines
        
        Args:
            text: Text to split into sentences
            
        Returns:
            List of sentences
        """
        import re
        
        # Split on sentence boundaries
        # Pattern: . ! ? followed by space and capital letter, or newline
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\n+', text)
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_long_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Split long text on word boundaries.
        
        This is a fallback for when text cannot be split on paragraph or
        sentence boundaries and still fit within chunk_size.
        
        Args:
            text: Text to split
            chunk_size: Maximum chunk size in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = ""
        
        for word in words:
            # If adding this word would exceed chunk_size
            if len(current_chunk) + len(word) + 1 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap
                    if overlap > 0:
                        # Take last few words for overlap
                        chunk_words = current_chunk.split()
                        overlap_words = []
                        overlap_len = 0
                        
                        for w in reversed(chunk_words):
                            if overlap_len + len(w) + 1 <= overlap:
                                overlap_words.insert(0, w)
                                overlap_len += len(w) + 1
                            else:
                                break
                        
                        current_chunk = " ".join(overlap_words) + " " if overlap_words else ""
                    else:
                        current_chunk = ""
                
                # If single word is longer than chunk_size, force split it
                if len(word) > chunk_size:
                    # Split word into chunk_size pieces
                    for i in range(0, len(word), chunk_size - overlap):
                        chunk = word[i:i + chunk_size]
                        chunks.append(chunk)
                    current_chunk = ""
                else:
                    current_chunk = word
            else:
                current_chunk += " " + word if current_chunk else word
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


    def generate_embedding(self, text: str) -> list:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding as a list of floats

        Raises:
            ValueError: If text is empty
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            # Get the model (lazy loads if needed)
            model = self.model

            # Encode the text
            embedding = model.encode(text)

            # Convert numpy array to list for JSON serialization
            return embedding.tolist()

        except Exception as e:
            error_msg = f"Failed to generate embedding: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def generate_embeddings_batch(self, texts: List[str]) -> List[list]:
        """
        Generate embeddings for multiple texts in batch.

        Batch processing is more efficient than individual calls.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings, each as a list of floats

        Raises:
            ValueError: If texts list is empty
            Exception: If embedding generation fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        try:
            # Get the model (lazy loads if needed)
            model = self.model

            # Encode all texts at once (more efficient)
            embeddings = model.encode(texts)

            # Convert numpy array to list of lists for JSON serialization
            return embeddings.tolist()

        except Exception as e:
            error_msg = f"Failed to generate batch embeddings: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def store_embeddings(self, embeddings_data: dict, filepath: str) -> None:
        """
        Store embeddings to a JSON file.

        Args:
            embeddings_data: Dictionary containing embeddings data
            filepath: Path where to store the embeddings JSON file

        Raises:
            Exception: If file writing fails
        """
        try:
            from src.storage.file_storage import FileStorage

            storage = FileStorage()
            storage.write_json(filepath, embeddings_data)

            logger.info(f"Embeddings stored to {filepath}")

        except Exception as e:
            error_msg = f"Failed to store embeddings to {filepath}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def load_embeddings(self, filepath: str) -> dict:
        """
        Load embeddings from a JSON file.

        Args:
            filepath: Path to the embeddings JSON file

        Returns:
            Dictionary containing embeddings data

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If file reading fails
        """
        try:
            from src.storage.file_storage import FileStorage

            storage = FileStorage()
            embeddings_data = storage.read_json(filepath)

            logger.info(f"Embeddings loaded from {filepath}")
            return embeddings_data

        except FileNotFoundError as e:
            error_msg = f"Embeddings file not found: {filepath}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to load embeddings from {filepath}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e


    def search_embeddings(
        self,
        query_embedding: list,
        embeddings_db: list,
        top_k: int = 5
    ) -> list:
        """
        Search for most similar embeddings using cosine similarity.

        This method computes cosine similarity between a query embedding
        and all embeddings in the database, returning the top-k most similar.

        Args:
            query_embedding: Query embedding as a list of floats
            embeddings_db: List of embedding documents, each with 'embedding' key
            top_k: Number of top results to return (default: 5)

        Returns:
            List of top-k most similar documents with similarity scores,
            sorted by similarity (highest first)

        Raises:
            ValueError: If inputs are invalid
            Exception: If search fails
        """
        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")

        if not embeddings_db:
            raise ValueError("Embeddings database cannot be empty")

        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            # Convert query embedding to numpy array
            query_array = np.array([query_embedding])

            # Compute similarity scores
            results = []
            for doc in embeddings_db:
                if 'embedding' not in doc:
                    logger.warning(f"Document missing 'embedding' key: {doc.get('source', 'unknown')}")
                    continue

                # Get document embedding
                doc_embedding = doc['embedding']

                # Compute cosine similarity
                similarity = cosine_similarity(
                    query_array,
                    [doc_embedding]
                )[0][0]

                # Store result with metadata
                results.append({
                    'source': doc.get('source', 'unknown'),
                    'content': doc.get('content', ''),
                    'embedding': doc_embedding,
                    'score': float(similarity),
                    'metadata': doc.get('metadata', {})
                })

            # Sort by similarity (highest first)
            results.sort(key=lambda x: x['score'], reverse=True)

            # Return top-k
            return results[:top_k]

        except Exception as e:
            error_msg = f"Failed to search embeddings: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def search_by_text(
        self,
        query_text: str,
        embeddings_db: list,
        top_k: int = 5
    ) -> list:
        """
        Search for most similar documents by text query.

        This method:
        1. Generates embedding for the query text
        2. Searches for similar embeddings
        3. Returns top-k results

        Args:
            query_text: Query text to search for
            embeddings_db: List of embedding documents
            top_k: Number of top results to return (default: 5)

        Returns:
            List of top-k most similar documents with similarity scores

        Raises:
            ValueError: If query_text is empty
            Exception: If search fails
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query text cannot be empty")

        try:
            # Generate embedding for query text
            query_embedding = self.generate_embedding(query_text)

            # Search using the embedding
            results = self.search_embeddings(query_embedding, embeddings_db, top_k)

            logger.info(f"Found {len(results)} results for query: {query_text[:50]}...")
            return results

        except Exception as e:
            error_msg = f"Failed to search by text: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def search_by_service_type(
        self,
        service_type: str,
        embeddings_db: list,
        top_k: int = 5
    ) -> list:
        """
        Search for best practices and patterns for a specific service type.

        This method searches for documents related to a specific service type
        (e.g., 'api_gateway', 'database', 'message_queue').

        Args:
            service_type: Service type to search for
            embeddings_db: List of embedding documents
            top_k: Number of top results to return (default: 5)

        Returns:
            List of top-k most relevant documents for the service type

        Raises:
            ValueError: If service_type is empty
            Exception: If search fails
        """
        if not service_type or not service_type.strip():
            raise ValueError("Service type cannot be empty")

        try:
            # Create a query based on service type
            query_text = f"SLO recommendations for {service_type} services"

            # Search using the query
            results = self.search_by_text(query_text, embeddings_db, top_k)

            logger.info(f"Found {len(results)} results for service type: {service_type}")
            return results

        except Exception as e:
            error_msg = f"Failed to search by service type: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def batch_search(
        self,
        query_embeddings: List[list],
        embeddings_db: list,
        top_k: int = 5
    ) -> List[list]:
        """
        Search for multiple query embeddings efficiently.

        This method performs batch search for multiple queries,
        returning top-k results for each query.

        Args:
            query_embeddings: List of query embeddings
            embeddings_db: List of embedding documents
            top_k: Number of top results per query (default: 5)

        Returns:
            List of result lists, one per query

        Raises:
            ValueError: If inputs are invalid
            Exception: If search fails
        """
        if not query_embeddings:
            raise ValueError("Query embeddings list cannot be empty")

        try:
            results = []
            for query_embedding in query_embeddings:
                query_results = self.search_embeddings(
                    query_embedding,
                    embeddings_db,
                    top_k
                )
                results.append(query_results)

            logger.info(f"Completed batch search for {len(query_embeddings)} queries")
            return results

        except Exception as e:
            error_msg = f"Failed to perform batch search: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e


    def retrieve_with_threshold(
        self,
        query_embedding: list,
        embeddings_db: list,
        similarity_threshold: float = 0.5
    ) -> list:
        """
        Retrieve documents above a similarity threshold.

        Instead of returning top-k, this returns all documents
        with similarity score >= threshold, sorted by score.

        Args:
            query_embedding: Query embedding as a list of floats
            embeddings_db: List of embedding documents
            similarity_threshold: Minimum similarity score (0-1, default: 0.5)

        Returns:
            List of documents with similarity >= threshold, sorted by score

        Raises:
            ValueError: If threshold is invalid
            Exception: If retrieval fails
        """
        if not (0 <= similarity_threshold <= 1):
            raise ValueError("similarity_threshold must be between 0 and 1")

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            # Convert query embedding to numpy array
            query_array = np.array([query_embedding])

            # Compute similarity scores
            results = []
            for doc in embeddings_db:
                if 'embedding' not in doc:
                    continue

                # Compute cosine similarity
                similarity = cosine_similarity(
                    query_array,
                    [doc['embedding']]
                )[0][0]

                # Only include if above threshold
                if similarity >= similarity_threshold:
                    results.append({
                        'source': doc.get('source', 'unknown'),
                        'content': doc.get('content', ''),
                        'embedding': doc['embedding'],
                        'score': float(similarity),
                        'metadata': doc.get('metadata', {})
                    })

            # Sort by similarity (highest first)
            results.sort(key=lambda x: x['score'], reverse=True)

            logger.info(f"Retrieved {len(results)} documents above threshold {similarity_threshold}")
            return results

        except Exception as e:
            error_msg = f"Failed to retrieve with threshold: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def retrieve_by_metadata(
        self,
        embeddings_db: list,
        metadata_filter: dict
    ) -> list:
        """
        Retrieve documents matching metadata criteria.

        This filters embeddings by metadata fields without similarity search.
        Useful for finding all documents of a specific type or service.

        Args:
            embeddings_db: List of embedding documents
            metadata_filter: Dictionary of metadata key-value pairs to match
                           Example: {'document_type': 'runbook', 'service_type': 'api_gateway'}

        Returns:
            List of documents matching all metadata criteria

        Raises:
            ValueError: If metadata_filter is empty
            Exception: If retrieval fails
        """
        if not metadata_filter:
            raise ValueError("metadata_filter cannot be empty")

        try:
            results = []

            for doc in embeddings_db:
                metadata = doc.get('metadata', {})

                # Check if all filter criteria match
                if all(metadata.get(key) == value for key, value in metadata_filter.items()):
                    results.append({
                        'source': doc.get('source', 'unknown'),
                        'content': doc.get('content', ''),
                        'embedding': doc.get('embedding', []),
                        'score': 1.0,  # Perfect match for metadata
                        'metadata': metadata
                    })

            logger.info(f"Retrieved {len(results)} documents matching metadata filter")
            return results

        except Exception as e:
            error_msg = f"Failed to retrieve by metadata: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def retrieve_diverse_results(
        self,
        query_embedding: list,
        embeddings_db: list,
        top_k: int = 5,
        diversity_factor: float = 0.3
    ) -> list:
        """
        Retrieve top-k results with diversity consideration.

        This retrieves results that are both relevant to the query
        and diverse from each other, avoiding redundant results.

        Algorithm:
        1. Start with highest similarity result
        2. For each subsequent result, consider both:
           - Similarity to query (relevance)
           - Dissimilarity to already selected results (diversity)
        3. Score = (1 - diversity_factor) * query_similarity + diversity_factor * avg_dissimilarity

        Args:
            query_embedding: Query embedding as a list of floats
            embeddings_db: List of embedding documents
            top_k: Number of results to return (default: 5)
            diversity_factor: Weight for diversity (0-1, default: 0.3)
                            0 = pure relevance, 1 = pure diversity

        Returns:
            List of top-k diverse results

        Raises:
            ValueError: If inputs are invalid
            Exception: If retrieval fails
        """
        if not (0 <= diversity_factor <= 1):
            raise ValueError("diversity_factor must be between 0 and 1")

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            if not embeddings_db:
                return []

            # Get all similarity scores to query
            query_array = np.array([query_embedding])
            all_similarities = []

            for doc in embeddings_db:
                if 'embedding' not in doc:
                    continue

                similarity = cosine_similarity(
                    query_array,
                    [doc['embedding']]
                )[0][0]

                all_similarities.append({
                    'doc': doc,
                    'query_similarity': float(similarity)
                })

            if not all_similarities:
                return []

            # Sort by query similarity
            all_similarities.sort(key=lambda x: x['query_similarity'], reverse=True)

            # Greedy selection for diversity
            selected = []
            selected_embeddings = []

            for item in all_similarities:
                if len(selected) >= top_k:
                    break

                doc = item['doc']
                query_sim = item['query_similarity']

                if not selected:
                    # First result: just use query similarity
                    selected.append(doc)
                    selected_embeddings.append(doc['embedding'])
                else:
                    # Compute average dissimilarity to selected results
                    doc_embedding = np.array([doc['embedding']])
                    selected_array = np.array(selected_embeddings)

                    similarities_to_selected = cosine_similarity(
                        doc_embedding,
                        selected_array
                    )[0]

                    avg_similarity_to_selected = np.mean(similarities_to_selected)
                    avg_dissimilarity = 1 - avg_similarity_to_selected

                    # Combined score
                    combined_score = (
                        (1 - diversity_factor) * query_sim +
                        diversity_factor * avg_dissimilarity
                    )

                    # Only add if it improves diversity
                    if avg_dissimilarity > 0.1 or len(selected) < 2:
                        selected.append(doc)
                        selected_embeddings.append(doc['embedding'])

            # Format results
            results = []
            for doc in selected:
                query_array_np = np.array([query_embedding])
                score = cosine_similarity(
                    query_array_np,
                    [doc['embedding']]
                )[0][0]

                results.append({
                    'source': doc.get('source', 'unknown'),
                    'content': doc.get('content', ''),
                    'embedding': doc['embedding'],
                    'score': float(score),
                    'metadata': doc.get('metadata', {})
                })

            logger.info(f"Retrieved {len(results)} diverse results")
            return results

        except Exception as e:
            error_msg = f"Failed to retrieve diverse results: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def retrieve_multi_source(
        self,
        query_embedding: list,
        embeddings_data: dict,
        top_k_per_source: int = 3
    ) -> dict:
        """
        Retrieve top-k results from each knowledge source separately.

        This retrieves results from different sources (runbooks, best practices, historical)
        separately, ensuring diverse knowledge sources in the results.

        Args:
            query_embedding: Query embedding as a list of floats
            embeddings_data: Dictionary with 'runbooks', 'best_practices', 'historical' keys
            top_k_per_source: Number of results per source (default: 3)

        Returns:
            Dictionary with results organized by source:
            {
                'runbooks': [...],
                'best_practices': [...],
                'historical': [...]
            }

        Raises:
            ValueError: If inputs are invalid
            Exception: If retrieval fails
        """
        if not embeddings_data:
            raise ValueError("embeddings_data cannot be empty")

        try:
            results = {}

            for source_name in ['runbooks', 'best_practices', 'historical']:
                source_embeddings = embeddings_data.get(source_name, [])

                if source_embeddings:
                    source_results = self.search_embeddings(
                        query_embedding,
                        source_embeddings,
                        top_k=top_k_per_source
                    )
                    results[source_name] = source_results
                else:
                    results[source_name] = []

            logger.info(f"Retrieved results from {len([s for s in results if results[s]])} sources")
            return results

        except Exception as e:
            error_msg = f"Failed to retrieve from multiple sources: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e



