import openai
import tiktoken
import logging
from files.python.obj.chat import ChatObj


def authenticate(API_KEY):
  openai.organization = "org-XWFEL4a6E0JSWS7rklGoJ8Vd" # organization name
  openai.api_key = API_KEY


def create_embedding(embedding_model: str, content):
  """Create an embedding"""

  try:
    response = openai.Embedding.create(model=embedding_model, input=content)
  except Exception as e:
    print(e)
    raise e

  
  for i, be in enumerate(response["data"]):
    assert i == be["index"]  # double check embeddings are in same order as input

  return response


def query(message: str, previous_chat: list[ChatObj], model: str):

  chat_to_load = []
  running_token_count = 0
  for chatobj in previous_chat:
    running_token_count += num_tokens(chatobj.prompt+chatobj.response, model)
    if running_token_count > 1000: break
    chat_to_load.append({"role": "user", "content": chatobj.prompt})
    chat_to_load.append({"role": "assistant", "content": chatobj.response})

  messages = [
    {"role": "system", "content": "You are skilled at reading and interpreting documents. You will throughly process provided documents and answer detailed questions given the information provided."},
    *chat_to_load,
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