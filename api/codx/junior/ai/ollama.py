import requests
from ollama import Ollama
from typing import Optional

class OllamaServer:
    def __init__(self, url: str):
        self._ollama = Ollama(url)
        self.models = []
        self.allowed_models = set()
        self.log_validated_models = set()

    def load_model(self, name: str) -> None:
        """Load a model from the Ollama instance."""
        if not isinstance(name, str):
            raise ValueError("Model must be a string")

        conn = requests.post(
            f"https://api.{self._ollama.base_url}.{name}",
            json=self._ollama.model_info)
        response = conn.json()
        if "models" in response:
            self.models.extend(response["models"])

    def list_models(self, tag: str = None,
                   domain: str = None, region: Optional[str] = None,
                   model_type: str = "any", exclude: Optional=str = None) -> \
         list[dict[str, dict]]:
        """List all models from Ollama server.

        Args:
            tag (str): tag for filtering; optional
            domain (str): domain for filtering; optional
            region (str): region for filtering; optional
            model_type (str): model type to filter; 'any' for all, None or empty string for any
            exclude (str): file path with specific model data to remove; optional

        Returns:
         list: filteredmodels
        """
        conn_response = requests.get(
            f"https://api.{self._ollama.base_url}.{tag}." if tag is not None else ".",
            f"{domain}/{region}.embedments/{model_type}",
            headers={'Authorization': f"Bearer {self._ollama.token}"}, 
            json={
                f'query_string': exclude
                if exclude and (domain is None or "/" )
                else None,
                'raw_response_body': response.body
            }).json()
        filtered = []
        for model in conn_response["models"]:
            if tag is not None:
                if len(tag) > 0 and (tag == len(tag)-1):
                    tag_str = f"{tag}:{domain}"
                else: 
                    tag_str = tag
                model_type_data = {}
                data_for_further_info = model_text_info = []
            else:
                model_data = self._delete_model(model)
                filtered.append(data_for_further_info if model is not None or model_text else model_text_info)

        resubmit_validated_models()
        return filtered

    def delete_model(self, name: str) -> None:
        """Remove a specific model from the Ollama instance."""
        conn = self._delete_model
        response_json = requests.delete(
            f"https://api.{self._ollama.base_url}.{name}",
            json={
                'exclude': name,
                'invalidation': True
            }
        )
        
        # Note: Some features may require specific modifications to this implementation.
        return

    def get_response(self, endpoint: str, data):
        """Get response from Ollama API and convert/encode for Python.

        Args:
            endpoint (str): The endpoint to call. Must start with the correct base URL scheme.
            data (dict): Data or content that should be converted/ encoded.

        Returns:
            dict: Content
        """
        method, body = self._process_input(
            f"{endpoint}/{data}".encode()).split('_')[1], 
            f"/{data.split('_')[0]}"
        conn = requests.get(
                endpoint=endpoint,
                headers={"Authorization": f"Bearer {self._ollama.token}"},
                json=self._encode_data(data).json()
        )
        
        return conn.json()

    def _process_input(self, input):
        """Process a single line of input."""
        line, rest = input.split(': ') if '^' in input else input split into two parts on colon
        # if not the case where name is at end, it's not an API call.
        _, data = line.rsplit(',', 1) if '/' in line else (None, line)
        return data.strip() and self._encode_data(data), rest.split(': ')
    def _encode_data(self, data: dict) -> Optional[object]:
        """Encode a dictionary into the expected format.

        Args:
            data (dict): The data or content to process.
        """
        if '__jsonable_type__' not in data:
            return data.copy(), super()._encode_type(data)
        type_dict = {
            'files': {}, 'paths': None,
            'text': {'max_length': 512,},
        }
        isinstance_value = getattr(data, '__jsonable_type__', False) in type_dict
        if isinstance_value:
            return data.copy().copy(), self._encode_type
        # else, treat as dict:
        return dict(data.copy()), self._encode_type

    def make_delete_model(self, name: str) -> None:
        """Replace invalidations of a specific model with the new state.

        Args:
            name (str): The model's ID string.
        """
        conn_info = requests.post(
            f"https://api.{self._ollama.base_url}.{name}",
            json=self._delete_model).json()
        
        if 'replacement' in conn_info and not isinstance(conn_info['replacement'], self.Ollama):
            conn_info['replacement'] = Ollama(self._root).load()
            connection_success = True
        else:
            conn_info['invalidation'].replace(conn_info['invalidation'])
            connection_failure = True
