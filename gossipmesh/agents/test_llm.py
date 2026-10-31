import unittest
from unittest.mock import MagicMock, patch
import asyncio

from gossipmesh.agents.llm import LocalLlamaFallbackProvider
from gossipmesh_engine.providers.models import GenerationRequest, Message


class TestLocalLlamaFallbackProvider(unittest.TestCase):
    def setUp(self):
        self.provider = LocalLlamaFallbackProvider(model_path="dummy_path.gguf")

    def test_provider_name(self):
        self.assertEqual(self.provider.provider_name, "llama_cpp_local")

    @patch("gossipmesh.agents.llm.os.path.exists", return_value=True)
    @patch("gossipmesh.agents.llm.Llama")
    def test_generate_success(self, mock_llama_cls, mock_exists):
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = {
            "choices": [
                {"message": {"role": "assistant", "content": "Hello from local llama!"}}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_llama_cls.return_value = mock_model

        request = GenerationRequest(
            model="llama-3-8b", messages=[Message(role="user", content="Hi")]
        )

        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.provider.generate(request))

        self.assertEqual(response.content, "Hello from local llama!")
        self.assertEqual(response.usage.prompt_tokens, 10)
        self.assertEqual(response.usage.completion_tokens, 5)
        self.assertEqual(response.usage.total_tokens, 15)

    @patch("gossipmesh.agents.llm.os.path.exists", return_value=False)
    def test_health_check_missing_model(self, mock_exists):
        loop = asyncio.get_event_loop()
        health = loop.run_until_complete(self.provider.check_health())
        self.assertFalse(health.is_healthy)
        self.assertIn("Model path not found", health.error)


if __name__ == "__main__":
    unittest.main()
