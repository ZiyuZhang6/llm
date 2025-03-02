"""
A minimal Retrieval-Augmented Generation (RAG) chatbot implementation
using LangChain with a history-aware retriever.

This script:
  - Loads documents from a given URL using a web loader. (Temporary)
  - Splits the documents into smaller chunks. (Temporary)
  - Creates embeddings and indexes the chunks in a FAISS vector store. (Temporary)
  - Uses a history-aware retriever and a document chain (for "stuffing" retrieved docs)
    to answer user questions based on both conversation history and retrieved context.
  - Uses an imported prompt template from prompt.py instead of building it inline.

Ensure you have your .env set up with OPENAI_API_KEY and that you have installed
the necessary dependencies.
"""

import os
import getpass
from typing_extensions import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.faiss import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from llm_research_assistant.rag.prompt import chat_prompt

##############################################################################
# 1) Environment Setup
##############################################################################

from dotenv import load_dotenv

load_dotenv()

# Check for the OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    print("Enter your OpenAI API key (e.g., sk-...):")
    os.environ["OPENAI_API_KEY"] = getpass.getpass()

LLM_MODEL = "gpt-4o-mini"  # Chat model for generation
EMBED_MODEL = "text-embedding-3-large"  # Embedding model for vectorization

##############################################################################
# 2) Document Loading & Splitting
##############################################################################


def get_documents_from_web(url: str) -> List[Document]:
    """
    Loads documents from the provided URL using WebBaseLoader,
    then splits the content into smaller chunks.
    """
    loader = WebBaseLoader(url)
    docs = loader.load()  # Load the webpage as Document(s)

    # Split documents into chunks for efficient embedding and retrieval.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,  # Adjust chunk size based on your data and LLM limits
        chunk_overlap=20,  # Small overlap to preserve context between chunks
    )
    split_docs = splitter.split_documents(docs)
    return split_docs


##############################################################################
# 3) Create Vector Store (Using FAISS, To be replaced with Chroma)
##############################################################################


def create_db(docs: List[Document]):
    """
    Creates a vector store (using FAISS) by embedding the provided documents.
    """
    embedding = OpenAIEmbeddings(model=EMBED_MODEL)
    # Create a FAISS vector store from the documents
    vector_store = FAISS.from_documents(docs, embedding=embedding)
    return vector_store


##############################################################################
# 4) Create the Retrieval Chain
##############################################################################


def create_chain(vector_store):
    """
    Creates a retrieval chain that:
      - Uses a chat LLM for generating answers.
      - Formats prompts with chat history.
      - Uses a history-aware retriever to generate better queries.
    """
    # Initialize the chat model
    model = ChatOpenAI(model=LLM_MODEL, temperature=0.4, verbose=True)

    # Create a document chain that "stuffs" the retrieved documents into the prompt.
    # This chain uses the custom prompt imported from prompt.py.
    chain = create_stuff_documents_chain(llm=model, prompt=chat_prompt)

    # Create a basic retriever from the vector store (retrieves top 3 relevant chunks)
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # Define a prompt for the history-aware retriever.
    # This prompt uses the conversation history to generate an optimized search query.
    retriever_prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            (
                "user",
                "Given the above conversation, generate a search query to retrieve \
                information relevant to the conversation.",
            ),
        ]
    )
    # Create a history-aware retriever that uses the above prompt.
    history_aware_retriever = create_history_aware_retriever(
        llm=model, retriever=retriever, prompt=retriever_prompt
    )

    # Create the retrieval chain using the history-aware retriever and document chain
    retrieval_chain = create_retrieval_chain(
        history_aware_retriever,  # The retriever that considers chat history
        chain,  # The chain that generates an answer using the retrieved documents
    )

    return retrieval_chain


def process_chat(chain, question, chat_history):
    """
    Processes a user question through the retrieval chain.
    Uses the provided chat_history for context.
    Returns the generated answer.
    """
    response = chain.invoke(
        {
            "chat_history": chat_history,
            "input": question,
        }
    )
    return response["answer"]


if __name__ == "__main__":
    # Load and process documents from the specified URL.
    docs = get_documents_from_web(
        "https://python.langchain.com/docs/expression_language/"
    )
    # Create the vector store (FAISS) from the processed documents.
    vector_store = create_db(docs)
    # Create the retrieval chain with history-aware retrieval.
    chain = create_chain(vector_store)

    # Initialize an empty chat history (list of message objects).
    chat_history = []

    print("Start chatting with the assistant (type 'exit' to quit):")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        # Process the user question through the retrieval chain.
        response = process_chat(chain, user_input, chat_history)
        # Append the messages to the chat history.
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=response))
        # Print the assistant's response.
        print("Assistant:", response)
