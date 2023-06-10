class StatusObj:
  def __init__(self, status_code: int, error_message:str = ""):
    self.status_code = status_code
    self.error_message = error_message
  
  def jsonify(self):
    return dict(status_code = self.status_code, error_message = self.error_message)
  
def parse_status(json_obj):
  return StatusObj(json_obj["status_code"], json_obj["error_message"])
