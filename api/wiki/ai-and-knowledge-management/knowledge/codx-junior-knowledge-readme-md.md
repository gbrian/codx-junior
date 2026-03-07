## Question Answering over Code

This document outlines a pipeline for Question Answering (QA) over code, drawing parallels with standard document QA but incorporating specific strategies for code.

### Overview

The QA over code pipeline follows similar steps to document QA, with key differences in the splitting strategy. This approach aims to:

*   Keep top-level functions and classes as separate documents.
*   Group remaining code into distinct documents.
*   Preserve metadata indicating the origin of each split.

### Quickstart

To get started, install the necessary libraries:

```python
!pip install openai tiktoken chromadb langchain
```

You will also need to set your OpenAI API key as an environment variable (`OPENAI_API_KEY`) or load it from a `.env` file.

### Loading Code Documents

All Python project files are loaded using `langchain.document_loaders.TextLoader`. The following script demonstrates iterating through files in a specified repository path and loading each `.py` file.

```python
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers import LanguageParser
from langchain.text_splitter import Language

# Clone the repository (example path)
repo_path = "/Users/rlm/Desktop/test_repo"
# repo = Repo.clone_from("https://github.com/langchain-ai/langchain", to_path=repo_path)

# Load Python code using LanguageParser
loader = GenericLoader.from_filesystem(
    repo_path + "/libs/langchain/langchain",
    glob="**/*",
    suffixes=[".py"],
    parser=LanguageParser(language=Language.PYTHON, parser_threshold=500),
)
documents = loader.load()
print(len(documents))
# Output: 1293
```

The `LanguageParser` ensures that top-level functions and classes are kept together within a single document, while other code segments are placed in separate documents. Crucially, it retains metadata about the source of each split.

### Splitting Documents

To prepare documents for embedding and vector storage, they are split into smaller chunks. The `RecursiveCharacterTextSplitter` with the `Language.PYTHON` option is utilized for this purpose.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

python_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON, chunk_size=2000, chunk_overlap=200
)
texts = python_splitter.split_documents(documents)
print(len(texts))
# Output: 3748
```

### RetrievalQA

For semantically searching code content, documents are embedded and stored in a vector store. The setup for the vectorstore retriever includes testing Maximum Marginal Relevance (MMR) for retrieval and setting the number of returned documents to 8.

For more information on vectorstore integrations and embedding models, refer to the [LangChain documentation](https://python.langchain.com/docs/integrations/vectorstores) and [embedding model integrations](https://python.langchain.com/docs/integrations/text_embedding).

```python
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

db = Chroma.from_documents(texts, OpenAIEmbeddings(disallowed_special=()))
retriever = db.as_retriever(
    search_type="mmr",  # Also test "similarity"
    search_kwargs={"k": 8},
)
```

### Chat with Code

The system can be used for conversational QA, similar to chatbots. This involves integrating Large Language Models (LLMs) and memory.

For more information on LLM and chat model integrations, refer to the [LangChain documentation](https://python.langchain.com/docs/integrations/chat_models). Consider using local LLMs for enhanced privacy and control.

```python
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationSummaryMemory

llm = ChatOpenAI(model_name="gpt-4")
memory = ConversationSummaryMemory(
    llm=llm, memory_key="chat_history", return_messages=True
)
qa = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, memory=memory)

question = "How can I initialize a ReAct agent?"
result = qa(question)
print(result["answer"])
```