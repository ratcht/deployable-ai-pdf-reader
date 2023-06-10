import openai
from flask import Flask, redirect, url_for, render_template, request, session, after_this_request
from files.python.api import authenticate
from files.python.params import OPENAI_API_KEY, ACCEPTED_FILE_TYPES, UPLOAD_FOLDER_PATH, INDEX_JSON_FILE_PATH, PINECONE_API_KEY, ENVIRONMENT, INDEX
from files.python.datahandler import read_pdf, create_df, upload_to_pinecone, get_pinecone_index
from files.python.ask import ask
from files.python.obj.chat import ChatObj, parse_chat
from files.python.obj.error import StatusObj, parse_status
import json
import pandas as pd
import os
from dotenv import load_dotenv
import logging
from werkzeug.utils import secure_filename

class ComplexEncoder(json.JSONEncoder):
  def default(self, obj):
    if hasattr(obj,'jsonify'):
      return obj.jsonify()
    else:
      return json.JSONEncoder.default(self, obj)

# configure pinecone_index

pinecone_index = get_pinecone_index(PINECONE_API_KEY, ENVIRONMENT, INDEX)

# init logging
logging.basicConfig(level=logging.INFO)
handle = "app.py"
logger = logging.getLogger(handle)


script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
authenticate(OPENAI_API_KEY)

app = Flask(__name__)
app.secret_key = "admin"


def is_file_allowed(filename):
  file_extension = filename.rsplit('.', 1)[1]
  print(f"File Extension: {file_extension}")
  return file_extension in ACCEPTED_FILE_TYPES 


@app.route("/upload", methods=["POST"])
def upload_file():
  
  # check if request has file part
  if 'file' not in request.files: redirect(url_for('index'))

  file = request.files['file']
  
  # check if file is empty
  if file.filename == '': redirect(url_for('index'))

  # check if file is allowed
  if not (file and is_file_allowed(file.filename)):
    session["error"] = json.dumps(StatusObj(400, "File input was invalid!"), cls=ComplexEncoder)
    return redirect(url_for('error'))


  try:
    filename = secure_filename(file.filename)
    filepath = os.path.join(script_dir, UPLOAD_FOLDER_PATH, filename)
    print(f"File Path: {filepath}")
    file.save(filepath)
    print("Saved to upload folder!")
  except IOError as io:
    session["error"] = json.dumps(StatusObj(400, f"Something went wrong when reading/writing to the file... {io}"), cls=ComplexEncoder)
    return redirect(url_for('error'))
  
  try:
    # embed file and store as csv
    chunks = read_pdf(filepath)
    df = create_df(chunks)
    upload_to_pinecone(df, pinecone_index)
  except (openai.error.APIError, openai.error.InvalidRequestError, openai.error.Timeout) as oe:
    session["error"] = json.dumps(StatusObj(400, f"Something went wrong with the file when passing to OpenAI... {oe}"), cls=ComplexEncoder)
    return redirect(url_for('error'))
  except Exception as e:
    session["error"] = json.dumps(StatusObj(400, f"Something went wrong... {e}"), cls=ComplexEncoder)
  finally:
    # clear upload folder
    @after_this_request
    def remove_file(response):
      print('After request ...')
      os.remove(filepath)
      return response
    return redirect(url_for('error'))

@app.route("/upload/list", methods=["GET"])
def upload_list():
  # display pinecone fetch information
  
  return render_template("list.html", list=list)


@app.route("/chat", methods=["POST"])
def chat():  
  # Get chat input
  chat_input = request.get_json()

  # Send chat to GPT
  try:
    chat_response = ask(chat_input)
  except Exception as e:
    session["error"] = json.dumps(StatusObj(500, f"Something happened! Please retry. Exception: {e}"), cls=ComplexEncoder)
    return session["error"]

  chat = ChatObj(chat_input, chat_response)
  

  parsed_chat = parse_chat(
    json.loads(session["chat"])
  )
  
  parsed_chat.append(chat)

  session["chat"] = json.dumps(parsed_chat, cls=ComplexEncoder)

  return json.dumps(StatusObj(200), cls=ComplexEncoder)


@app.route("/chat/list", methods=["GET"])
def chat_list():
  print(f'Chat: {session["chat"]}')
  return render_template("partials/chat-partial.html", loaded_chat=parse_chat(json.loads(session["chat"])))

@app.route("/chat/clear", methods=["GET"])
def clear_chat():
  print("Chat cleared!")
  session.pop("chat")
  return redirect(url_for("index"))



@app.route("/error", methods=["GET"])
def error():
  """Handle errors"""

  # check if error is active
  if "error" not in session:
    return redirect(url_for("index"))
  
  # handle error
  error = parse_status(json.loads(session["error"]))
  print(f"\n  Error: {error.error_message}\n")

  

  session.pop("error") # remove from session once dealt with
  return redirect(url_for("index"))



@app.route("/", methods=["GET"])
def index():

  # set session if not set
  if "chat" not in session:
    session['chat'] = '[]' 
  
  return render_template("index.html")


if __name__ == "__main__":
  # webbrowser.open('http://127.0.0.1:8000')  # Go to example.com
  # set upload folder
  print(f"script_dir: {script_dir}")

  app.config["UPLOAD_FOLDER"] = os.path.join(script_dir, UPLOAD_FOLDER_PATH)

  # run app
  app.run(port=5000)


  