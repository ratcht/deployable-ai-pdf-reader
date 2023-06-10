from files.python.api import query, num_tokens, create_embedding
from files.python.params import GPT_MODEL, EMBEDDING_MODEL
import logging
import pinecone



def rank_strings_pinecone(
  query: str,
  pinecone_index: pinecone.Index,
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


def create_query(query: str, pinecone_index: pinecone.Index, model: str, token_budget: int):
  """Return a message for GPT, with relevant source texts pulled from a dataframe."""
  strings, relatednesses, titles = rank_strings_pinecone(query, pinecone_index, top_n=3)
  print("Finished ranking strings")

  introduction = 'Use the below information, including the title of the document, to answer the subsequent question. Paraphrase and reword the information in the document for clarity, but do not change any facts. Do not give answers that are too long. If the answer cannot be found in the information, write "I could not find an answer."'
  question = f"\n\nQuestion: {query}"
  message = introduction
  for string in strings:
    next_article = f'\n\Document Section:\n"""\n{string}\n"""'
    if (num_tokens(message + next_article + question, model=model) > token_budget):
      break
    else:
      message += next_article
  return message + question


def ask(prompt: str, pinecone_index: pinecone.Index):
  try:
    message = create_query(prompt, pinecone_index, model=GPT_MODEL, token_budget=4096-500)
  except Exception as e:
    raise Exception(f"From create_query()... {e}")
  
  try:
    response = query(message, GPT_MODEL)
  except Exception as e:
    raise Exception(f"From query()... {e}")

  
  return response


