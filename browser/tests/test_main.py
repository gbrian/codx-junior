import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from browser.main import browse  # Import the browse function from main.py

class MockedLLM:
    # Mock class to simulate ChatOpenAI
    def __init__(self, **kwargs):
        pass

@pytest.mark.asyncio
async def test_browse_success():
    payload = BrowsePayload(ai_settings={}, chat="Test chat message")
    
    # Patch ChatOpenAI and Agent
    with patch('browser.main.ChatOpenAI', new=MockedLLM), \
         patch('browser.main.Agent', new=AsyncMock(return_value=AsyncMock(run=AsyncMock(return_value="Mocked Result")))):
        
        result = await browse(payload)
        assert result == {"message": "Success", "result": "Mocked Result"}

@pytest.mark.asyncio
async def test_browse_failure():
    payload = BrowsePayload(ai_settings={}, chat="Test chat message")
    
    # Patch ChatOpenAI and Agent to raise an exception
    with patch('browser.main.ChatOpenAI', new=MockedLLM), \
         patch('browser.main.Agent', new=AsyncMock(side_effect=Exception("Mocked Error"))):
        
        with pytest.raises(HTTPException) as excinfo:
            await browse(payload)
        assert excinfo.value.status_code == 500
        assert str(excinfo.value.detail) == "Mocked Error"