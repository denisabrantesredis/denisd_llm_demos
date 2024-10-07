import os
import json
import redis
import numpy as np
from configparser import ConfigParser
from redis.commands.json.path import Path
from redis.commands.search.query import Query
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import NumericField, TagField, TextField, VectorField


def initialize_db(client):
  try:
    for key in client.scan_iter("vecdoc:*"):
      client.delete(key)
    client.ft("idx:vecdoc").dropindex()
  except Exception as e:
    print(f"Index doesn't exist. Will create a new one.")


def create_index(client, VECTOR_DIMENSION):
   
    # Create an index for the vectors
    result = "FAILED"

    schema = (
        TextField("$.element_id", as_name="element_id"),
        TagField("$.doc_id", as_name="doc_id"),
        TagField("$.id", as_name="id"),
        TextField("$.text", as_name="text"),
        TextField("$.title", as_name="title"),
        TagField("$.authors", as_name="authors"),
        TagField("$.published", as_name="published"),
        VectorField(
            "$.vector",
            "FLAT",
            {
                "TYPE": "FLOAT32",
                "DIM": VECTOR_DIMENSION,
                "DISTANCE_METRIC": "COSINE",
            },
            as_name="vector",
        )
    )
    try:
        definition = IndexDefinition(prefix=["vecdoc:"], index_type=IndexType.JSON)
        result = client.ft("idx:lmdoc").create_index(fields=schema, definition=definition)
    except Exception as ex:
        result = f"FAILED to create index: {ex}"
    return result

  
def get_index_status(client):
  info = client.ft("idx:vecdoc").info()
  return info


def json_search_by_key(client, key):
    return client.json().get(key)


def execute_query(client, query):
    all_items = client.sort(query, desc=False)
    return all_items


def write_vector(client, document):
    result = "FAILED"
    try:
        pipeline = client.pipeline()
        redis_key = document['redis_key']
        pipeline.json().set(redis_key, "$", document)
        res = pipeline.execute()
        result = f"{redis_key} record inserted successfully"
    except Exception as e:
        result = f"FAILED with error: {e}"
    return result
  

def vector_query(client, query_vector):
    response = "FAILED TO RUN QUERY"

    query = (
        Query('(*)=>[KNN 3 @embeddings $query_vector AS vector_score]')
        .sort_by('vector_score')
        .return_fields('vector_score', 'title', 'text', 'metadata.orig_elements')
        .dialect(2)
    )
    query_input = json.loads(query_vector)
    query_response = client.ft("idx:vecdoc").search(query, { 'query_vector': np.array(query_input, dtype=np.float32).tobytes() }).docs
    response = []
    for doc in query_response:
        #json_doc = doc.id
        #response.append(json_doc)
        response.append(doc)
    return response


def hybrid_query(client, query_vector, author):
    response = "FAILED TO RUN QUERY"

    query = (
        Query('(@authors:{$author})=>[KNN 3 @embeddings $query_vector AS vector_score]')
        .sort_by('vector_score')
        .return_fields('vector_score', 'title', 'text', 'metadata.orig_elements')
        .dialect(2)
    )
    query_input = json.loads(query_vector)
    query_response = client.ft("idx:vecdoc").search(query, {'author': author,'query_vector': np.array(query_input, dtype=np.float32).tobytes() }).docs
    response = []
    for doc in query_response:
        #json_doc = doc.id
        #response.append(json_doc)
        response.append(doc)
    return response


def embed(client, documents):
  insert_results = []
  #client = initialize_db(client)

  try:
    create_index(client, 1024)
  except Exception as e:
    print(f"Failed to create index with exception: {e}")
    insert_results.append(e)

  for i in range(len(documents)):
      document = documents[i]
      insert_result = write_vector(client, document)
      insert_results.append(insert_results)
      if i % 20 == 0:
          print(f"--> Inserting document {i} - result: {insert_result}")

  return insert_results

def insert_records(client, documents):
  insert_results = []

  for i in range(len(documents)):
      document = documents[i]
      insert_result = write_vector(client, document)
      insert_results.append(insert_results)
      if i % 20 == 0:
          print(f"--> Inserting document {i} - result: {insert_result}")

  return insert_results

