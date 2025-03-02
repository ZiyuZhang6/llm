from langchain.prompts import PromptTemplate

# The template has placeholders for:
# - chat_history: the conversation so far (previous user + assistant turns)
# - context: relevant chunks retrieved from your vector store
# - question: the user’s new query

chat_template = """
You are a helpful and knowledgeable research assistant. Your role is to answer questions
using the provided context. You can also reference the conversation history to
understand the user’s references or follow-up questions.

Here is the conversation so far:
{chat_history}

Here are relevant excerpts from your knowledge base (research papers):
{context}

Please answer the user's question, using only the information from these excerpts and
the conversation history. If you do not have enough information, say so.
Do not fabricate data.

User’s current question: {input}

Your answer:
"""

chat_prompt = PromptTemplate(
    template=chat_template, input_variables=["chat_history", "context", "input"]
)
