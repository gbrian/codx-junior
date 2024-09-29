> from https://python.langchain.com/docs/use_cases/question_answering/code_understanding

Overview
The pipeline for QA over code follows the steps we do for document question answering, with some differences:

In particular, we can employ a splitting strategy that does a few things:

Keeps each top-level function and class in the code is loaded into separate documents.
Puts remaining into a separate document.
Retains metadata about where each split comes from
Quickstart
!pip install openai tiktoken chromadb langchain

# Set env var OPENAI_API_KEY or load from a .env file
# import dotenv

# dotenv.load_dotenv()

We’ll follow the structure of this notebook and employ context aware code splitting.

Loading
We will upload all python project files using the langchain.document_loaders.TextLoader.

The following script iterates over the files in the LangChain repository and loads every .py file (a.k.a. documents):

# from git import Repo
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers import LanguageParser
from langchain.text_splitter import Language

# Clone
repo_path = "/Users/rlm/Desktop/test_repo"
# repo = Repo.clone_from("https://github.com/langchain-ai/langchain", to_path=repo_path)

We load the py code using LanguageParser, which will:

Keep top-level functions and classes together (into a single document)
Put remaining code into a separate document
Retains metadata about where each split comes from
# Load
loader = GenericLoader.from_filesystem(
    repo_path + "/libs/langchain/langchain",
    glob="**/*",
    suffixes=[".py"],
    parser=LanguageParser(language=Language.PYTHON, parser_threshold=500),
)
documents = loader.load()
len(documents)

1293

Splitting
Split the Document into chunks for embedding and vector storage.

We can use RecursiveCharacterTextSplitter w/ language specified.

from langchain.text_splitter import RecursiveCharacterTextSplitter

python_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON, chunk_size=2000, chunk_overlap=200
)
texts = python_splitter.split_documents(documents)
len(texts)

3748

RetrievalQA
We need to store the documents in a way we can semantically search for their content.

The most common approach is to embed the contents of each document then store the embedding and document in a vector store.

When setting up the vectorstore retriever:

We test max marginal relevance for retrieval
And 8 documents returned
Go deeper
Browse the > 40 vectorstores integrations here.
See further documentation on vectorstores here.
Browse the > 30 text embedding integrations here.
See further documentation on embedding models here.
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

db = Chroma.from_documents(texts, OpenAIEmbeddings(disallowed_special=()))
retriever = db.as_retriever(
    search_type="mmr",  # Also test "similarity"
    search_kwargs={"k": 8},
)

Chat
Test chat, just as we do for chatbots.

Go deeper
Browse the > 55 LLM and chat model integrations here.
See further documentation on LLMs and chat models here.
Use local LLMS: The popularity of PrivateGPT and GPT4All underscore the importance of running LLMs locally.
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
result["answer"]