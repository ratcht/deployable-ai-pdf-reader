from google.cloud import datastore
import logging
from google.cloud.datastore.query import PropertyFilter




"""This is deprecated. Do not use. Just keep as reference for functions"""

"""
def fetch_config_value_by_filter(key: str):
  filters = [("Type", "=", key)]
  query = client.query(kind='Config')
  query.add_filter(filter=PropertyFilter("Type", "=", key))
  res = list(query.fetch())
  if (len(res) == 0): raise Exception("Datastore: Entity not found in database")
  if (len(res) > 1): raise Exception("Datastore: You fucked up with your keys. Multiple entities were returned")
  return res
"""



def set_config_value(key: str, value:str):
  client = datastore.Client(project="ai-chatbot-389511")

  complete_key = client.key("Config", key)
  entity = datastore.Entity(key=complete_key)
  entity.update(
    {
      "Value": value
    }
  )
  client.put(entity)


def update_config_value(key: str, value:str):
  client = datastore.Client(project="ai-chatbot-389511")

  keys = client.key("Config", key)
  entity = client.get(key=keys)
  if (entity == None): raise Exception("Datastore: Entity not found in database")
  entity.update(
    {
      "Value": value
    }
  )
  client.put(entity)

def update_document_list(document_title: str, is_deleting = False):
  client = datastore.Client(project="ai-chatbot-389511")

  entity = get_config_entity_by_key("UPLOADED_DOCUMENTS")
  document_list: list = entity['Value']
  
  if is_deleting: document_list.remove(document_title)
  else: document_list.append(document_title)

  entity.update(
    {
      "Value": document_list
    }
  )
  client.put(entity)


def get_config_value(key:str):
  return get_config_entity_by_key(key)['Value']

def get_config_entity_by_key(key:str):
  client = datastore.Client(project="ai-chatbot-389511")

  keys = client.key("Config", key)
  entity = client.get(key=keys)
  if (entity == None): raise Exception("Datastore: Entity not found in database")
  return entity




#try:
#  logger.info(fetch_config_value("EMBEDDING_MODEL"))
#except Exception as e:
#  logger.error(f"oh shit: {e}")

