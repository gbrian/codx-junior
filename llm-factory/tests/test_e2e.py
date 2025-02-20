import unittest
import requests
import os

# Base URL for the LLM Factory API
LLM_FACTORY_BASE_URL = "http://localhost:8754"

class TestEndToEnd(unittest.TestCase):
    """Test suite for end-to-end testing of the LLM Factory API."""

    def test_load_ollama_model_codellama(self):
        """
        Test loading the ollama model codellama by sending a request to the API.
        Verifies that the response status is 200 and contains 'success'.
        """
        url = f"{LLM_FACTORY_BASE_URL}/api/pull"
        data = {"model": "mxbai-embed-large"}

        # Sending POST request to the API
        response = requests.post(url, json=data)

        # Asserting the response status code to be 200 (OK)
        self.assertEqual(response.status_code, 200, "Expected status code to be 200")

    def test_embeddings_request_openai_format(self):
        """
        Test embeddings request using OpenAI request format.
        Verifies that the response status is 200 and checks for expected response structure.
        """
        url = f"{LLM_FACTORY_BASE_URL}/v1/embeddings"
        data = {
            "input": "This is a test sentence for embeddings.",
            "model": "mxbai-embed-large",
            "encoding_format": "float"
        }

        # Sending POST request to the API
        response = requests.post(url, json=data)

        # Asserting the response status code to be 200 (OK)
        self.assertEqual(response.status_code, 200, "Expected status code to be 200")

        # Verifying the response content has the 'embeddings' key
        response_json = response.json()
        self.assertIn("data", response_json, "Expected 'embeddings' key in response")

    def test_chat_completion_openai_format(self):
        """
        Test chat completion using the OpenAI format.
        Verifies that the response status is 200 and checks for expected response structure.
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ]
        }

        # Sending POST request to the API
        response = requests.post(url, headers=headers, json=data)

        # Asserting the response status code to be 200 (OK)
        self.assertEqual(response.status_code, 200, "Expected status code to be 200")

        # Verifying the response content
        response_json = response.json()
        self.assertIn("choices", response_json, "Expected 'choices' key in response")

if __name__ == '__main__':
    unittest.main()