"""
Hybrid Recommendation Engine

Combines statistical baseline recommendations with AI-powered refinement
using LLM and RAG for contextual, explainable SLO recommendations.

Workflow:
1. Generate statistical baseline from historical metrics
2. Retrieve relevant knowledge via RAG
3. Refine with LLM using context and knowledge
4. Validate against safety constraints
5. Return final recommendation with explanation
"""

import logging
from typing import Dict, Any, Optional, List
from src.engines.recommendation_engine import RecommendationEngine
from src.engines.ollama_client import OllamaClient, OllamaConfig
from src.engines.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class HybridRecommendationEngine:
    """
    Hybrid engine combining statistical and AI-powered recommendations.
    
    This engine:
    1. Generates statistical baseline recommendations
    2. Retrieves relevant knowledge from knowledge base
    3. Refines recommendations using LLM
    4. Validates output against safety constraints
    5. Returns final recommendation with explanation
    """
    
    def __init__(
        self,
        recommendation_engine: Optional[RecommendationEngine] = None,
        ollama_client: Optional[OllamaClient] = None,
        rag_engine: Optional[RAGEngine] = None,
        use_ai: bool = True
    ):
        """
        Initialize hybrid recommendation engine.
        
        Args:
            recommendation_engine: Statistical recommendation engine
            ollama_client: Ollama LLM client
            rag_engine: RAG engine for knowledge retrieval
            use_ai: Whether to use AI refinement (default: True)
        """
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.ollama_client = ollama_client or OllamaClient()
        self.rag_engine = rag_engine or RAGEngine()
        self.use_ai = use_ai
        
        logger.info("HybridRecommendationEngine initialized")
        logger.info(f"  AI refinement: {'enabled' if use_ai else 'disabled'}")
    
    def generate_recommendation(
        self,
        service_id: str,
        metrics: Dict[str, Any],
        dependencies: Dict[str, Any],
        infrastructure: Dict[str, Any],
        embeddings_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate hybrid recommendation combining statistical and AI approaches.
        
        Args:
            service_id: Service identifier
            metrics: Service metrics (latency, availability, error rate)
            dependencies: Dependency information
            infrastructure: Infrastructure details
            embeddings_data: Pre-loaded embeddings for RAG (optional)
            context: Additional context (service type, team, etc.)
            
        Returns:
            Complete recommendation with statistical baseline, AI refinement,
            and explanation
            
        Raises:
            Exception: If recommendation generation fails
        """
        try:
            logger.info(f"Generating hybrid recommendation for {service_id}")
            
            # Step 1: Generate statistical baseline
            logger.debug("Step 1: Generating statistical baseline")
            baseline_result = self.recommendation_engine.compute_base_recommendations(
                service_id
            )
            statistical_baseline = baseline_result["base_recommendations"]
            
            # Step 2: Apply constraints
            logger.debug("Step 2: Applying constraints")
            constrained_result = self.recommendation_engine.apply_dependency_constraints(
                service_id,
                statistical_baseline
            )
            constrained_rec = constrained_result.get("constrained_recommendations", statistical_baseline)
            
            constrained_result2 = self.recommendation_engine.apply_infrastructure_constraints(
                service_id,
                constrained_rec
            )
            constrained_rec = constrained_result2.get("constrained_recommendations", constrained_rec)
            
            # Step 3: Generate tiers
            logger.debug("Step 3: Generating recommendation tiers")
            tiers_result = self.recommendation_engine.generate_tiers(
                service_id,
                constrained_rec
            )
            tiers = tiers_result.get("tiers", {})
            
            # Step 4: Compute confidence
            logger.debug("Step 4: Computing confidence score")
            confidence_result = self.recommendation_engine.compute_confidence_score(
                service_id
            )
            confidence = confidence_result.get("confidence_score", 0.5)
            
            # Step 5: Retrieve relevant knowledge
            logger.debug("Step 5: Retrieving relevant knowledge")
            relevant_knowledge = self._retrieve_knowledge(
                service_id,
                context or {},
                embeddings_data
            )
            
            # Step 6: AI refinement (if enabled and Ollama available)
            refined_recommendation = None
            if self.use_ai and self.ollama_client.is_available():
                logger.debug("Step 6: Refining with LLM")
                try:
                    refined_recommendation = self._refine_with_llm(
                        service_id,
                        tiers,
                        context or {},
                        relevant_knowledge
                    )
                except Exception as e:
                    logger.warning(f"LLM refinement failed, continuing without it: {e}")
                    refined_recommendation = None
            else:
                logger.debug("Step 6: Skipping LLM refinement (disabled or unavailable)")
            
            # Step 7: Validate output
            logger.debug("Step 7: Validating recommendation")
            final_recommendation = self._validate_and_merge(
                tiers,
                refined_recommendation,
                statistical_baseline
            )
            
            # Step 8: Generate explanation
            logger.debug("Step 8: Generating explanation")
            explanation = self.recommendation_engine.generate_explanation(
                service_id,
                statistical_baseline,
                constrained_rec,
                constrained_rec,  # infrastructure_constrained_recommendations
                constrained_result.get("metadata", {}),  # dependency_metadata
                constrained_result2.get("metadata", {}),  # infrastructure_metadata
                confidence
            )
            
            # Step 9: Compile final result
            result = {
                "service_id": service_id,
                "recommendation": final_recommendation,
                "tiers": tiers,
                "confidence_score": confidence,
                "explanation": explanation,
                "statistical_baseline": statistical_baseline,
                "refined_by_ai": refined_recommendation is not None,
                "relevant_knowledge_count": len(relevant_knowledge)
            }
            
            logger.info(f"✓ Generated hybrid recommendation for {service_id}")
            return result
        
        except Exception as e:
            error_msg = f"Failed to generate hybrid recommendation: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _retrieve_knowledge(
        self,
        service_id: str,
        context: Dict[str, Any],
        embeddings_data: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge from knowledge base.
        
        Args:
            service_id: Service identifier
            context: Service context
            embeddings_data: Pre-loaded embeddings (optional)
            
        Returns:
            List of relevant knowledge documents
        """
        try:
            if not embeddings_data:
                logger.debug("No embeddings data provided, skipping knowledge retrieval")
                return []
            
            # Generate query based on service type
            service_type = context.get('service_type', 'generic')
            query = f"SLO recommendations for {service_type} services"
            
            # Search for relevant documents
            query_embedding = self.rag_engine.generate_embedding(query)
            
            # Combine all embeddings
            all_embeddings = (
                embeddings_data.get('runbooks', []) +
                embeddings_data.get('best_practices', []) +
                embeddings_data.get('historical', [])
            )
            
            # Retrieve diverse results
            results = self.rag_engine.retrieve_diverse_results(
                query_embedding,
                all_embeddings,
                top_k=5,
                diversity_factor=0.3
            )
            
            logger.debug(f"Retrieved {len(results)} relevant knowledge documents")
            return results
        
        except Exception as e:
            logger.warning(f"Failed to retrieve knowledge: {e}")
            return []
    
    def _refine_with_llm(
        self,
        service_id: str,
        tiers: Dict[str, Any],
        context: Dict[str, Any],
        relevant_knowledge: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Refine recommendation using LLM.
        
        Args:
            service_id: Service identifier
            tiers: Recommendation tiers from statistical engine
            context: Service context
            relevant_knowledge: Retrieved knowledge documents
            
        Returns:
            LLM-refined recommendation or None if refinement fails
        """
        try:
            # Build context for LLM
            llm_context = {
                'service_type': context.get('service_type', 'generic'),
                'team': context.get('team', 'unknown'),
                'criticality': context.get('criticality', 'medium'),
                'upstream_services': context.get('upstream_services', []),
                'downstream_services': context.get('downstream_services', []),
                'critical_path': context.get('critical_path', []),
                'datastores': context.get('datastores', []),
                'caches': context.get('caches', []),
                'similar_services': context.get('similar_services', [])
            }
            
            # Refine with LLM
            refined = self.ollama_client.refine_recommendation(
                service_id,
                tiers['balanced'],
                llm_context
            )
            
            logger.debug(f"LLM refinement completed for {service_id}")
            return refined
        
        except Exception as e:
            logger.warning(f"LLM refinement failed: {e}")
            return None
    
    def _validate_and_merge(
        self,
        statistical_tiers: Dict[str, Any],
        refined_recommendation: Optional[Dict[str, Any]],
        statistical_baseline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and merge statistical and AI recommendations.
        
        Args:
            statistical_tiers: Statistical recommendation tiers
            refined_recommendation: LLM-refined recommendation (optional)
            statistical_baseline: Statistical baseline for validation
            
        Returns:
            Final validated recommendation
        """
        try:
            # If no AI refinement, use statistical balanced tier
            if not refined_recommendation:
                return statistical_tiers['balanced']
            
            # If AI refinement failed or returned fallback, use statistical
            if refined_recommendation.get('fallback'):
                logger.debug("Using statistical baseline due to LLM fallback")
                return statistical_tiers['balanced']
            
            # Validate LLM output
            llm_rec = refined_recommendation.get('recommendations', {}).get('balanced')
            if not llm_rec:
                logger.debug("Invalid LLM output, using statistical baseline")
                return statistical_tiers['balanced']
            
            # Check if LLM recommendation is reasonable
            if self._is_reasonable_recommendation(llm_rec, statistical_baseline):
                logger.debug("LLM recommendation validated")
                return llm_rec
            else:
                logger.debug("LLM recommendation failed validation, using statistical")
                return statistical_tiers['balanced']
        
        except Exception as e:
            logger.warning(f"Validation failed: {e}, using statistical baseline")
            return statistical_tiers['balanced']
    
    def _is_reasonable_recommendation(
        self,
        recommendation: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> bool:
        """
        Check if recommendation is reasonable compared to baseline.
        
        Args:
            recommendation: Recommendation to validate
            baseline: Statistical baseline for comparison
            
        Returns:
            True if recommendation is reasonable, False otherwise
        """
        try:
            # Check availability
            rec_avail = recommendation.get('availability', 0)
            base_avail = baseline.get('availability', 0)
            if rec_avail > base_avail + 1:  # Can't exceed baseline by more than 1%
                logger.debug(f"Availability too high: {rec_avail}% vs {base_avail}%")
                return False
            
            # Check latency
            rec_latency = recommendation.get('latency_p95_ms', 0)
            base_latency = baseline.get('latency_p95_ms', 0)
            if rec_latency < base_latency * 0.8:  # Can't be 20% better than baseline
                logger.debug(f"Latency too good: {rec_latency}ms vs {base_latency}ms")
                return False
            
            # Check error rate
            rec_error = recommendation.get('error_rate', 0)
            base_error = baseline.get('error_rate', 0)
            if rec_error < base_error * 0.5:  # Can't be 50% better than baseline
                logger.debug(f"Error rate too good: {rec_error}% vs {base_error}%")
                return False
            
            return True
        
        except Exception as e:
            logger.warning(f"Validation check failed: {e}")
            return False
