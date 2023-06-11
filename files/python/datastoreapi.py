from google.cloud import datastore
import logging
from google.cloud.datastore.query import PropertyFilter

client = datastore.Client(project="ai-chatbot-389511")


# init logging
handle = "datastoreapi.py"
logger = logging.getLogger(handle)



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
  complete_key = client.key("Config", key)
  entity = datastore.Entity(key=complete_key)
  entity.update(
    {
      "Value": value
    }
  )
  client.put(entity)


def update_config_value(key: str, value:str):
  keys = client.key("Config", key)
  entity = client.get(key=keys)
  if (entity == None): raise Exception("Datastore: Entity not found in database")
  entity.update(
    {
      "Value": value
    }
  )
  client.put(entity)


def get_config_value_by_key(key:str):
  keys = client.key("Config", key)
  entity = client.get(key=keys)
  if (entity == None): raise Exception("Datastore: Entity not found in database")
  return entity




#try:
#  logger.info(fetch_config_value("EMBEDDING_MODEL"))
#except Exception as e:
#  logger.error(f"oh shit: {e}")
