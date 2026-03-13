"""
Unit tests for RAG Engine - Embedding Model Loading

Tests the core functionality of loading and managing the sentence-transformers
embedding model for the RAG engine.

NOTE: These tests require sentence-transformers to be installed.
If the library is not available, tests will be skipped.
"""

import pytest

# Check if sentence-transformers is available
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from src.engines.rag_engine import RAGEngine


class TestRAGEngineInitialization:
    """Test RAG engine initialization and configuration."""
    
    def test_init_with_default_model(self):
        """Test initialization with default model name."""
        engine = RAGEngine()
        assert engine.model_name == "all-MiniLM-L6-v2"
        assert engine._model is None  # Lazy loading
        assert not engine.is_model_loaded()
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model name."""
        custom_model = "paraphrase-MiniLM-L6-v2"
        engine = RAGEngine(model_name=custom_model)
        assert engine.model_name == custom_model
        assert engine._model is None
        assert not engine.is_model_loaded()


@pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
class TestRAGEngineModelLoading:
    """Test embedding model loading functionality."""
    
    def test_load_model_success(self):
        """Test successful model loading."""
        engine = RAGEngine()
        
        # Model should not be loaded initially
        assert not engine.is_model_loaded()
        
        # Load the model
        engine.load_model()
        
        # Model should now be loaded
        assert engine.is_model_loaded()
        assert engine._model is not None
        
        # Verify it's a SentenceTransformer instance
        assert isinstance(engine._model, SentenceTransformer)
    
    def test_load_model_idempotent(self):
        """Test that loading model multiple times doesn't reload."""
        engine = RAGEngine()
        
        # Load model first time
        engine.load_model()
        first_model = engine._model
        
        # Load model second time
        engine.load_model()
        second_model = engine._model
        
        # Should be the same instance
        assert first_model is second_model
    
    def test_model_property_lazy_loads(self):
        """Test that accessing model property triggers lazy loading."""
        engine = RAGEngine()
        
        # Model not loaded initially
        assert not engine.is_model_loaded()
        
        # Access model property
        model = engine.model
        
        # Model should now be loaded
        assert engine.is_model_loaded()
        assert model is not None
        assert isinstance(model, SentenceTransformer)
    
    def test_model_property_returns_same_instance(self):
        """Test that model property returns the same instance."""
        engine = RAGEngine()
        
        model1 = engine.model
        model2 = engine.model
        
        assert model1 is model2


@pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
class TestRAGEngineErrorHandling:
    """Test error handling in RAG engine."""
    
    def test_invalid_model_name_raises_exception(self):
        """Test that invalid model name raises appropriate exception."""
        engine = RAGEngine(model_name="invalid-model-name-that-does-not-exist")
        
        with pytest.raises(Exception) as exc_info:
            engine.load_model()
        
        # Should contain error message about model loading failure
        assert "Failed to load model" in str(exc_info.value)
