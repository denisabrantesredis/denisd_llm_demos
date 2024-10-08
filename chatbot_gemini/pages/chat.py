import os
import streamlit as st
from configparser import ConfigParser

from langchain_redis import RedisChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_google_genai import ChatGoogleGenerativeAI

st.set_page_config(layout="wide", page_title="Redis-Chat-Go")

config_obj = ConfigParser()
config_obj.read("./config.ini")
redis_host = config_obj['REDIS_INFO']['host']
redis_port = config_obj['REDIS_INFO']['port']
redis_user = config_obj['REDIS_INFO']['user']
redis_pass = config_obj['REDIS_INFO']['password']

REDIS_URL = f"redis://default:{redis_pass}@{redis_host}:{redis_port}"

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = config_obj['GCP_INFO']['gcp_api_key']

# Initialize RedisChatMessageHistory
user_session = "default"

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.5,
    top_p=0.95,
    top_k=64,
    max_output_tokens=8192
    )

# Create a conversational chain
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])
chain = prompt | llm


# Function to get or create a RedisChatMessageHistory instance
def get_redis_history(session_id: str):
    return RedisChatMessageHistory(session_id, redis_url=REDIS_URL, ttl=3600)

# Create a runnable with message history
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_redis_history,
    input_messages_key="input",
    history_messages_key="history"
)

def generate_response(input_text, user_session):
    response = chain_with_history.invoke({"input": input_text}, config={"configurable": {"session_id": user_session}})
    return response.content


# Constants
NUMBER_OF_MESSAGES_TO_DISPLAY = 20

def initialize_conversation():
    assistant_message = "Hello! How can I assist you today?"

    conversation_history = [
        {"role": "system", "content": "You are a specialized AI assistant"},
        {"role": "system", "content": "Refer to conversation history to provide context to your response."},
        {"role": "assistant", "content": assistant_message}
    ]
    return conversation_history


def initialize_session_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []


def on_chat_submit(chat_input, user_session):
    user_input = chat_input.strip().lower()

    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = initialize_conversation()

    st.session_state.conversation_history.append({"role": "user", "content": user_input})

    # response = generate_response(st.session_state.conversation_history, user_session)
    response = generate_response(chat_input, user_session)

    assistant_reply = response

    st.session_state.conversation_history.append({"role": "assistant", "content": assistant_reply})
    st.session_state.history.append({"role": "user", "content": user_input})
    st.session_state.history.append({"role": "assistant", "content": assistant_reply})




def main():
    initialize_session_state()

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
            link_panel = st.container()
            with link_panel:
                panel1, panel2 = st.columns([0.5,0.5])
                with panel1:
                    st.page_link("gui.py", label="Home", icon="🏠")
                with panel2:
                    st.page_link("pages/chat_no_history.py", label="Chat - No History", icon="⛔️")

    st.title("AI Chatbot - with Redis as LLM Memory")


    if not st.session_state.history:
        initial_bot_message = "Hello! How can I assist you today?"
        st.session_state.history.append({"role": "assistant", "content": initial_bot_message})
        st.session_state.conversation_history = initialize_conversation()


    #st.toggle("Keep Chat History", value=True, on_change=load_chat_model)

    chat_input = st.chat_input("Ask me anything")
    if chat_input:
        on_chat_submit(chat_input, user_session)

    # Display chat history
    for message in st.session_state.history[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
        role = message["role"]

        user_image = "https://streamly.streamlit.app:443/~/+/media/af4f6547a2bed5f2155bcd7972b52f98441e3548ef0d1a0dca033dec.png"
        redis_image = "https://redis.io/wp-content/themes/wpx/assets/images/favicons/favicon-32x32.png?v=1720078588"
        avatar_image = redis_image if role == "assistant" else user_image if role == "user" else None

        with st.chat_message(role, avatar=avatar_image):
            st.write(message["content"])


if __name__ == "__main__":
    main()
