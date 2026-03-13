"""
Unit tests for Ollama LLM client with mocked responses.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.engines.ollama_client import OllamaClient, OllamaConfig


@pytest.fixture
def ollama_config():
    """Create an OllamaConfig instance."""
    return OllamaConfig(
        endpoint="http://localhost:11434",
        model="llama3.2:3b-instruct-q4_0",
        timeout_seconds=10
    )


@pytest.fixture
def ollama_client(ollama_config):
    """Create an OllamaClient instance."""
    return OllamaClient(config=ollama_config)


class TestOllamaClientInitialization:
    """Test OllamaClient initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        client = OllamaClient()
        assert client.config is not None
        assert client.config.endpoint == "http://localhost:11434"
        assert client.config.model == "llama3.2:3b-instruct-q4_0"
        assert client.config.timeout_seconds == 30
    
    def test_init_with_custom_config(self, ollama_config):
        """Test initialization with custom config."""
        client = OllamaClient(config=ollama_config)
        assert client.config == ollama_config
        assert client.config.endpoint == "http://localhost:11434"
        assert client.config.model == "llama3.2:3b-instruct-q4_0"
        assert client.config.timeout_seconds == 10


class TestOllamaClientAvailability:
    """Test Ollama server availability checking."""
    
    @patch('requests.get')
    def test_is_available_success(self, mock_get, ollama_client):
        """Test successful availability check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = ollama_client.is_available()
        
        assert result == True
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_is_available_connection_error(self, mock_get, ollama_client):
        """Test availability check with connection error."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        result = ollama_client.is_available()
        
        assert result == False
    
    @patch('requests.get')
    def test_is_available_timeout(self, mock_get, ollama_client):
        """Test availability check with timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        result = ollama_client.is_available()
        
        assert result == False
    
    @patch('requests.get')
    def test_is_available_server_error(self, mock_get, ollama_client):
        """Test availability check with server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = ollama_client.is_available()
        
        assert result == False


class TestOllamaClientGenerate:
    """Test LLM generation with mocked responses."""
    
    @patch('requests.post')
    def test_generate_success(self, mock_post, ollama_client):
        """Test successful LLM generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Generated text response"
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.generate("Test prompt")
        
        assert result == "Generated text response"
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_generate_with_parameters(self, mock_post, ollama_client):
        """Test generation with custom parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Response with params"
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.generate(
            "Test prompt",
            temperature=0.5,
            max_tokens=500
        )
        
        assert result == "Response with params"
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_generate_empty_prompt(self, mock_post, ollama_client):
        """Test generation with empty prompt raises error."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            ollama_client.generate("")
    
    @patch('requests.post')
    def test_generate_timeout(self, mock_post, ollama_client):
        """Test timeout handling."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        with pytest.raises(requests.exceptions.RequestException):
            ollama_client.generate("Test prompt")
    
    @patch('requests.post')
    def test_generate_connection_error(self, mock_post, ollama_client):
        """Test connection error handling."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with pytest.raises(requests.exceptions.RequestException):
            ollama_client.generate("Test prompt")
    
    @patch('requests.post')
    def test_generate_invalid_json_response(self, mock_post, ollama_client):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception):
            ollama_client.generate("Test prompt")


class TestOllamaClientGenerateJSON:
    """Test JSON output generation and parsing."""
    
    @patch('requests.post')
    def test_generate_json_success(self, mock_post, ollama_client):
        """Test successful JSON generation."""
        json_response = {
            "recommendations": {
                "availability": 99.9,
                "latency_p95_ms": 200
            },
            "confidence": 0.85
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": json.dumps(json_response)
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.generate_json("Generate JSON")
        
        assert result["recommendations"]["availability"] == 99.9
        assert result["confidence"] == 0.85
    
    @patch('requests.post')
    def test_generate_json_with_markdown_code_blocks(self, mock_post, ollama_client):
        """Test JSON parsing with markdown code blocks."""
        json_response = {
            "recommendations": {"availability": 99.9},
            "confidence": 0.85
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": f"```json\n{json.dumps(json_response)}\n```"
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.generate_json("Generate JSON")
        
        assert result["recommendations"]["availability"] == 99.9
    
    @patch('requests.post')
    def test_generate_json_invalid_json(self, mock_post, ollama_client):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "This is not valid JSON"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(json.JSONDecodeError):
            ollama_client.generate_json("Generate JSON")
    
    @patch('requests.post')
    def test_generate_json_empty_prompt(self, mock_post, ollama_client):
        """Test JSON generation with empty prompt raises error."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            ollama_client.generate_json("")


class TestOllamaClientRefineRecommendation:
    """Test recommendation refinement workflow."""
    
    @patch('requests.post')
    def test_refine_recommendation_success(self, mock_post, ollama_client):
        """Test successful recommendation refinement."""
        refined_response = {
            "recommendations": {
                "aggressive": {"availability": 99.9, "latency_p95_ms": 150},
                "balanced": {"availability": 99.5, "latency_p95_ms": 200},
                "conservative": {"availability": 99.0, "latency_p95_ms": 300}
            },
            "recommended_tier": "balanced",
            "reasoning": {"summary": "Based on dependency analysis"},
            "confidence_score": 0.85
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": json.dumps(refined_response)
        }
        mock_post.return_value = mock_response
        
        statistical_baseline = {
            "availability": 99.5,
            "latency_p95_ms": 200,
            "latency_p99_ms": 400,
            "error_rate": 1.0
        }
        
        context = {
            "service_type": "api",
            "team": "platform",
            "criticality": "high",
            "upstream_services": ["auth-service"],
            "downstream_services": ["payment-service"],
            "critical_path": ["api", "auth", "db"]
        }
        
        result = ollama_client.refine_recommendation(
            "test-service",
            statistical_baseline,
            context
        )
        
        assert "recommendations" in result
        assert "balanced" in result["recommendations"]
        assert result["confidence_score"] == 0.85
    
    @patch('requests.post')
    def test_refine_recommendation_fallback(self, mock_post, ollama_client):
        """Test fallback to baseline on refinement failure."""
        mock_post.side_effect = Exception("LLM error")
        
        statistical_baseline = {
            "availability": 99.5,
            "latency_p95_ms": 200,
            "latency_p99_ms": 400,
            "error_rate": 1.0
        }
        
        context = {"service_type": "api"}
        
        # With fallback enabled, should return baseline
        result = ollama_client.refine_recommendation(
            "test-service",
            statistical_baseline,
            context
        )
        
        assert result["fallback"] == True
        assert result["recommendations"] == statistical_baseline


class TestOllamaClientGenerateExplanation:
    """Test explanation generation."""
    
    @patch('requests.post')
    def test_generate_explanation_success(self, mock_post, ollama_client):
        """Test successful explanation generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "This service should have 99.5% availability because it depends on auth-service which has 99.9% availability."
        }
        mock_post.return_value = mock_response
        
        recommendation = {
            "availability": 99.5,
            "latency_p95_ms": 200,
            "error_rate": 1.0
        }
        
        context = {
            "service_type": "api",
            "dependencies": ["auth-service"],
            "infrastructure": ["postgresql"]
        }
        
        result = ollama_client.generate_explanation(
            "test-service",
            recommendation,
            context
        )
        
        assert "availability" in result.lower()
        assert "auth-service" in result
    
    @patch('requests.post')
    def test_generate_explanation_error(self, mock_post, ollama_client):
        """Test explanation generation error handling."""
        mock_post.side_effect = Exception("Generation failed")
        
        recommendation = {"availability": 99.5}
        context = {"service_type": "api"}
        
        with pytest.raises(Exception):
            ollama_client.generate_explanation(
                "test-service",
                recommendation,
                context
            )


class TestOllamaClientErrorHandling:
    """Test error handling and fallback behavior."""
    
    @patch('requests.post')
    def test_generate_empty_response(self, mock_post, ollama_client):
        """Test handling of empty response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": ""
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.generate("Test prompt")
        
        assert result == ""
    
    @patch('requests.post')
    def test_generate_very_long_response(self, mock_post, ollama_client):
        """Test handling of very long responses."""
        long_response = "x" * 10000
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": long_response
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.generate("Test prompt")
        
        assert len(result) == 10000
        assert result == long_response
    
    @patch('requests.post')
    def test_generate_with_special_characters(self, mock_post, ollama_client):
        """Test handling of special characters."""
        special_response = "Response with émojis 🚀 and spëcial çharacters"
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": special_response
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.generate("Test prompt")
        
        assert result == special_response


class TestOllamaClientConfiguration:
    """Test client configuration."""
    
    def test_config_defaults(self):
        """Test default configuration."""
        config = OllamaConfig()
        assert config.endpoint == "http://localhost:11434"
        assert config.model == "llama3.2:3b-instruct-q4_0"
        assert config.timeout_seconds == 30
        assert config.temperature == 0.3
        assert config.max_tokens == 2000
    
    def test_config_custom_values(self):
        """Test custom configuration."""
        config = OllamaConfig(
            endpoint="http://custom:11434",
            model="custom-model",
            timeout_seconds=60,
            temperature=0.7,
            max_tokens=4000
        )
        assert config.endpoint == "http://custom:11434"
        assert config.model == "custom-model"
        assert config.timeout_seconds == 60
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
    
    def test_config_fallback_to_baseline(self):
        """Test fallback to baseline configuration."""
        config = OllamaConfig(fallback_to_baseline=True)
        assert config.fallback_to_baseline == True
        
        config2 = OllamaConfig(fallback_to_baseline=False)
        assert config2.fallback_to_baseline == False


class TestOllamaClientIntegration:
    """Test integration scenarios."""
    
    @patch('requests.post')
    def test_complete_recommendation_workflow(self, mock_post, ollama_client):
        """Test complete recommendation workflow."""
        # Mock the generate_json call
        refined_response = {
            "recommendations": {
                "balanced": {
                    "availability": 99.5,
                    "latency_p95_ms": 200
                }
            },
            "confidence_score": 0.85
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": json.dumps(refined_response)
        }
        mock_post.return_value = mock_response
        
        statistical_baseline = {
            "availability": 99.5,
            "latency_p95_ms": 200,
            "latency_p99_ms": 400,
            "error_rate": 1.0
        }
        
        context = {
            "service_type": "api",
            "team": "platform",
            "upstream_services": ["auth"],
            "downstream_services": ["payment"]
        }
        
        # Step 1: Refine recommendations
        refined = ollama_client.refine_recommendation(
            "test-service",
            statistical_baseline,
            context
        )
        
        assert "recommendations" in refined
        
        # Step 2: Generate explanation
        mock_response.json.return_value = {
            "response": "This service should have 99.5% availability..."
        }
        
        explanation = ollama_client.generate_explanation(
            "test-service",
            refined["recommendations"]["balanced"],
            context
        )
        
        assert explanation is not None
        assert len(explanation) > 0
