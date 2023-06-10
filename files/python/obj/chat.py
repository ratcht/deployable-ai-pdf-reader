import json

class ChatObj:
  def __init__(self, prompt, response):
    self.prompt = prompt
    self.response = response

  def get_prompt(self, prompt):
    return prompt
  
  def get_response(self, response):
    return response
  
  def jsonify(self):
    return dict(prompt = self.prompt, response=self.response) 
  

def parse_chat(json_obj):
  chat = []
  for chat_obj_json in json_obj:
    chat_obj = ChatObj(chat_obj_json["prompt"], chat_obj_json["response"])
    chat.append(chat_obj)
  return chat

