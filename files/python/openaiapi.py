import openai
import tiktoken
import logging

handle = "api.py"
logger = logging.getLogger(handle)


def authenticate(API_KEY):
  openai.api_key = API_KEY


def create_embedding(embedding_model: str, content):
  """Create an embedding"""

  response = openai.Embedding.create(model=embedding_model, input=content)

  
  for i, be in enumerate(response["data"]):
    assert i == be["index"]  # double check embeddings are in same order as input

  return response


def query(message: str, model: str):
  messages = [
    {"role": "system", "content": "You are skilled at reading and interpreting documents. You will throughly process provided documents and answer detailed questions given the information provided."},
    {"role": "user", "content": message},
  ]

  try:
    response = openai.ChatCompletion.create(
      model=model,
      messages=messages,
      temperature=0
    )
  except Exception as e:
    raise Exception(f"From Chat Completion... {e}")
  
  response_message = response["choices"][0]["message"]["content"]
  return response_message


def num_tokens(text: str, model: str) -> int:
  """Return the number of tokens in a string"""
  encoding = tiktoken.encoding_for_model(model)
  return len(encoding.encode(text))