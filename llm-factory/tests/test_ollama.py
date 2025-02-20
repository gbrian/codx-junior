import sys
import time

from ollama import Client
from ollama import ChatResponse


model = sys.argv[1]
content = sys.argv[2]

start_time = time.time()

client = Client(
  host='http://0.0.0.0:11434',
  headers={'x-some-header': 'some-value'}
)

print(f"Pull model {model}")
client.pull(model=model)

print(f"Send rquest {content}")
response: ChatResponse = client.chat(
  model=model, 
  messages=[
    {
      'role': 'user',
      'content': content,
    },
  ],
  stream=True,
)

first_word_taken = None
for chunk in response:
    if not first_word_taken:
      first_word_taken = time.time() - start_time
    print(chunk['message']['content'], end='', flush=True)

time_taken = time.time() - start_time
print(f"Time taken: {time_taken}, first word at {first_word_taken}")