from PyPDF2 import PdfReader
import pandas as pd  # for storing text and embeddings data
from files.python.openaiapi import create_embedding, num_tokens
import logging
from werkzeug.utils import secure_filename
import pinecone



# read pdf
def read_pdf(file_path: str) -> list:
  reader = PdfReader(file_path)
  chunks = []
  for page in reader.pages:
    chunks.append(page.extract_text())
  return chunks

def read_pdf_from_file(file) -> list:
  reader = PdfReader(file)
  chunks = []
  for page in reader.pages:
    excerpt = page.extract_text()
    chunks.append(excerpt)
  return chunks

# process embeddings
def create_df(chunks: list, title: str, EMBEDDING_MODEL: str, batch_size = 1000) -> pd.DataFrame:
  embeddings = []
  for batch_start in range(0, len(chunks), batch_size):
    batch_end = batch_start + batch_size
    batch = chunks[batch_start:batch_end]
    print(f"Batch {batch_start} to {batch_end-1}")

    response = create_embedding(EMBEDDING_MODEL, batch)
    
    batch_embeddings = [e["embedding"] for e in response["data"]]
    embeddings.extend(batch_embeddings)

  titles = [title for i in range(len(embeddings))]
  df = pd.DataFrame({"text": chunks, "embedding": embeddings, "title": titles})
  return df


def get_pinecone_index(API_KEY, ENVIRONMENT, INDEX) -> pinecone.Index:
  pinecone.init(
    api_key=API_KEY,
    environment=ENVIRONMENT 
  )
  index = pinecone.Index(INDEX)
  return index

  
def get_starting_id(pinecone_index: pinecone.Index):
  return pinecone_index.describe_index_stats()['total_vector_count']


def upload_to_pinecone(df: pd.DataFrame, pinecone_index: pinecone.Index, batch_size: int = 32):

  for batch_start in range(0, len(df.index), batch_size):
    batch_end = batch_start + batch_size
    
    print(f"Batch {batch_start} to {batch_end-1}")

    batch = df[batch_start:batch_end]

    batch_titles = batch['title'].tolist()

    startingID = get_starting_id(pinecone_index)
    batch_ids = [i+startingID for i in range(0,len(batch_titles))]
    batch_ids_string = list(map(str, batch_ids))
    batch_embeddings = batch['embedding'].tolist()
    batch_text = batch['text'].tolist()

    meta = [{'title':title, 'text': text } for title, text in zip(batch_titles, batch_text)]
    
    # prep metadata and upsert batch
    to_upsert = zip(batch_ids_string, batch_embeddings, meta)

    # upsert to Pinecone
    pinecone_index.upsert(vectors=list(to_upsert))


def delete_by_title_pinecone(pinecone_index: pinecone.Index, document_title: str):
  pinecone_index.delete(delete_all=False, filter={"secured_title": document_title})




  