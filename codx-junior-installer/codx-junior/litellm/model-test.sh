curl -X POST http://litellm-codx-junior:4000/v1/chat/completions \
 -H "Authorization: Bearer sk-efwefwe-hwdwqfew!" \
 -H "Content-Type: application/json" \
 -d '{ "model": "ollama/phi4",  "messages": [{"role": "user", "content": "Hello!"}]  }'  