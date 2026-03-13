"""
Example: Hybrid Recommendation Engine

This example demonstrates the complete hybrid recommendation workflow:
1. Generate statistical baseline from metrics
2. Retrieve relevant knowledge from knowledge base
3. Refine with LLM using context and knowledge
4. Validate against safety constraints
5. Return final recommendation with explanation

This combines the best of both statistical analysis and AI reasoning.
"""

import json
import logging
from pathlib import Path
from src.engines.hybrid_recommendation_engine import HybridRecommendationEngine
from src.engines.recommendation_engine import RecommendationEngine
from src.engines.ollama_client import OllamaClient, OllamaConfig
from src.engines.rag_engine import RAGEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demonstrate_hybrid_recommendation():
    """
    Demonstrate hybrid recommendation generation.
    """
    
    logger.info("=" * 60)
    logger.info("Hybrid Recommendation Engine Example")
    logger.info("=" * 60)
    
    # Initialize engines
    logger.info("\nInitializing engines...")
    recommendation_engine = RecommendationEngine()
    ollama_client = OllamaClient()
    rag_engine = RAGEngine()
    
    hybrid_engine = HybridRecommendationEngine(
        recommendation_engine=recommendation_engine,
        ollama_client=ollama_client,
        rag_engine=rag_engine,
        use_ai=True
    )
    
    # Check Ollama availability
    logger.info("\nChecking Ollama availability...")
    if ollama_client.is_available():
        logger.info("✓ Ollama is available - AI refinement will be used")
    else:
        logger.info("✗ Ollama is not available - using statistical baseline only")
        logger.info("  To enable AI refinement, start Ollama: ollama serve")
    
    # Load embeddings for RAG
    logger.info("\nLoading embeddings for RAG...")
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    embeddings_data = None
    
    if embeddings_file.exists():
        try:
            embeddings_data = rag_engine.load_embeddings(str(embeddings_file))
            logger.info(f"✓ Loaded embeddings: {embeddings_data['metadata']['total_documents']} documents")
        except Exception as e:
            logger.warning(f"Failed to load embeddings: {e}")
    else:
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        logger.info("  Run: python scripts/generate_knowledge_base_embeddings.py")
    
    # Example 1: API Gateway Service
    logger.info("\n" + "=" * 60)
    logger.info("Example 1: API Gateway Service")
    logger.info("=" * 60)
    
    api_gateway_metrics = {
        'latency_p50': 30,
        'latency_p95': 80,
        'latency_p99': 150,
        'error_rate': 0.2,
        'availability': 99.92
    }
    
    api_gateway_dependencies = {
        'upstream_services': [],
        'downstream_services': ['auth-service', 'user-service', 'payment-service'],
        'critical_path': ['api-gateway', 'auth-service', 'user-db'],
        'critical_path_latency': 200
    }
    
    api_gateway_infrastructure = {
        'datastores': [],
        'caches': ['redis-cache'],
        'network_latency_ms': 5
    }
    
    api_gateway_context = {
        'service_type': 'api_gateway',
        'team': 'platform',
        'criticality': 'critical',
        'upstream_services': [],
        'downstream_services': ['auth-service', 'user-service', 'payment-service'],
        'critical_path': ['api-gateway', 'auth-service', 'user-db'],
        'datastores': [],
        'caches': ['redis-cache'],
        'similar_services': [
            {'service_id': 'checkout-api', 'availability': 99.9, 'latency_p95_ms': 120}
        ]
    }
    
    try:
        recommendation = hybrid_engine.generate_recommendation(
            service_id='api-gateway',
            metrics=api_gateway_metrics,
            dependencies=api_gateway_dependencies,
            infrastructure=api_gateway_infrastructure,
            embeddings_data=embeddings_data,
            context=api_gateway_context
        )
        
        logger.info("\nRecommendation Generated:")
        logger.info(f"  Service: {recommendation['service_id']}")
        logger.info(f"  Confidence: {recommendation['confidence_score']:.2f}")
        logger.info(f"  AI Refined: {recommendation['refined_by_ai']}")
        logger.info(f"  Knowledge Used: {recommendation['relevant_knowledge_count']} documents")
        
        logger.info("\nRecommended SLOs (Balanced Tier):")
        rec = recommendation['recommendation']
        logger.info(f"  Availability: {rec.get('availability', 'N/A')}%")
        logger.info(f"  Latency p95: {rec.get('latency_p95_ms', 'N/A')}ms")
        logger.info(f"  Latency p99: {rec.get('latency_p99_ms', 'N/A')}ms")
        logger.info(f"  Error Rate: {rec.get('error_rate', 'N/A')}%")
        
        logger.info("\nExplanation:")
        logger.info(f"  {recommendation['explanation']['summary']}")
        
        logger.info("\nTop Factors:")
        for i, factor in enumerate(recommendation['explanation'].get('top_factors', [])[:3], 1):
            logger.info(f"  {i}. {factor}")
    
    except Exception as e:
        logger.error(f"Failed to generate recommendation: {e}")
    
    # Example 2: Database Service
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Database Service")
    logger.info("=" * 60)
    
    database_metrics = {
        'latency_p50': 5,
        'latency_p95': 15,
        'latency_p99': 50,
        'error_rate': 0.05,
        'availability': 99.98
    }
    
    database_dependencies = {
        'upstream_services': ['api-gateway', 'batch-processor'],
        'downstream_services': [],
        'critical_path': [],
        'critical_path_latency': 0
    }
    
    database_infrastructure = {
        'datastores': ['postgresql'],
        'caches': [],
        'network_latency_ms': 2
    }
    
    database_context = {
        'service_type': 'database',
        'team': 'data',
        'criticality': 'critical',
        'upstream_services': ['api-gateway', 'batch-processor'],
        'downstream_services': [],
        'critical_path': [],
        'datastores': ['postgresql'],
        'caches': [],
        'similar_services': [
            {'service_id': 'user-db', 'availability': 99.95, 'latency_p95_ms': 20}
        ]
    }
    
    try:
        recommendation = hybrid_engine.generate_recommendation(
            service_id='user-db',
            metrics=database_metrics,
            dependencies=database_dependencies,
            infrastructure=database_infrastructure,
            embeddings_data=embeddings_data,
            context=database_context
        )
        
        logger.info("\nRecommendation Generated:")
        logger.info(f"  Service: {recommendation['service_id']}")
        logger.info(f"  Confidence: {recommendation['confidence_score']:.2f}")
        logger.info(f"  AI Refined: {recommendation['refined_by_ai']}")
        
        logger.info("\nRecommended SLOs (Balanced Tier):")
        rec = recommendation['recommendation']
        logger.info(f"  Availability: {rec.get('availability', 'N/A')}%")
        logger.info(f"  Latency p95: {rec.get('latency_p95_ms', 'N/A')}ms")
        logger.info(f"  Latency p99: {rec.get('latency_p99_ms', 'N/A')}ms")
        logger.info(f"  Error Rate: {rec.get('error_rate', 'N/A')}%")
    
    except Exception as e:
        logger.error(f"Failed to generate recommendation: {e}")
    
    # Example 3: Message Queue Service
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Message Queue Service")
    logger.info("=" * 60)
    
    queue_metrics = {
        'latency_p50': 20,
        'latency_p95': 50,
        'latency_p99': 200,
        'error_rate': 0.1,
        'availability': 99.91
    }
    
    queue_dependencies = {
        'upstream_services': ['api-gateway', 'batch-processor'],
        'downstream_services': ['notification-service', 'analytics-service'],
        'critical_path': [],
        'critical_path_latency': 0
    }
    
    queue_infrastructure = {
        'datastores': [],
        'caches': [],
        'network_latency_ms': 5
    }
    
    queue_context = {
        'service_type': 'message_queue',
        'team': 'platform',
        'criticality': 'high',
        'upstream_services': ['api-gateway', 'batch-processor'],
        'downstream_services': ['notification-service', 'analytics-service'],
        'critical_path': [],
        'datastores': [],
        'caches': [],
        'similar_services': [
            {'service_id': 'event-queue', 'availability': 99.9, 'latency_p95_ms': 100}
        ]
    }
    
    try:
        recommendation = hybrid_engine.generate_recommendation(
            service_id='event-queue',
            metrics=queue_metrics,
            dependencies=queue_dependencies,
            infrastructure=queue_infrastructure,
            embeddings_data=embeddings_data,
            context=queue_context
        )
        
        logger.info("\nRecommendation Generated:")
        logger.info(f"  Service: {recommendation['service_id']}")
        logger.info(f"  Confidence: {recommendation['confidence_score']:.2f}")
        logger.info(f"  AI Refined: {recommendation['refined_by_ai']}")
        
        logger.info("\nRecommended SLOs (Balanced Tier):")
        rec = recommendation['recommendation']
        logger.info(f"  Availability: {rec.get('availability', 'N/A')}%")
        logger.info(f"  Latency p95: {rec.get('latency_p95_ms', 'N/A')}ms")
        logger.info(f"  Latency p99: {rec.get('latency_p99_ms', 'N/A')}ms")
        logger.info(f"  Error Rate: {rec.get('error_rate', 'N/A')}%")
    
    except Exception as e:
        logger.error(f"Failed to generate recommendation: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Hybrid Recommendation Examples Complete")
    logger.info("=" * 60)


def demonstrate_statistical_only():
    """
    Demonstrate statistical-only recommendations (without AI).
    """
    
    logger.info("\n" + "=" * 60)
    logger.info("Statistical-Only Recommendation Example")
    logger.info("=" * 60)
    
    # Initialize with AI disabled
    hybrid_engine = HybridRecommendationEngine(use_ai=False)
    
    metrics = {
        'latency_p50': 30,
        'latency_p95': 80,
        'latency_p99': 150,
        'error_rate': 0.2,
        'availability': 99.92
    }
    
    dependencies = {
        'upstream_services': [],
        'downstream_services': ['auth-service', 'user-service'],
        'critical_path': ['api-gateway', 'auth-service'],
        'critical_path_latency': 150
    }
    
    infrastructure = {
        'datastores': [],
        'caches': ['redis'],
        'network_latency_ms': 5
    }
    
    context = {
        'service_type': 'api_gateway',
        'team': 'platform',
        'criticality': 'critical'
    }
    
    try:
        recommendation = hybrid_engine.generate_recommendation(
            service_id='api-gateway',
            metrics=metrics,
            dependencies=dependencies,
            infrastructure=infrastructure,
            context=context
        )
        
        logger.info("\nStatistical Recommendation Generated:")
        logger.info(f"  Service: {recommendation['service_id']}")
        logger.info(f"  Confidence: {recommendation['confidence_score']:.2f}")
        logger.info(f"  AI Refined: {recommendation['refined_by_ai']}")
        
        logger.info("\nRecommended SLOs:")
        rec = recommendation['recommendation']
        logger.info(f"  Availability: {rec.get('availability', 'N/A')}%")
        logger.info(f"  Latency p95: {rec.get('latency_p95_ms', 'N/A')}ms")
    
    except Exception as e:
        logger.error(f"Failed: {e}")


if __name__ == '__main__':
    # Run hybrid recommendation examples
    demonstrate_hybrid_recommendation()
    
    # Run statistical-only example
    demonstrate_statistical_only()
