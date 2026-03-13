"""
Example: Advanced Retrieval Strategies

This example demonstrates advanced retrieval techniques:
1. Threshold-based retrieval (retrieve all above similarity threshold)
2. Metadata-based filtering (retrieve by document type, service type)
3. Diverse result retrieval (avoid redundant results)
4. Multi-source retrieval (retrieve from different knowledge sources)

These techniques enable more sophisticated knowledge retrieval
for LLM context grounding and recommendation refinement.
"""

import logging
from pathlib import Path
from src.engines.rag_engine import RAGEngine
from src.storage.file_storage import FileStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demonstrate_threshold_retrieval():
    """
    Demonstrate retrieval with similarity threshold.
    
    Instead of returning top-k, this returns all documents
    with similarity >= threshold, useful for finding all relevant documents.
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
        
        logger.info("Threshold-Based Retrieval Examples:")
        logger.info("=" * 60)
        
        # Generate query embedding
        query_text = "API gateway SLO recommendations"
        query_embedding = engine.generate_embedding(query_text)
        
        logger.info(f"Query: {query_text}\n")
        
        # Try different thresholds
        thresholds = [0.9, 0.7, 0.5, 0.3]
        
        for threshold in thresholds:
            results = engine.retrieve_with_threshold(
                query_embedding,
                all_embeddings,
                similarity_threshold=threshold
            )
            
            logger.info(f"Threshold {threshold}: {len(results)} results")
            for i, result in enumerate(results[:3], 1):
                logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
            if len(results) > 3:
                logger.info(f"  ... and {len(results) - 3} more")
            logger.info("")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_metadata_filtering():
    """
    Demonstrate retrieval by metadata filtering.
    
    This retrieves documents matching specific metadata criteria
    without similarity search, useful for finding all documents of a type.
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
        
        logger.info("Metadata-Based Filtering Examples:")
        logger.info("=" * 60)
        
        # Example 1: Get all runbooks
        logger.info("\nExample 1: Get all runbooks")
        runbooks = engine.retrieve_by_metadata(
            all_embeddings,
            {'document_type': 'runbook'}
        )
        logger.info(f"Found {len(runbooks)} runbooks:")
        for result in runbooks[:5]:
            logger.info(f"  - {result['source']}")
        
        # Example 2: Get best practices for specific service type
        logger.info("\nExample 2: Get best practices for api_gateway")
        api_practices = engine.retrieve_by_metadata(
            all_embeddings,
            {
                'document_type': 'best_practice',
                'service_type': 'api_gateway'
            }
        )
        logger.info(f"Found {len(api_practices)} best practices for api_gateway:")
        for result in api_practices[:5]:
            logger.info(f"  - {result['source']}")
        
        # Example 3: Get all best practices
        logger.info("\nExample 3: Get all best practices")
        all_practices = engine.retrieve_by_metadata(
            all_embeddings,
            {'document_type': 'best_practice'}
        )
        logger.info(f"Found {len(all_practices)} best practices total")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_diverse_retrieval():
    """
    Demonstrate diverse result retrieval.
    
    This retrieves results that are both relevant to the query
    and diverse from each other, avoiding redundant results.
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
        
        logger.info("Diverse Result Retrieval Examples:")
        logger.info("=" * 60)
        
        # Generate query embedding
        query_text = "SLO recommendations for microservices"
        query_embedding = engine.generate_embedding(query_text)
        
        logger.info(f"Query: {query_text}\n")
        
        # Compare pure relevance vs diverse results
        logger.info("Pure Relevance (top-5):")
        pure_results = engine.search_embeddings(
            query_embedding,
            all_embeddings,
            top_k=5
        )
        for i, result in enumerate(pure_results, 1):
            logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
        
        logger.info("\nDiverse Results (top-5 with diversity):")
        diverse_results = engine.retrieve_diverse_results(
            query_embedding,
            all_embeddings,
            top_k=5,
            diversity_factor=0.3
        )
        for i, result in enumerate(diverse_results, 1):
            logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
        
        # Show diversity factor impact
        logger.info("\nDiversity Factor Impact:")
        for diversity_factor in [0.0, 0.3, 0.6, 0.9]:
            results = engine.retrieve_diverse_results(
                query_embedding,
                all_embeddings,
                top_k=3,
                diversity_factor=diversity_factor
            )
            logger.info(f"  Factor {diversity_factor}: {len(results)} results")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_multi_source_retrieval():
    """
    Demonstrate multi-source retrieval.
    
    This retrieves top-k results from each knowledge source separately,
    ensuring diverse knowledge sources in the results.
    """
    
    engine = RAGEngine()
    
    # Load embeddings
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        return
    
    try:
        embeddings_data = engine.load_embeddings(str(embeddings_file))
        
        logger.info("Multi-Source Retrieval Examples:")
        logger.info("=" * 60)
        
        # Generate query embedding
        query_text = "Database SLO recommendations and best practices"
        query_embedding = engine.generate_embedding(query_text)
        
        logger.info(f"Query: {query_text}\n")
        
        # Retrieve from multiple sources
        multi_results = engine.retrieve_multi_source(
            query_embedding,
            embeddings_data,
            top_k_per_source=3
        )
        
        # Display results by source
        for source_name, results in multi_results.items():
            logger.info(f"\n{source_name.upper()} ({len(results)} results):")
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
                logger.info(f"     {result['content'][:60]}...")
        
        # Summary
        total_results = sum(len(results) for results in multi_results.values())
        logger.info(f"\nTotal results from all sources: {total_results}")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_combined_retrieval_strategy():
    """
    Demonstrate a combined retrieval strategy.
    
    This shows how to combine multiple retrieval techniques:
    1. Get diverse results for relevance
    2. Filter by metadata for specific types
    3. Apply threshold for quality
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
        
        logger.info("Combined Retrieval Strategy:")
        logger.info("=" * 60)
        
        # Scenario: Get best practices for API gateway with high confidence
        logger.info("\nScenario: Find best practices for API gateway\n")
        
        # Step 1: Get best practices by metadata
        logger.info("Step 1: Filter by metadata (best_practice + api_gateway)")
        api_practices = engine.retrieve_by_metadata(
            all_embeddings,
            {
                'document_type': 'best_practice',
                'service_type': 'api_gateway'
            }
        )
        logger.info(f"  Found {len(api_practices)} best practices")
        
        # Step 2: Get diverse runbooks for API gateway
        logger.info("\nStep 2: Get diverse runbooks for API gateway")
        query_embedding = engine.generate_embedding("API gateway SLO recommendations")
        runbooks = engine.retrieve_by_metadata(
            all_embeddings,
            {'document_type': 'runbook'}
        )
        
        # Filter runbooks by similarity to query
        relevant_runbooks = engine.retrieve_with_threshold(
            query_embedding,
            runbooks,
            similarity_threshold=0.5
        )
        logger.info(f"  Found {len(relevant_runbooks)} relevant runbooks")
        
        # Step 3: Combine results
        logger.info("\nStep 3: Combine results")
        combined = api_practices + relevant_runbooks[:3]
        logger.info(f"  Total combined results: {len(combined)}")
        
        logger.info("\nFinal Results:")
        for i, result in enumerate(combined[:5], 1):
            logger.info(f"  {i}. [{result['score']:.4f}] {result['source']}")
            logger.info(f"     Type: {result['metadata'].get('document_type', 'N/A')}")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


def demonstrate_retrieval_performance():
    """
    Demonstrate retrieval performance characteristics.
    
    Shows how different retrieval strategies perform with various parameters.
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
        
        logger.info("Retrieval Performance Characteristics:")
        logger.info("=" * 60)
        
        query_embedding = engine.generate_embedding("SLO recommendations")
        
        logger.info(f"\nDatabase size: {len(all_embeddings)} documents\n")
        
        # Test different top_k values
        logger.info("Top-K Retrieval Performance:")
        for k in [1, 5, 10, 20]:
            results = engine.search_embeddings(query_embedding, all_embeddings, top_k=k)
            logger.info(f"  top_k={k}: {len(results)} results retrieved")
        
        # Test different thresholds
        logger.info("\nThreshold Retrieval Performance:")
        for threshold in [0.9, 0.7, 0.5, 0.3]:
            results = engine.retrieve_with_threshold(
                query_embedding,
                all_embeddings,
                similarity_threshold=threshold
            )
            logger.info(f"  threshold={threshold}: {len(results)} results retrieved")
        
        # Test diversity factors
        logger.info("\nDiversity Retrieval Performance:")
        for diversity_factor in [0.0, 0.3, 0.6, 0.9]:
            results = engine.retrieve_diverse_results(
                query_embedding,
                all_embeddings,
                top_k=5,
                diversity_factor=diversity_factor
            )
            logger.info(f"  diversity={diversity_factor}: {len(results)} results retrieved")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


if __name__ == '__main__':
    # Example 1: Threshold retrieval
    logger.info("=" * 60)
    logger.info("Example 1: Threshold-Based Retrieval")
    logger.info("=" * 60)
    demonstrate_threshold_retrieval()
    
    # Example 2: Metadata filtering
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Metadata-Based Filtering")
    logger.info("=" * 60)
    demonstrate_metadata_filtering()
    
    # Example 3: Diverse retrieval
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Diverse Result Retrieval")
    logger.info("=" * 60)
    demonstrate_diverse_retrieval()
    
    # Example 4: Multi-source retrieval
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Multi-Source Retrieval")
    logger.info("=" * 60)
    demonstrate_multi_source_retrieval()
    
    # Example 5: Combined strategy
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Combined Retrieval Strategy")
    logger.info("=" * 60)
    demonstrate_combined_retrieval_strategy()
    
    # Example 6: Performance characteristics
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Retrieval Performance")
    logger.info("=" * 60)
    demonstrate_retrieval_performance()
