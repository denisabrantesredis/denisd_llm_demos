import os
import time
import redis
import streamlit as st

os.environ["PYDANTIC_SKIP_VALIDATING_CORE_SCHEMAS"] = "True"

from configparser import ConfigParser

from unstructured.partition.html import partition_html
from unstructured.chunking.title import chunk_by_title
from unstructured.staging.base import convert_to_dict, dict_to_elements
from utils.rag_schema import Document as rag_document

from langchain_redis import RedisConfig, RedisVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_redis import RedisCache
from langchain_redis import RedisSemanticCache
from langchain.globals import set_llm_cache

from streamlit_extras.metric_cards import style_metric_cards

st.set_page_config(layout="wide", page_title="Redis-Chat-Go")

time_parse, time_save, time_search, time_llm = 0, 0, 0, 0

main_sidebar = st.sidebar
with main_sidebar:
    center_img = f"""
        <div style='text-align:center; margin-top: 0px; min-height:80px;'>
            <img src='https://redis.io/wp-content/uploads/2024/04/Redis_Desktop_15_FeatureStores_M6_Icon01.svg?&auto=webp&quality=85,75&width=80'/>
        </div>
        <div style='font-family: \"Space Grotesk\";font-weight: 400; letter-spacing: 0; font-size: 22px; margin-top: 20px; margin-bottom: 20px; text-align:center;'>
            The Redis Difference
        </div>
    """
    st.markdown(center_img, unsafe_allow_html=True)


embeddings = HuggingFaceEmbeddings()

style = """
<style>
@font-face {
    font-family: 'Space Grotesk';
    src: url('https://redis.io/wp-content/themes/redislabs-glide/assets/dist/fonts/SpaceGrotesk-Regular.woff') format("woff");
}

html,
body,
[class*='css'] {
    font-family: 'Space Grotesk';
    color: #0a6309;
}
p, ol, ul, dl {
    font-family: 'Space Grotesk';
    margin:0px 0px 1rem;
    padding: 0px;
    font-size: 1rem;
    font-weight: 400;
}
h1, h2, h3, h4 {
    font-family: 'Space Grotesk';
    font-weight: 400;
}
.top-bar {
    font-family: 'Space Grotesk';
    background-color: #FFFFFF;
    padding: 15px;
    color: white;
    margin-top: -20px;
}

</style>
"""

st.markdown(style, unsafe_allow_html=True)

input_panel = st.container()
with input_panel:
    panel1, panel2 = st.columns([0.85,0.15])
    with panel1:
        st.markdown(
            """
            <div class="top-bar">
                <img src="https://redis.io/wp-content/uploads/2024/04/Logotype.svg?auto=webp&quality=85,75&width=80" alt="Redis Logo" height="40">
            </div>
            """,
            unsafe_allow_html=True,
        )
    with panel2:
        st.page_link("pages/chat.py", label="Live Chat", icon="🤖")



st.title("The lazy person's web page reader™")

config_obj = ConfigParser()
config_obj.read("./config.ini")
redis_host = config_obj['REDIS_INFO']['host']
redis_port = config_obj['REDIS_INFO']['port']
redis_user = config_obj['REDIS_INFO']['user']
redis_pass = config_obj['REDIS_INFO']['password']

REDIS_URL = f"redis://default:{redis_pass}@{redis_host}:{redis_port}"

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = config_obj['GCP_INFO']['gcp_api_key']



def typewriter(text: str, speed: int):
    tokens = text.split()
    container = st.empty()
    for index in range(len(tokens) + 1):
        curr_full_text = " ".join(tokens[:index])
        container.markdown(curr_full_text)
        time.sleep(1 / speed)

def load_vector_store():
    config = RedisConfig(
        index_name="idx:web",
        redis_url=REDIS_URL,
        metadata_schema=[
            {"name": "id", "type": "text"},
            {"name": "url", "type": "text"},
            {"name": "filetype", "type": "text"},
            {"name": "languages", "type": "tag"}
        ]
    )
    vector_store = RedisVectorStore(embeddings, config=config)
    return vector_store

def load_chat_model(use_cache):

    if use_cache == "Use Cache":
        redis_cache = RedisCache(redis_url=REDIS_URL, ttl=3600)
    else:
        redis_cache = RedisSemanticCache(redis_url=REDIS_URL, embeddings=embeddings, distance_threshold=0.2, ttl=3600)

    set_llm_cache(redis_cache)

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0.5,
        top_p=0.95,
        top_k=64,
        max_output_tokens=8192
        )

    return llm

def vector_db_cleanup():
    db_client = redis.Redis(host=redis_host, port=redis_port, password=redis_pass, decode_responses=True)
    try:
        for key in db_client.scan_iter("idx:*"):
            db_client.delete(key)
        db_client.ft("idx:web").dropindex()
    except Exception as e:
        print(f"Index not found.")


with st.spinner("Connecting to Vector Database"):
    vector_db_cleanup()
    vector_store = load_vector_store()

## INPUT FOR WEB SITE URL

input_panel = st.container()
with input_panel:
    panel1, na = st.columns([0.99,0.01])
    with panel1:
        use_cache = st.radio(
            "Use Cache?",
            ["Use Cache", "Use Semantic Cache (20%)"],
            index=0,
            key=None,
            help=None,
            on_change=None,
            args=None,
            kwargs=None,
            disabled=False,
            horizontal=True,
            captions=None,
            label_visibility="hidden")

url_input = st.text_input(label="Enter the URL to the page you definitely don't want to read:", key="url_input")

if url_input:
    with st.spinner("Reading the page for you, beloved lazy person..."):
            timer_start = time.perf_counter()
            acceptable_types = ["NarrativeText", "List", "ListItem"]
            elements = partition_html(url=url_input)
            output_list = rag_document()
            for element in elements:
                el = element.to_dict()
                el_type = el["type"]
                if el_type in acceptable_types:
                    if len(el["text"]) >= 20:
                        output_list.append(element.to_dict())

            elements_raw = dict_to_elements(output_list)
            chunking_settings = {
                "combine_text_under_n_chars": 50,
                "max_characters": 750,
                "new_after_n_chars": 500
            }
            chunked_raw = chunk_by_title(elements=elements_raw, **chunking_settings)
            chunk_results = convert_to_dict(chunked_raw)

            counter = 0
            texts = []
            metadata = []

            for document in chunk_results:
                counter = counter + 1
                texts.append(document['text'])
                metadata_obj = {
                                "id": f"webdoc:{counter:05}",
                                "url": document["metadata"]["url"],
                                "filetype": document["metadata"]["filetype"],
                                "languages": document["metadata"]["languages"],
                                }
                metadata.append(metadata_obj)

            timer_end = time.perf_counter()
            time_parse = round(timer_end - timer_start, 4)

            timer_start = time.perf_counter()
            doc_ids = vector_store.add_texts(texts, metadata)
            timer_end = time.perf_counter()

            time_save = round(timer_end - timer_start, 4)
            with main_sidebar:
                dash_2 = st.container()
                with dash_2:
                    panel1, na = st.columns([0.99,0.01])
                    panel1.metric(label="Vector DB Insert Time (sec)", value=time_save, delta=None)
                    style_metric_cards()

    st.text(f"Success! {len(doc_ids)} documents inserted in the Vector Database!")

    st.divider()

    user_input = st.text_input(label="Now, ask a question about that page", key="input")
    if user_input:

        with st.spinner("Searching the Vector Database"):
            timer_start = time.perf_counter()
            result_nodes = vector_store.similarity_search_with_score(user_input)
            timer_end = time.perf_counter()

            time_search = round(timer_end - timer_start, 4)

            with main_sidebar:
                dash_3 = st.container()
                with dash_3:
                    panel1, na = st.columns([0.99,0.01])
                    panel1.metric(label="Vector DB Search Time (sec)", value=time_search, delta=None)
                    style_metric_cards()

        total_results = len(result_nodes)
        st.text(f"[Found {total_results} results in the Vector Database]")

        text_list = []
        distance_list = []

        if use_cache == "Use Cache":
            spinner_text = "Getting a Response from the LLM - using Redis Cache"
        else:
            spinner_text = "Getting a Response from the LLM - using Redis Semantic Cache"
        with st.spinner(spinner_text):
            for node in result_nodes:
                text_list.append(node[0].page_content)
                distance = node[1]
                distance_list.append(distance)

            # Get a consolidated response from the LLM
            st.subheader("Response from the Large Language Model", divider="rainbow")

            system_template = """
            Your task is to answer questions by using a given context.

            Don't invent anything that is outside of the context.

            %CONTEXT%
            {context}

            """

            llm_response_container = st.empty()

            messages = [
                SystemMessage(content=system_template.format(context=text_list)),
                HumanMessage(content=user_input)
            ]

            llm = load_chat_model(use_cache)

            timer_start = time.perf_counter()
            llm_response = llm.invoke(messages)
            timer_end = time.perf_counter()
            #typewriter(text=llm_response.content, speed=20)
            st.markdown(llm_response.content)

            time_llm = round(timer_end - timer_start, 4)

            with main_sidebar:
                dash_4 = st.container()
                with dash_4:
                    panel1, na = st.columns([0.99,0.01])
                    panel1.metric(label="LLM Time (sec)", value=time_llm, delta=None)
                    style_metric_cards()

            st.divider()
