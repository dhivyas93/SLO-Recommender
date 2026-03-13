"""
RAG Engine Example

This example demonstrates how to use the RAG engine for loading
the sentence-transformers embedding model.

Requirements:
- sentence-transformers must be installed: pip install sentence-transformers

Usage:
    python examples/rag_engine_example.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engines.rag_engine import RAGEngine


def main():
    """Demonstrate RAG engine embedding model loading."""
    
    print("=" * 60)
    print("RAG Engine - Embedding Model Loading Demo")
    print("=" * 60)
    print()
    
    # Initialize RAG engine with default model
    print("1. Initializing RAG engine with default model (all-MiniLM-L6-v2)...")
    engine = RAGEngine()
    print(f"   Model name: {engine.model_name}")
    print(f"   Model loaded: {engine.is_model_loaded()}")
    print()
    
    # Load the model
    print("2. Loading the embedding model...")
    print("   (This may take a moment on first run - downloading ~86MB model)")
    try:
        engine.load_model()
        print("   ✓ Model loaded successfully!")
        print(f"   Model loaded: {engine.is_model_loaded()}")
        print()
        
        # Access model properties
        print("3. Model properties:")
        print(f"   Max sequence length: {engine.model.max_seq_length}")
        print(f"   Embedding dimension: {engine.model.get_sentence_embedding_dimension()}")
        print()
        
        # Test lazy loading with a new engine
        print("4. Testing lazy loading with a new engine instance...")
        engine2 = RAGEngine()
        print(f"   Model loaded initially: {engine2.is_model_loaded()}")
        
        # Access model property (triggers lazy loading)
        model = engine2.model
        print(f"   Model loaded after accessing property: {engine2.is_model_loaded()}")
        print()
        
        # Test idempotent loading
        print("5. Testing idempotent loading...")
        first_model = engine.model
        engine.load_model()  # Load again
        second_model = engine.model
        print(f"   Same model instance: {first_model is second_model}")
        print()
        
        print("=" * 60)
        print("✓ All demonstrations completed successfully!")
        print("=" * 60)
        
    except ImportError as e:
        print(f"   ✗ Error: {e}")
        print()
        print("   Please install sentence-transformers:")
        print("   pip install sentence-transformers")
        print()
        return 1
    
    except Exception as e:
        print(f"   ✗ Error loading model: {e}")
        print()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
