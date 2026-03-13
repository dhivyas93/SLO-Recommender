"""
Example: Vector Search and Retrieval

This example demonstrates how to use the RAG engine to:
1. Search for similar documents using cosine similarity
2. Retrieve top-k most relevant documents
3. Search by text query
4. Search by service type
5. Perform batch searches

Vector search is used to find relevant knowledge base documents
to provide context for LLM-powered recommendation refinement.
"""

import logging
from pathlib import Path
from src.engines.rag_engine import RAGEngine
from src.storage.file_storage import FileStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demonstrate_cosine_similarity_search():
    """
    Demonstrate basic cosine similarity search.
    
    This shows how to search for similar embeddings given a query embedding.
    """
    
    engine = RAGEngine()
    storage = FileStorage()
    
    # Load pre-computed embeddings
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        logger.info("Run embeddings_generation_example.py first")
        return
    
    try:
        embeddings_data = engine.load_embeddings(str(embeddings_file))
        
        # Combine all embeddings for search
        all_embeddings = (
            embeddings_data.get('runbooks', []) +
            embeddings_data.get('best_practices', []) +
            embeddings_data.get('historical', [])
        )
        
        if not all_embeddings:
            logger.warning("No embeddings found in database")
            return
        
        logger.info(f"Loaded {len(all_embeddings)} embeddings for search")
        
        # Create a query embedding
        query_text = "API gateway availability and latency requirements"
        query_embedding = engine.generate_embedding(query_text)
        
        logger.info(f"\nQuery: {query_text}")
        logger.info(f"Query embedding dimension: {len(query_embedding)}")
        
        # Search for top-5 similar documents
        results = engine.search_embeddings(query_embedding, all_embeddings, top_k=5)
        
        logger.info(f"\nTop-5 most similar documents:")
        for i, result in enumerate(results, 1):
            logger.info(f"\n  {i}. Score: {result['score']:.4f}")
            logger.info(f"     Source: {result['source']}")
            logger.info(f"     Content: {result['content'][:100]}...")
            if result['metadata']:
                logger.info(f"     Metadata: {result['metadata']}")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_text_query_search():
    """
    Demonstrate searching by text query.
    
    This shows how to search for relevant documents using natural language queries.
    """
    
    engine = RAGEngine()
    
    # Load embeddings
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        return
    
    try:
        embeddings_data = engine.load_embeddings(str(embeddings_file))
        all_embeddings = (
            embeddings_data.get('runbooks', []) +
            embeddings_data.get('best_practices', []) +
            embeddings_data.get('historical', [])
        )
        
        if not all_embeddings:
            logger.warning("No embeddings found in database")
            return
        
        # Example queries
        queries = [
            "How should I set SLOs for a database service?",
            "What are best practices for message queue latency?",
            "How do I handle dependencies in SLO recommendations?",
            "What availability targets should I use for critical services?"
        ]
        
        logger.info("Text Query Search Examples:")
        logger.info("=" * 60)
        
        for query in queries:
            logger.info(f"\nQuery: {query}")
            
            results = engine.search_by_text(query, all_embeddings, top_k=3)
            
            logger.info(f"Top-3 results:")
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
                logger.info(f"     {result['content'][:80]}...")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_service_type_search():
    """
    Demonstrate searching by service type.
    
    This shows how to find relevant best practices and patterns
    for specific service types.
    """
    
    engine = RAGEngine()
    
    # Load embeddings
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        return
    
    try:
        embeddings_data = engine.load_embeddings(str(embeddings_file))
        all_embeddings = (
            embeddings_data.get('runbooks', []) +
            embeddings_data.get('best_practices', []) +
            embeddings_data.get('historical', [])
        )
        
        if not all_embeddings:
            logger.warning("No embeddings found in database")
            return
        
        # Example service types
        service_types = [
            'api_gateway',
            'database',
            'message_queue',
            'cache',
            'external_service'
        ]
        
        logger.info("Service Type Search Examples:")
        logger.info("=" * 60)
        
        for service_type in service_types:
            logger.info(f"\nService Type: {service_type}")
            
            results = engine.search_by_service_type(service_type, all_embeddings, top_k=3)
            
            logger.info(f"Top-3 relevant documents:")
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
                if isinstance(result['content'], dict):
                    logger.info(f"     Type: {result['content'].get('service_type', 'N/A')}")
                else:
                    logger.info(f"     {result['content'][:80]}...")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_batch_search():
    """
    Demonstrate batch search for multiple queries.
    
    This shows how to efficiently search for multiple queries at once.
    """
    
    engine = RAGEngine()
    
    # Load embeddings
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        return
    
    try:
        embeddings_data = engine.load_embeddings(str(embeddings_file))
        all_embeddings = (
            embeddings_data.get('runbooks', []) +
            embeddings_data.get('best_practices', []) +
            embeddings_data.get('historical', [])
        )
        
        if not all_embeddings:
            logger.warning("No embeddings found in database")
            return
        
        # Generate multiple query embeddings
        queries = [
            "API gateway SLO recommendations",
            "Database availability constraints",
            "Message queue latency budgets"
        ]
        
        logger.info("Batch Search Example:")
        logger.info("=" * 60)
        logger.info(f"Searching for {len(queries)} queries...")
        
        # Generate embeddings for all queries
        query_embeddings = engine.generate_embeddings_batch(queries)
        
        # Perform batch search
        batch_results = engine.batch_search(query_embeddings, all_embeddings, top_k=3)
        
        # Display results
        for query, results in zip(queries, batch_results):
            logger.info(f"\nQuery: {query}")
            logger.info(f"Results:")
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_relevance_scoring():
    """
    Demonstrate how relevance scores work.
    
    Cosine similarity scores range from -1 to 1:
    - 1.0: Identical embeddings (perfect match)
    - 0.5: Moderately similar
    - 0.0: Orthogonal (no similarity)
    - -1.0: Opposite embeddings (rare in practice)
    """
    
    engine = RAGEngine()
    
    logger.info("Relevance Scoring Explanation:")
    logger.info("=" * 60)
    logger.info("Cosine similarity scores range from -1 to 1:")
    logger.info("  1.0  = Identical (perfect match)")
    logger.info("  0.7+ = Highly relevant")
    logger.info("  0.5+ = Moderately relevant")
    logger.info("  0.3+ = Somewhat relevant")
    logger.info("  <0.3 = Low relevance")
    logger.info("  -1.0 = Opposite (rare)")
    
    # Create sample embeddings to demonstrate scoring
    try:
        # Generate embeddings for similar and dissimilar texts
        texts = [
            "API gateway SLO recommendations",
            "API gateway availability and latency",
            "Database performance tuning",
            "Message queue throughput optimization"
        ]
        
        embeddings = engine.generate_embeddings_batch(texts)
        
        # Create embedding documents
        embedding_docs = [
            {
                'source': f'sample_{i}',
                'content': text,
                'embedding': emb,
                'metadata': {}
            }
            for i, (text, emb) in enumerate(zip(texts, embeddings))
        ]
        
        # Search with first text as query
        query_embedding = embeddings[0]
        results = engine.search_embeddings(query_embedding, embedding_docs, top_k=4)
        
        logger.info(f"\nQuery: {texts[0]}")
        logger.info("Similarity scores to other documents:")
        for result in results:
            logger.info(f"  {result['score']:.4f} - {result['content']}")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_search_with_metadata_filtering():
    """
    Demonstrate how to use metadata for filtering search results.
    
    This shows how to search and then filter results by metadata
    (e.g., document type, service type).
    """
    
    engine = RAGEngine()
    
    # Load embeddings
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        return
    
    try:
        embeddings_data = engine.load_embeddings(str(embeddings_file))
        all_embeddings = (
            embeddings_data.get('runbooks', []) +
            embeddings_data.get('best_practices', []) +
            embeddings_data.get('historical', [])
        )
        
        if not all_embeddings:
            logger.warning("No embeddings found in database")
            return
        
        logger.info("Search with Metadata Filtering:")
        logger.info("=" * 60)
        
        # Search for all results
        query_text = "SLO recommendations"
        results = engine.search_by_text(query_text, all_embeddings, top_k=10)
        
        logger.info(f"\nQuery: {query_text}")
        logger.info(f"Total results: {len(results)}")
        
        # Filter by document type
        runbook_results = [r for r in results if r['metadata'].get('document_type') == 'runbook']
        practice_results = [r for r in results if r['metadata'].get('document_type') == 'best_practice']
        
        logger.info(f"\nRunbooks: {len(runbook_results)}")
        for result in runbook_results[:3]:
            logger.info(f"  [{result['score']:.4f}] {result['source']}")
        
        logger.info(f"\nBest Practices: {len(practice_results)}")
        for result in practice_results[:3]:
            logger.info(f"  [{result['score']:.4f}] {result['source']}")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


if __name__ == '__main__':
    # Example 1: Basic cosine similarity search
    logger.info("=" * 60)
    logger.info("Example 1: Cosine Similarity Search")
    logger.info("=" * 60)
    demonstrate_cosine_similarity_search()
    
    # Example 2: Text query search
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Text Query Search")
    logger.info("=" * 60)
    demonstrate_text_query_search()
    
    # Example 3: Service type search
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Service Type Search")
    logger.info("=" * 60)
    demonstrate_service_type_search()
    
    # Example 4: Batch search
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Batch Search")
    logger.info("=" * 60)
    demonstrate_batch_search()
    
    # Example 5: Relevance scoring
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Relevance Scoring")
    logger.info("=" * 60)
    demonstrate_relevance_scoring()
    
    # Example 6: Search with metadata filtering
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Search with Metadata Filtering")
    logger.info("=" * 60)
    demonstrate_search_with_metadata_filtering()
