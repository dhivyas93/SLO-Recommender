#!/usr/bin/env python3
"""
Demonstration of fallback to industry standards when confidence is low.

This example shows how the recommendation engine would use industry standard
SLOs as a fallback when:
1. Confidence score is low (< 0.5)
2. Data is insufficient
3. Historical metrics are unreliable

Usage:
    python examples/fallback_demonstration.py
"""

from src.engines.recommendation_engine import RecommendationEngine


def demonstrate_fallback_mechanism():
    """
    Demonstrate the fallback to industry standards mechanism.
    
    In a real implementation, this would be integrated into the main
    recommendation generation workflow where:
    1. Compute confidence score
    2. If confidence < 0.5, use industry standards as fallback
    3. Include explanation that fallback was used
    """
    engine = RecommendationEngine()
    
    print("=" * 70)
    print("FALLBACK TO INDUSTRY STANDARDS DEMONSTRATION")
    print("=" * 70)
    
    # Scenario 1: Low confidence for a new API service
    print("\n📊 Scenario 1: New API Gateway Service (Low Confidence)")
    print("-" * 70)
    print("Context:")
    print("  - Service just deployed, only 2 days of metrics")
    print("  - Data completeness: 30%")
    print("  - Computed confidence score: 0.42 (< 0.5 threshold)")
    print("\nDecision: Use industry standard fallback")
    
    api_fallback = engine.get_industry_standard_recommendations("api_gateway")
    print("\nFallback Recommendations (API Gateway Standards):")
    print(f"  ✓ Availability: {api_fallback['availability']}%")
    print(f"  ✓ Latency p95: {api_fallback['latency_p95_ms']}ms")
    print(f"  ✓ Latency p99: {api_fallback['latency_p99_ms']}ms")
    print(f"  ✓ Error Rate: {api_fallback['error_rate_percent']}%")
    print("\nExplanation:")
    print("  'Using industry standard SLOs due to insufficient historical data.")
    print("   Confidence score (0.42) is below threshold (0.5). These standards")
    print("   are based on typical API gateway performance in production systems.'")
    
    # Scenario 2: Database service with insufficient data
    print("\n\n📊 Scenario 2: Database Service (Insufficient Data)")
    print("-" * 70)
    print("Context:")
    print("  - Database migrated from different infrastructure")
    print("  - Historical metrics not representative")
    print("  - Computed confidence score: 0.38 (< 0.5 threshold)")
    print("\nDecision: Use industry standard fallback")
    
    db_fallback = engine.get_industry_standard_recommendations("database")
    print("\nFallback Recommendations (Database Standards):")
    print(f"  ✓ Availability: {db_fallback['availability']}%")
    print(f"  ✓ Latency p95: {db_fallback['latency_p95_ms']}ms")
    print(f"  ✓ Latency p99: {db_fallback['latency_p99_ms']}ms")
    print(f"  ✓ Error Rate: {db_fallback['error_rate_percent']}%")
    print("\nExplanation:")
    print("  'Using industry standard SLOs due to infrastructure migration.")
    print("   Historical metrics may not reflect new infrastructure capabilities.")
    print("   These standards represent typical database performance expectations.'")
    
    # Scenario 3: Message queue with high variability
    print("\n\n📊 Scenario 3: Message Queue (High Variability)")
    print("-" * 70)
    print("Context:")
    print("  - High coefficient of variation in latency (CV: 0.85)")
    print("  - Unstable performance patterns")
    print("  - Computed confidence score: 0.45 (< 0.5 threshold)")
    print("\nDecision: Use industry standard fallback")
    
    queue_fallback = engine.get_industry_standard_recommendations("message_queue")
    print("\nFallback Recommendations (Message Queue Standards):")
    print(f"  ✓ Availability: {queue_fallback['availability']}%")
    print(f"  ✓ Latency p95: {queue_fallback['latency_p95_ms']}ms")
    print(f"  ✓ Latency p99: {queue_fallback['latency_p99_ms']}ms")
    print(f"  ✓ Error Rate: {queue_fallback['error_rate_percent']}%")
    print("\nExplanation:")
    print("  'Using industry standard SLOs due to high performance variability.")
    print("   Historical metrics show unstable patterns (CV: 0.85). These standards")
    print("   provide a stable baseline until performance stabilizes.'")
    
    # Scenario 4: Unknown service type
    print("\n\n📊 Scenario 4: Custom Service (Unknown Type)")
    print("-" * 70)
    print("Context:")
    print("  - Custom microservice with unique characteristics")
    print("  - Service type not in standard categories")
    print("  - Computed confidence score: 0.35 (< 0.5 threshold)")
    print("\nDecision: Use generic industry standard fallback")
    
    generic_fallback = engine.get_industry_standard_recommendations("custom_service")
    print("\nFallback Recommendations (Generic Service Standards):")
    print(f"  ✓ Availability: {generic_fallback['availability']}%")
    print(f"  ✓ Latency p95: {generic_fallback['latency_p95_ms']}ms")
    print(f"  ✓ Latency p99: {generic_fallback['latency_p99_ms']}ms")
    print(f"  ✓ Error Rate: {generic_fallback['error_rate_percent']}%")
    print("\nExplanation:")
    print("  'Using generic industry standard SLOs due to low confidence and")
    print("   unknown service type. These conservative standards provide a safe")
    print("   baseline. Consider refining as more data becomes available.'")
    
    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY: When to Use Industry Standard Fallback")
    print("=" * 70)
    print("\n✓ Confidence score < 0.5 (low confidence)")
    print("✓ Insufficient historical data (< 7 days)")
    print("✓ High performance variability (CV > 0.7)")
    print("✓ Data quality issues (completeness < 50%)")
    print("✓ Infrastructure migrations")
    print("✓ New service deployments")
    print("\nBenefits:")
    print("  • Provides reasonable SLO targets even with limited data")
    print("  • Based on industry best practices and SRE standards")
    print("  • Prevents unrealistic or unsafe recommendations")
    print("  • Gives teams a starting point to iterate from")
    print("\nNext Steps:")
    print("  • Monitor actual performance against fallback SLOs")
    print("  • Collect more historical data (30+ days recommended)")
    print("  • Re-run recommendations when confidence improves")
    print("  • Adjust SLOs based on actual service capabilities")
    print("\n" + "=" * 70)


def show_integration_example():
    """
    Show how this would be integrated into the main recommendation flow.
    """
    print("\n\n" + "=" * 70)
    print("INTEGRATION EXAMPLE: Recommendation Flow with Fallback")
    print("=" * 70)
    
    print("""
Pseudo-code for integrating fallback mechanism:

```python
def generate_recommendation(service_id, service_type="generic"):
    engine = RecommendationEngine()
    
    try:
        # Step 1: Compute confidence score
        confidence_result = engine.compute_confidence_score(service_id)
        confidence_score = confidence_result['confidence_score']
        
        # Step 2: Check if confidence is sufficient
        if confidence_score < 0.5:
            # Low confidence - use industry standard fallback
            recommendations = engine.get_industry_standard_recommendations(service_type)
            
            explanation = {
                "summary": f"Using industry standard SLOs due to low confidence ({confidence_score:.2f})",
                "fallback_used": True,
                "fallback_reason": "Confidence score below 0.5 threshold",
                "service_type": service_type,
                "recommendation_source": "industry_standards"
            }
            
            return {
                "recommendations": {
                    "aggressive": recommendations,
                    "balanced": recommendations,
                    "conservative": recommendations
                },
                "confidence_score": confidence_score,
                "explanation": explanation,
                "fallback_used": True
            }
        
        else:
            # High confidence - use data-driven recommendations
            base_recs = engine.compute_base_recommendations(service_id)
            # ... continue with normal flow
            
    except ValueError as e:
        # Insufficient data - use fallback
        recommendations = engine.get_industry_standard_recommendations(service_type)
        
        explanation = {
            "summary": f"Using industry standard SLOs due to insufficient data",
            "fallback_used": True,
            "fallback_reason": str(e),
            "service_type": service_type,
            "recommendation_source": "industry_standards"
        }
        
        return {
            "recommendations": {
                "aggressive": recommendations,
                "balanced": recommendations,
                "conservative": recommendations
            },
            "confidence_score": 0.0,
            "explanation": explanation,
            "fallback_used": True
        }
```

Key Integration Points:
1. Check confidence score after computation
2. Use fallback if confidence < 0.5
3. Handle exceptions (insufficient data) with fallback
4. Include clear explanation that fallback was used
5. Provide same recommendation structure for consistency
    """)
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_fallback_mechanism()
    show_integration_example()
