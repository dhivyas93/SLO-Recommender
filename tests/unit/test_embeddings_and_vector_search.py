"""
Unit tests for embeddings generation and vector search in RAG Engine.

Tests the core functionality of:
- Generating embeddings for text
- Batch embedding generation
- Vector search using cosine similarity
- Threshold-based retrieval
- Metadata-based retrieval
- Diverse result retrieval
- Multi-source retrieval
"""

import pytest
import numpy as np

# Check if sentence-transformers is available
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from src.engines.rag_engine import RAGEngine


@pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
class TestEmbeddingsGeneration:
    """Test embedding generation functionality."""
    
    @pytest.fixture
    def rag_engine(self):
        """Create RAG engine instance."""
        return RAGEngine()
    
    def test_generate_embedding_single_text(self, rag_engine):
        """Test generating embedding for a single text."""
        text = "API gateway for microservices"
        
        embedding = rag_engine.generate_embedding(text)
        
        # Verify embedding is a list
        assert isinstance(embedding, list)
        
        # Verify embedding has correct dimension (384 for all-MiniLM-L6-v2)
        assert len(embedding) == 384
        
        # Verify all values are floats
        assert all(isinstance(val, float) for val in embedding)
    
    def test_generate_embedding_empty_text_raises_error(self, rag_engine):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            rag_engine.generate_embedding("")
    
    def test_generate_embedding_whitespace_only_raises_error(self, rag_engine):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            rag_engine.generate_embedding("   \n\t  ")
    
    def test_generate_embedding_long_text(self, rag_engine):
        """Test generating embedding for long text."""
        # Create a long text (will be truncated by model to max_seq_length)
        long_text = "This is a test. " * 100
        
        embedding = rag_engine.generate_embedding(long_text)
        
        # Should still return valid embedding
        assert isinstance(embedding, list)
        assert len(embedding) == 384
    
    def test_generate_embeddings_batch(self, rag_engine):
        """Test batch embedding generation."""
        texts = [
            "API gateway for microservices",
            "Database with high availability",
            "Message queue for async processing"
        ]
        
        embeddings = rag_engine.generate_embeddings_batch(texts)
        
        # Verify we get a list of embeddings
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        
        # Verify each embedding is correct
        for embedding in embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) == 384
            assert all(isinstance(val, float) for val in embedding)
    
    def test_generate_embeddings_batch_empty_list_raises_error(self, rag_engine):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            rag_engine.generate_embeddings_batch([])
    
    def test_generate_embeddings_batch_single_text(self, rag_engine):
        """Test batch generation with single text."""
        texts = ["Single text"]
        
        embeddings = rag_engine.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 384
    
    def test_embeddings_are_normalized(self, rag_engine):
        """Test that embeddings are normalized (L2 norm ≈ 1)."""
        text = "Test text for normalization"
        
        embedding = rag_engine.generate_embedding(text)
        
        # Compute L2 norm
        norm = np.sqrt(sum(x**2 for x in embedding))
        
        # Should be approximately 1 (normalized)
        assert 0.99 < norm < 1.01
    
    def test_similar_texts_have_similar_embeddings(self, rag_engine):
        """Test that similar texts produce similar embeddings."""
        text1 = "API gateway for microservices"
        text2 = "API gateway for distributed services"
        text3 = "Database with high availability"
        
        embedding1 = rag_engine.generate_embedding(text1)
        embedding2 = rag_engine.generate_embedding(text2)
        embedding3 = rag_engine.generate_embedding(text3)
        
        # Compute cosine similarities
        from sklearn.metrics.pairwise import cosine_similarity
        
        sim_1_2 = cosine_similarity([embedding1], [embedding2])[0][0]
        sim_1_3 = cosine_similarity([embedding1], [embedding3])[0][0]
        
        # Similar texts should have higher similarity
        assert sim_1_2 > sim_1_3


@pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
class TestVectorSearch:
    """Test vector search functionality."""
    
    @pytest.fixture
    def rag_engine(self):
        """Create RAG engine instance."""
        return RAGEngine()
    
    @pytest.fixture
    def sample_embeddings_db(self, rag_engine):
        """Create sample embeddings database."""
        documents = [
            {
                "source": "runbook_api_gateway",
                "content": "API gateway SLO recommendations: 99.9% availability, 100ms p95 latency",
                "metadata": {"type": "runbook", "service_type": "api_gateway"}
            },
            {
                "source": "runbook_database",
                "content": "Database SLO recommendations: 99.95% availability, 50ms p95 latency",
                "metadata": {"type": "runbook", "service_type": "database"}
            },
            {
                "source": "best_practice_cache",
                "content": "Cache best practices: high hit rate improves latency significantly",
                "metadata": {"type": "best_practice", "service_type": "cache"}
            },
            {
                "source": "historical_payment",
                "content": "Payment service historical pattern: 99.5% availability, 200ms p95 latency",
                "metadata": {"type": "historical", "service_type": "payment"}
            }
        ]
        
        # Generate embeddings for all documents
        contents = [doc["content"] for doc in documents]
        embeddings = rag_engine.generate_embeddings_batch(contents)
        
        # Add embeddings to documents
        for doc, embedding in zip(documents, embeddings):
            doc["embedding"] = embedding
        
        return documents
    
    def test_search_embeddings_basic(self, rag_engine, sample_embeddings_db):
        """Test basic vector search."""
        # Create query embedding
        query_text = "API gateway SLO recommendations"
        query_embedding = rag_engine.generate_embedding(query_text)
        
        # Search
        results = rag_engine.search_embeddings(query_embedding, sample_embeddings_db, top_k=2)
        
        # Verify results
        assert len(results) == 2
        assert all("score" in result for result in results)
        assert all("source" in result for result in results)
        
        # Results should be sorted by score (highest first)
        assert results[0]["score"] >= results[1]["score"]
    
    def test_search_embeddings_top_k(self, rag_engine, sample_embeddings_db):
        """Test that top_k parameter works correctly."""
        query_embedding = rag_engine.generate_embedding("SLO recommendations")
        
        # Search with different top_k values
        results_1 = rag_engine.search_embeddings(query_embedding, sample_embeddings_db, top_k=1)
        results_3 = rag_engine.search_embeddings(query_embedding, sample_embeddings_db, top_k=3)
        
        assert len(results_1) == 1
        assert len(results_3) == 3
        
        # First result should be the same
        assert results_1[0]["source"] == results_3[0]["source"]
    
    def test_search_embeddings_empty_query_raises_error(self, rag_engine, sample_embeddings_db):
        """Test that empty query embedding raises ValueError."""
        with pytest.raises(ValueError, match="Query embedding cannot be empty"):
            rag_engine.search_embeddings([], sample_embeddings_db)
    
    def test_search_embeddings_empty_db_raises_error(self, rag_engine):
        """Test that empty database raises ValueError."""
        query_embedding = rag_engine.generate_embedding("test")
        
        with pytest.raises(ValueError, match="Embeddings database cannot be empty"):
            rag_engine.search_embeddings(query_embedding, [])
    
    def test_search_embeddings_invalid_top_k_raises_error(self, rag_engine, sample_embeddings_db):
        """Test that invalid top_k raises ValueError."""
        query_embedding = rag_engine.generate_embedding("test")
        
        with pytest.raises(ValueError, match="top_k must be >= 1"):
            rag_engine.search_embeddings(query_embedding, sample_embeddings_db, top_k=0)
    
    def test_search_by_text(self, rag_engine, sample_embeddings_db):
        """Test search by text query."""
        results = rag_engine.search_by_text("API gateway", sample_embeddings_db, top_k=2)
        
        assert len(results) <= 2
        assert all("score" in result for result in results)
        assert all("content" in result for result in results)
    
    def test_search_by_text_empty_query_raises_error(self, rag_engine, sample_embeddings_db):
        """Test that empty text query raises ValueError."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            rag_engine.search_by_text("", sample_embeddings_db)
    
    def test_search_by_service_type(self, rag_engine, sample_embeddings_db):
        """Test search by service type."""
        results = rag_engine.search_by_service_type("api_gateway", sample_embeddings_db, top_k=2)
        
        assert len(results) <= 2
        assert all("score" in result for result in results)
    
    def test_batch_search(self, rag_engine, sample_embeddings_db):
        """Test batch search with multiple queries."""
        query_texts = [
            "API gateway SLO",
            "Database recommendations",
            "Cache best practices"
        ]
        
        query_embeddings = rag_engine.generate_embeddings_batch(query_texts)
        results = rag_engine.batch_search(query_embeddings, sample_embeddings_db, top_k=2)
        
        # Should have results for each query
        assert len(results) == 3
        
        # Each query should have up to top_k results
        for query_results in results:
            assert len(query_results) <= 2
    
    def test_retrieve_with_threshold(self, rag_engine, sample_embeddings_db):
        """Test retrieval with similarity threshold."""
        query_embedding = rag_engine.generate_embedding("API gateway SLO")
        
        # Retrieve with high threshold
        results_high = rag_engine.retrieve_with_threshold(
            query_embedding,
            sample_embeddings_db,
            similarity_threshold=0.7
        )
        
        # Retrieve with low threshold
        results_low = rag_engine.retrieve_with_threshold(
            query_embedding,
            sample_embeddings_db,
            similarity_threshold=0.3
        )
        
        # Low threshold should return more results
        assert len(results_low) >= len(results_high)
        
        # All results should meet threshold
        for result in results_high:
            assert result["score"] >= 0.7
        
        for result in results_low:
            assert result["score"] >= 0.3
    
    def test_retrieve_with_threshold_invalid_threshold_raises_error(self, rag_engine, sample_embeddings_db):
        """Test that invalid threshold raises ValueError."""
        query_embedding = rag_engine.generate_embedding("test")
        
        with pytest.raises(ValueError, match="similarity_threshold must be between 0 and 1"):
            rag_engine.retrieve_with_threshold(query_embedding, sample_embeddings_db, similarity_threshold=1.5)
    
    def test_retrieve_by_metadata(self, rag_engine, sample_embeddings_db):
        """Test retrieval by metadata filter."""
        # Retrieve all runbooks
        results = rag_engine.retrieve_by_metadata(
            sample_embeddings_db,
            {"type": "runbook"}
        )
        
        assert len(results) == 2
        assert all(result["metadata"]["type"] == "runbook" for result in results)
    
    def test_retrieve_by_metadata_multiple_filters(self, rag_engine, sample_embeddings_db):
        """Test retrieval with multiple metadata filters."""
        results = rag_engine.retrieve_by_metadata(
            sample_embeddings_db,
            {"type": "runbook", "service_type": "api_gateway"}
        )
        
        assert len(results) == 1
        assert results[0]["source"] == "runbook_api_gateway"
    
    def test_retrieve_by_metadata_no_matches(self, rag_engine, sample_embeddings_db):
        """Test retrieval with no matching metadata."""
        results = rag_engine.retrieve_by_metadata(
            sample_embeddings_db,
            {"type": "nonexistent"}
        )
        
        assert len(results) == 0
    
    def test_retrieve_by_metadata_empty_filter_raises_error(self, rag_engine, sample_embeddings_db):
        """Test that empty metadata filter raises ValueError."""
        with pytest.raises(ValueError, match="metadata_filter cannot be empty"):
            rag_engine.retrieve_by_metadata(sample_embeddings_db, {})
    
    def test_retrieve_diverse_results(self, rag_engine, sample_embeddings_db):
        """Test retrieval with diversity consideration."""
        query_embedding = rag_engine.generate_embedding("SLO recommendations")
        
        # Retrieve with diversity
        results_diverse = rag_engine.retrieve_diverse_results(
            query_embedding,
            sample_embeddings_db,
            top_k=3,
            diversity_factor=0.5
        )
        
        # Retrieve without diversity (pure relevance)
        results_relevant = rag_engine.search_embeddings(
            query_embedding,
            sample_embeddings_db,
            top_k=3
        )
        
        # Both should return results
        assert len(results_diverse) > 0
        assert len(results_relevant) > 0
    
    def test_retrieve_diverse_results_invalid_diversity_factor_raises_error(self, rag_engine, sample_embeddings_db):
        """Test that invalid diversity factor raises ValueError."""
        query_embedding = rag_engine.generate_embedding("test")
        
        with pytest.raises(ValueError, match="diversity_factor must be between 0 and 1"):
            rag_engine.retrieve_diverse_results(
                query_embedding,
                sample_embeddings_db,
                diversity_factor=1.5
            )
    
    def test_retrieve_multi_source(self, rag_engine, sample_embeddings_db):
        """Test retrieval from multiple sources."""
        # Organize embeddings by source
        embeddings_data = {
            "runbooks": [doc for doc in sample_embeddings_db if doc["metadata"]["type"] == "runbook"],
            "best_practices": [doc for doc in sample_embeddings_db if doc["metadata"]["type"] == "best_practice"],
            "historical": [doc for doc in sample_embeddings_db if doc["metadata"]["type"] == "historical"]
        }
        
        query_embedding = rag_engine.generate_embedding("SLO recommendations")
        
        results = rag_engine.retrieve_multi_source(
            query_embedding,
            embeddings_data,
            top_k_per_source=2
        )
        
        # Should have results organized by source
        assert "runbooks" in results
        assert "best_practices" in results
        assert "historical" in results
        
        # Each source should have up to top_k_per_source results
        for source_results in results.values():
            assert len(source_results) <= 2


@pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
class TestEmbeddingsStorage:
    """Test embeddings storage and loading."""
    
    @pytest.fixture
    def rag_engine(self):
        """Create RAG engine instance."""
        return RAGEngine()
    
    def test_store_and_load_embeddings(self, rag_engine, tmp_path):
        """Test storing and loading embeddings."""
        # Create sample embeddings data
        embeddings_data = {
            "runbooks": [
                {
                    "source": "test_runbook",
                    "content": "Test content",
                    "embedding": rag_engine.generate_embedding("Test content"),
                    "metadata": {"type": "runbook"}
                }
            ]
        }
        
        # Store embeddings
        filepath = "test_embeddings.json"
        rag_engine.store_embeddings(embeddings_data, filepath)
        
        # Load embeddings
        loaded_data = rag_engine.load_embeddings(filepath)
        
        # Verify data
        assert "runbooks" in loaded_data
        assert len(loaded_data["runbooks"]) == 1
        assert loaded_data["runbooks"][0]["source"] == "test_runbook"
    
    def test_load_nonexistent_embeddings_raises_error(self, rag_engine):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            rag_engine.load_embeddings("nonexistent_file.json")
