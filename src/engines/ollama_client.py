"""
Ollama LLM Client for Local LLM Integration

This module provides HTTP client integration with Ollama for local LLM-powered
reasoning and explanation generation. Ollama runs locally and provides access to
open-source models like Llama 3.2 3B Instruct.

Technology:
- Ollama: Local LLM server (free, open-source)
- Model: Llama 3.2 3B Instruct (3B parameters, ~2GB model)
- API: HTTP REST API on localhost:11434
- Cost: $0 (runs locally)
"""

import json
import logging
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for Ollama client."""
    
    endpoint: str = "http://localhost:11434"
    model: str = "orca-mini"
    temperature: float = 0.3
    max_tokens: int = 300
    timeout_seconds: int = 180
    fallback_to_baseline: bool = True  # Will use statistical baseline if Ollama unavailable


class OllamaClient:
    """
    HTTP client for Ollama local LLM server.
    
    This client communicates with Ollama via HTTP REST API to generate
    LLM-powered recommendations and explanations.
    
    Features:
    - HTTP API communication with Ollama
    - Structured JSON output parsing
    - Timeout and error handling
    - Fallback to statistical baseline on failure
    - Comprehensive logging
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialize Ollama client.
        
        Args:
            config: OllamaConfig instance (uses defaults if None)
        """
        self.config = config or OllamaConfig()
        logger.info(f"OllamaClient initialized")
        logger.info(f"  Endpoint: {self.config.endpoint}")
        logger.info(f"  Model: {self.config.model}")
        logger.info(f"  Temperature: {self.config.temperature}")
        logger.info(f"  Max tokens: {self.config.max_tokens}")
        logger.info(f"  Timeout: {self.config.timeout_seconds}s")
    
    def is_available(self) -> bool:
        """
        Check if Ollama server is available.
        
        Returns:
            bool: True if Ollama is running and responding, False otherwise
        """
        try:
            response = requests.get(
                f"{self.config.endpoint}/api/tags",
                timeout=2  # Reduced timeout to 2 seconds
            )
            is_available = response.status_code == 200
            
            if is_available:
                logger.info("✓ Ollama server is available")
            else:
                logger.warning(f"✗ Ollama server returned status {response.status_code}")
            
            return is_available
        
        except requests.exceptions.Timeout:
            logger.warning(f"✗ Ollama server timeout at {self.config.endpoint}")
            return False
        
        except requests.exceptions.ConnectionError:
            logger.warning(f"✗ Cannot connect to Ollama at {self.config.endpoint}")
            logger.info("  Make sure Ollama is running: ollama serve")
            return False
        
        except Exception as e:
            logger.warning(f"✗ Error checking Ollama availability: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: The prompt to send to the model
            temperature: Optional temperature override (0-1)
            max_tokens: Optional max tokens override
            
        Returns:
            Generated text from the model
            
        Raises:
            ValueError: If prompt is empty
            requests.exceptions.RequestException: If API call fails
            Exception: If response parsing fails
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens
        
        try:
            logger.debug(f"Calling Ollama with prompt: {prompt[:100]}...")
            
            response = requests.post(
                f"{self.config.endpoint}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stream": False
                },
                timeout=self.config.timeout_seconds
            )
            
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get("response", "")
            
            if not generated_text or not generated_text.strip():
                logger.warning(f"Ollama returned empty response. Full response: {result}")
            
            logger.debug(f"Generated {len(generated_text)} characters")
            return generated_text
        
        except requests.exceptions.Timeout:
            error_msg = f"Ollama request timed out after {self.config.timeout_seconds}s"
            logger.error(error_msg)
            raise requests.exceptions.RequestException(error_msg)
        
        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to Ollama at {self.config.endpoint}"
            logger.error(error_msg)
            raise requests.exceptions.RequestException(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to generate text: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def generate_json(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON output using Ollama.
        
        Adds JSON formatting instructions to prompt and parses response.
        
        Args:
            prompt: The prompt to send to the model
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            ValueError: If prompt is empty
            json.JSONDecodeError: If response is not valid JSON
            Exception: If API call fails
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        try:
            generated_text = self.generate(prompt, temperature, max_tokens)
            
            logger.debug(f"Raw response length: {len(generated_text)}")
            logger.debug(f"Raw response (first 500 chars): {generated_text[:500]}")
            
            if not generated_text or not generated_text.strip():
                raise json.JSONDecodeError("Empty response from model", "", 0)
            
            # Try to parse JSON
            # Sometimes the model includes markdown code blocks
            json_text = generated_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]  # Remove ```json
            if json_text.startswith("```"):
                json_text = json_text[3:]  # Remove ```
            if json_text.endswith("```"):
                json_text = json_text[:-3]  # Remove ```
            
            json_text = json_text.strip()
            
            if not json_text:
                raise json.JSONDecodeError("Empty JSON after stripping", "", 0)
            
            parsed_json = json.loads(json_text)
            
            logger.debug(f"Parsed JSON with {len(parsed_json)} keys")
            return parsed_json
        
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Response was: {generated_text[:500]}")
            
            # Try to extract JSON from response if it contains other text
            import re
            json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
            if json_match:
                try:
                    logger.info("Attempting to extract JSON from response")
                    parsed_json = json.loads(json_match.group())
                    logger.info("Successfully extracted JSON")
                    return parsed_json
                except:
                    pass
            
            raise json.JSONDecodeError(error_msg, generated_text, 0)
        
        except Exception as e:
            error_msg = f"Failed to generate JSON: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def refine_recommendation(
        self,
        service_id: str,
        statistical_baseline: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine statistical recommendation using LLM.
        
        This is the main method for AI-powered recommendation refinement.
        Takes statistical baseline and context, returns refined recommendation.
        
        Args:
            service_id: Service identifier
            statistical_baseline: Statistical baseline recommendations
            context: Additional context (metrics, dependencies, etc.)
            
        Returns:
            Refined recommendation with LLM insights
            
        Raises:
            Exception: If refinement fails
        """
        try:
            # Build prompt with context
            prompt = self._build_refinement_prompt(
                service_id,
                statistical_baseline,
                context
            )
            
            logger.info(f"Refining recommendation for {service_id}")
            
            # Generate JSON response
            refined = self.generate_json(prompt)
            
            logger.info(f"✓ Refined recommendation for {service_id}")
            return refined
        
        except Exception as e:
            error_msg = f"Failed to refine recommendation: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _build_refinement_prompt(
        self,
        service_id: str,
        statistical_baseline: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt for recommendation refinement.
        
        Args:
            service_id: Service identifier
            statistical_baseline: Statistical baseline recommendations
            context: Additional context
            
        Returns:
            Formatted prompt for LLM
        """
        avail = statistical_baseline.get('availability', 99.5)
        latency = statistical_baseline.get('latency_p95_ms', 200)
        error = statistical_baseline.get('error_rate', 0.5)
        
        # Simplified prompt that forces JSON output
        prompt = f"""Generate SLO recommendations for {service_id}. Baseline: {avail}% availability, {latency}ms latency, {error}% error rate.

Return ONLY this JSON structure, nothing else:
{{"recommendations": {{"aggressive": {{"availability": {avail + 0.3}, "latency_p95_ms": {int(latency * 0.75)}, "error_rate": {error * 0.5}}}, "balanced": {{"availability": {avail}, "latency_p95_ms": {latency}, "error_rate": {error}}}, "conservative": {{"availability": {avail - 0.5}, "latency_p95_ms": {int(latency * 1.5)}, "error_rate": {error * 2}}}}}, "recommended_tier": "balanced", "reasoning": "SLO recommendation"}}"""
        
        return prompt
    
    def _format_similar_services(self, similar_services: list) -> str:
        """Format similar services for prompt."""
        if not similar_services:
            return "No similar services found"
        
        formatted = []
        for service in similar_services[:3]:  # Limit to top 3
            formatted.append(
                f"- {service.get('service_id', 'unknown')}: "
                f"{service.get('availability', 'N/A')}% availability, "
                f"{service.get('latency_p95_ms', 'N/A')}ms latency"
            )
        
        return "\n".join(formatted)
    
    def generate_explanation(
        self,
        service_id: str,
        recommendation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate natural language explanation for recommendation.
        
        Args:
            service_id: Service identifier
            recommendation: The recommendation to explain
            context: Additional context
            
        Returns:
            Natural language explanation
            
        Raises:
            Exception: If generation fails
        """
        try:
            prompt = f"""Generate a clear, concise explanation for this SLO recommendation.

SERVICE: {service_id}
RECOMMENDATION:
- Availability: {recommendation.get('availability', 'N/A')}%
- Latency p95: {recommendation.get('latency_p95_ms', 'N/A')}ms
- Error Rate: {recommendation.get('error_rate', 'N/A')}%

CONTEXT:
- Service Type: {context.get('service_type', 'generic')}
- Key Dependencies: {', '.join(context.get('dependencies', []))}
- Infrastructure: {', '.join(context.get('infrastructure', []))}

Provide a 2-3 sentence explanation that:
1. Explains why these SLO targets are appropriate
2. Mentions key constraints or considerations
3. Suggests next steps for implementation"""
            
            explanation = self.generate(prompt)
            logger.info(f"Generated explanation for {service_id}")
            return explanation
        
        except Exception as e:
            error_msg = f"Failed to generate explanation: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
