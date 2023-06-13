from files.python.openaiapi import query, num_tokens, create_embedding
import logging
import pinecone

handle = "ask.py"
logger = logging.getLogger(handle)

def rank_strings_pinecone(
  query: str,
  pinecone_index: pinecone.Index,
  EMBEDDING_MODEL: str,
  top_n: int = 100
  ):

  query_embedding_response = create_embedding(
    EMBEDDING_MODEL,
    query
  )
  query_embedding = query_embedding_response["data"][0]["embedding"]

  pinecone_res = pinecone_index.query(query_embedding, top_k=top_n, include_metadata=True)

  strings = []
  relatednesses = []
  titles = []
  for match in pinecone_res['matches']:
    strings.append(match['metadata']['text'])
    titles.append(match['metadata']['title'])
    relatednesses.append(match['score'])

  return strings, relatednesses, titles


def create_query(query: str, pinecone_index: pinecone.Index, EMBEDDING_MODEL: str, GPT_MODEL: str, GPT_PROMPT: str, token_budget: int):
  """Return a message for GPT, with relevant source texts pulled from a dataframe."""
  strings, relatednesses, titles = rank_strings_pinecone(query, pinecone_index, EMBEDDING_MODEL, top_n=3)
  logger.info("Finished ranking strings")

  introduction = GPT_PROMPT
  question = f"\n\nQuestion: {query}"
  message = introduction
  for string, title in zip(strings, titles):
    next_article = f'\n\Document Title: {title}. Excerpt:\n"""\n{string}\n"""'
    if (num_tokens(message + next_article + question, model=GPT_MODEL) > token_budget):
      break
    else:
      message += next_article
  return message + question


def ask(prompt: str, pinecone_index: pinecone.Index, GPT_MODEL: str, EMBEDDING_MODEL: str, GPT_PROMPT:str, previous_chat: list = []):
  try:
    message = create_query(prompt, pinecone_index, EMBEDDING_MODEL=EMBEDDING_MODEL, GPT_MODEL=GPT_MODEL, GPT_PROMPT=GPT_PROMPT, token_budget=4096-1000)
  except Exception as e:
    raise Exception(f"From create_query()... {e}")
  
  # only take the last 3 messages
  chat_to_send = previous_chat[len(previous_chat)-4:] if (len(previous_chat) > 0) else []

  try:
    response = query(message, chat_to_send, GPT_MODEL)
  except Exception as e:
    raise Exception(f"From query()... {e}")

  
  return response


