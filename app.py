import openai
from flask import Flask, redirect, url_for, render_template, request, session, after_this_request
from werkzeug.utils import secure_filename
from files.python.openaiapi import authenticate
from files.python.datastoreapi import get_config_value, update_document_list, update_config_value
from files.python.datahandler import read_pdf, read_pdf_from_file, create_df, upload_to_pinecone, get_pinecone_index
from files.python.ask import ask
from files.python.obj.chat import ChatObj, parse_chat
from files.python.obj.error import StatusObj, parse_status
import google.cloud.logging
import json
import os
import logging
import bcrypt

class ComplexEncoder(json.JSONEncoder):
  def default(self, obj):
    if hasattr(obj,'jsonify'):
      return obj.jsonify()
    else:
      return json.JSONEncoder.default(self, obj)

# get all keys


ACCEPTED_FILE_TYPES = get_config_value("ACCEPTED_FILE_TYPES").split(',')



script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in

# authenticate
OPENAI_API_KEY = get_config_value("OPENAI_API_KEY")
authenticate(OPENAI_API_KEY)



app = Flask(__name__)
app.secret_key = "admin"


def is_file_allowed(filename):
  file_extension = filename.rsplit('.', 1)[1]
  logging.info(f"File Extension: {file_extension}")
  return file_extension in ACCEPTED_FILE_TYPES 

@app.route('/refresh')
def refresh_vars():
  logging.warning('Reauthenticating OpenAI...')
  OPENAI_API_KEY = get_config_value("OPENAI_API_KEY")
  authenticate(OPENAI_API_KEY)

  return redirect(url_for('index'))


@app.route('/warn')
def warning():
  logging.warning('Warning page opened...')
  return '<html><body>Warning Page</body></html>'

@app.route('/test')
def test():
  logging.info('Test page opened...')
  return render_template("test.html")

@app.route('/gcl')
def setup_cloud_logging():
  client = google.cloud.logging.Client()
  client.get_default_handler()
  client.setup_logging()
  return '<html><body>Logging was set up</body></html>'


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
    # embed file and store on pinecone
    chunks = read_pdf_from_file(file)
    df = create_df(chunks, file.filename, get_config_value("EMBEDDING_MODEL"))

    PINECONE_API_KEY = get_config_value("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = get_config_value("PINECONE_ENVIRONMENT")
    PINECONE_INDEX = get_config_value("PINECONE_INDEX")

    upload_to_pinecone(df, get_pinecone_index(PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX))
    update_document_list(secure_filename(file.filename))
  except (openai.error.APIError, openai.error.InvalidRequestError, openai.error.Timeout) as oe:
    session["error"] = json.dumps(StatusObj(400, f"Something went wrong with the file when passing to OpenAI... {oe}"), cls=ComplexEncoder)
    return redirect(url_for('error'))
  except Exception as e:
    session["error"] = json.dumps(StatusObj(400, f"Something went wrong... {e}"), cls=ComplexEncoder)
  finally:
    logging.info("After Upload...")
    return redirect(url_for('error'))


@app.route("/upload/list", methods=["GET"])
def upload_list():
  # display pinecone fetch information
  document_list = get_config_value("UPLOADED_DOCUMENTS")
  
  return render_template("list.html", list=document_list)


@app.route("/chat", methods=["POST"])
def chat():  
  # Get chat input
  logging.info("In /chat")
  chat_input = request.get_json()

  parsed_chat = parse_chat(
    json.loads(session["chat"])
  )

  # Send chat to GPT
  try:
    PINECONE_API_KEY = get_config_value("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = get_config_value("PINECONE_ENVIRONMENT")
    PINECONE_INDEX = get_config_value("PINECONE_INDEX")
    chat_response = ask(chat_input, get_pinecone_index(PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX), get_config_value("GPT_MODEL"), get_config_value("EMBEDDING_MODEL"), get_config_value("GPT_USER_PROMPT"), parsed_chat)
  except Exception as e:
    session["error"] = json.dumps(StatusObj(500, f"Something happened! Please retry. Exception: {e}"), cls=ComplexEncoder)
    return session["error"]

  chat = ChatObj(chat_input, chat_response)
  parsed_chat.append(chat)

  session["chat"] = json.dumps(parsed_chat, cls=ComplexEncoder)

  return json.dumps(StatusObj(200), cls=ComplexEncoder)


@app.route("/chat/list", methods=["GET"])
def chat_list():
  logging.info(f'Chat: {session["chat"]}')
  return render_template("partials/chat-partial.html", loaded_chat=parse_chat(json.loads(session["chat"])))


@app.route("/chat/clear", methods=["GET"])
def clear_chat():
  logging.info("Chat cleared!")
  session.pop("chat")
  return redirect(url_for("index"))


@app.route("/admin/verify", methods=["GET", "POST"])
def admin_verify():
  if request.method == "GET":
    if "auth" not in session:
      session["auth"] = "False"
    
    if session["auth"] == "True":
      return redirect(url_for("admin_panel"))
    
    return render_template("verify.html")

  # if post
  input_password = request.form['passwordInput']
  stored_password = get_config_value("ADMIN_PASSWORD")
  
  # Encode the authenticating password as well</strong> 
  stored_password = stored_password.encode('utf-8')

  input_password = input_password.encode('utf-8') 
  
  # Use conditions to compare the authenticating password with the stored one</strong>:
  if bcrypt.checkpw(input_password, stored_password):
    # password matches
    session["auth"] = "True"
    return redirect(url_for("admin_panel"))
  return redirect(url_for("admin_verify", password_wrong = True))

    
@app.route("/admin/panel", methods=["GET", "POST"])
def admin_panel():
  if request.method == "GET":
    if "auth" not in session:
      session["auth"] = "False"
    
    if session["auth"] == "False":
      return redirect(url_for("admin_verify"))

    PINECONE_API_KEY = get_config_value("PINECONE_API_KEY")
    GPT_PROMPT = get_config_value("GPT_USER_PROMPT")
    OPENAI_API_KEY = get_config_value("OPENAI_API_KEY")
    return render_template("panel.html", pinecone_api = PINECONE_API_KEY, openai_api = OPENAI_API_KEY, gpt_prompt = GPT_PROMPT)

  gptPrompt = request.form['gptPrompt']
  pineconeAPI = request.form['pineconeAPI']
  openaiAPI = request.form['openaiAPI']

  update_config_value("GPT_USER_PROMPT", gptPrompt)
  update_config_value("PINECONE_API_KEY", pineconeAPI)
  update_config_value("OPENAI_API_KEY", openaiAPI)





@app.route("/error", methods=["GET"])
def error():
  """Handle errors"""

  # check if error is active
  if "error" not in session:
    return redirect(url_for("index"))
  
  # handle error
  error = parse_status(json.loads(session["error"]))
  print(f"\n  Error: {error.error_message}\n")
  logging.info(f"\n  Error: {error.error_message}\n")

  

  session.pop("error") # remove from session once dealt with
  return redirect(url_for("index"))



@app.route("/", methods=["GET"])
def index():

  # set session if not set
  if "chat" not in session:
    session['chat'] = '[]' 

  if "auth" not in session:
    session['auth'] = "False" 

  logging.info("In Index Page")
  
  return render_template("index.html")

@app.route("/index-old", methods=["GET"])
def index_new():
  
  # set session if not set
  if "chat" not in session:
    session['chat'] = '[]' 
  
  return render_template("index-old.html")


if __name__ == "__main__":
  # webbrowser.open('http://127.0.0.1:8000')  # Go to example.com
  # set upload folder
  logging.info(f"script_dir: {script_dir}")

  app.config["SESSION_TYPE"] = 'filesystem'


  # run app
  app.run(port=8000, debug=True)


  