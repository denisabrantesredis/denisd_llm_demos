## LLM Demo

### Setup

Create a new environment for the demo (recommended) and install the pre-req packages.

```python
conda create -y --name rag_demo python=3.12

conda activate rag_demo

pip install --no-deps -r requirements.txt
```

Next, edit the `config.ini` file and set the Redis connection string, as well as the Google API Key.

The database you want to use for the demo needs to have JSON and Search enabled.

```yaml
[REDIS_INFO]
host=127.0.0.1
port=12000
user=
password=password
[GCP_INFO]
gcp_api_key=XXXX
```

PS: If the database has no password, <s>it should have one</s> you may need to edit the source code and change the connection string. Same goes for auth using certificates, etc.

To create a Google API Key, go to this URL:

[https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)

On that page, click the **Create Credentials** button, select **API Key** and copy the value. Then, edit your new API Key (which will show up on the top of the list as *API Key random number*), go to the **API Restrictions** section and select the **Restrict Key** option. 

A dropdown will be enabled where you can choose the permissions for this API. Scroll down on the list and choose **Generative Language API**.

**IMPORTANT**: make sure to restrict the permissions of the API!! *Great power, great responsibilities* and all of that. You should also consider recycling this key every now and then.

&nbsp;

## Running the App

Start the app by running:

```bash
streamlit run gui.py
```

App should then be accessible through the URL:

[http://127.0.0.1:8501](http://127.0.0.1:8501)

It should load automatically on your default browser.

Some details about this app:
- App was built using the new [Langchain package](https://redis.io/blog/langchain-redis-partner-package/) for cache and LLM memory

- Behind the scenes, it's using [Unstructured](https://docs.unstructured.io/open-source/core-functionality/partitioning#partition-html) to extract text from HTML pages. The code is very simple, it ignores images and most anything that's not pure text. If you're planning on demoing against your customer's web site, make sure to test it first; you may need to change the code in the [parsing.py](./utils/parsing.py) file if you want to modify the behavior. Unstructured supports several formats, so you can modify this to read PDFs, slides, images, etc.

- The app is configured to delete all documents with the `"idx:*"` key prefix every time the page is refreshed. This makes it simpler to test and redo the demo, etc. You can change this behavior by commenting line 167 on the [gui.py](./gui.py) file, if you want to preserve these documents across different demos.


&nbsp;
## Demo Flow

### Vector DB / Semantic Cache demo

The first page highlights a RAG use case with Redis as Vector DB and standard/semantic cache. This app reads web pages, stores the vectors in Redis and responds to user questions by using a Google Gemini model (which is why we need the Google API Key).

First, add the URL to the page you want to index. Keep in mind that, since we're showing cache and semantic cache, it needs to be some kind of content where you can ask 'similar' questions, to test the semantic search capabilities.

I recommend this blog post:

[https://redis.io/blog/redis-insight-makes-rdi-even-simpler/](https://redis.io/blog/redis-insight-makes-rdi-even-simpler/)

Once you add the URL to the field and press `return`, the code will extract the text and store it in Redis. 

At this point, there are 2 things you can highlight:

1 - On the left-side panel, a new card appeared, showing the time that it took for the code to insert the vectors in Redis. Do keep in mind that this time includes the generation of the vectors themselves, which is completely automated by the Langchain package. For this page, it should be around 250ms.

2 - You can use Redis Insight to show the actual documents, which will include some metadata (like the URL, etc), the original text and the vectors, which will look a bit weird, because they're being stored in a binary string format.

With the vectors in place, you can ask a question about the page. My recommendation for the first question is:

`How does Redis Insight make RDI simpler?`

This is, after all, the title of the blog post.

Once you ask the question and press `return`, a few things will happen:

1 - The code will check the Redis (basic) cache, to see if the question was already asked.

2 - This will be a cache miss, so the code will run a vector search.

3 - That search should return about 4 documents (a new label will appear on the screen with the number of retrieved documents). A new card will appear in 'The Redis Difference' panel showing the time it took to both check the cache and run the vector search (there is no way to get individual timing because all of this is done automatically by the Langchain code).

4 - With the vectors, the code will then call the Google Gemini API to get the model (`gemini-1.5-pro`) to generate a response. Fair warning, the quality of the response isn't great... I've been playing with the parameters to see if I can get better responses; you may want to change to the OpenAI model, if you have an API Key for that. Even a local Microsoft phi-3 model produced way better responses, so there's a lot of room to improve with Gemini, once I find the right settings. Regardless, it should take between 1.5 to 3 seconds for the model to respond, and a new card will appear with the LLM time.

&nbsp;

What we want to do now is highlight how much faster Redis can make this interaction. First, we want to show the basic cache.

If you go to Insight at this time, you will see that a new document was created, type JSON. This is the question we asked being cached (with the answer from the model). However, because we're using 'simple' cache, this will only be used if someone asks exactly the same question, *word for word, bar for bar* (like Drake).

Return to the application and send the same question again. Because this is streamlit, it won't resend unless you change the input; my recommendation is: delete the question mark, re-type it and press `return`. This will re-submit the same exact question as before, which will cause a cache hit this time.

The 'Redis Difference' cards will be updated to show the new times, and they should (hopefully) be a lot faster than before: because there was a cache hit, no vector search was performed, and the LLM was not called at all. This means that cache check time should be around 50ms and the time to retrieve the cached answer should be around 5ms (down from 3 seconds).

We do want to highlight how much faster Redis can make this environment perform. Also, you can talk about how simplified the code is: saving and checking the cache is completely automated, and everything else is a lot simpler with the Langchain package for Redis.

&nbsp;

However, we've only been using 'simple' cache right now, which is really not ideal, because it's unreasonable to expect that users will type the same question exactly. Which means that it's time to highlight the Semantic cache capabilities.

Click on the radio button for Semantic Cache, because of the way Streamlit works, the form will be re-submitted (meaning, the question will be asked again), which is a good thing, because this question will be in the semantic cache, just don't worry about the cars refreshing with new timings.

Next, you need to change the question just enough so it's not a perfect match. Keep in mind that if you change it too much, it will be outside of the similarity range (set to 20% by default), which will trigger a cache miss. I recommend changing the question to this:

`What does Redis Insight do to make RDI simpler?`

Hit `return` to send the question and you should get a cache hit, where you get the same answer from before, in about 50ms or so.

You can also go to Insight, where you will see a new document, type Hash with a key prefix of `llmcache`. Notice how the Langchain package creates a vector for the prompt, so the similarity search that runs against the cache can look for similar questions. The answer is stored in clear text, so it can be quickly retrieved, without having to be decoded.




&nbsp;
### LLM Memory demo

At the upper right corner of the page, you will find a **Live Chat** button, which will lead to a different page.

**IMPORTANT:** I recommend restarting the application if you're demoing LLM memory. For some reason, the app freaks out and won't react to new prompts, it will just send the same question over and over again. I have no idea why this is happening (other than I'm bad at writing code), but restarting the app fixes the issue.

There are actually 2 chat pages, one with Redis as LLM memory and one with no LLM memory. My recommended demo flow is:

1 - In the **AI Chatbot - with Redis as LLM Memory** page, ask a question that will lead to a follow-up. For instance:

`What is the capital of Canada?`

This is using the same Google Gemini model behind the scenes. The model should respond that the capital of Canada is Ottawa.

At this point, you can to go Insight and you should see 2 new documents, one for the question and one for the answer. These will be JSON documents, with a key prefix of `chat:default`, where 'default' is the user identifier, so the package can track multiple users at the same time.

Then, ask a follow-up question, like:

`How come it's not Toronto?`

The only way the model can properly answer this question is if it has the conversation history, so the context behind the question becomes clear. 

The Langchain package will retrieve all conversation documents, both questions and answers, from this user session (by the unique identifier) and will add them as part of the history that is sent to the model with every request. And the best part is, all this code is automated. It only takes 2 lines of code to have Redis serving as LLM memory.

You can ask another follow-up question, like:

`What other candidate cities can you list?`

Which again, requires context to be properly understood. This new interaction will also generate a new pair of Documents in Redis, one for the question and one for the answer.

One of the things you may want to highlight here is the multi-channel opportunity that Redis provides: by keeping conversation history off the client, customers can provide AI interactions that start at the browser and can continue on a mobile app; interactions where if the user decides to call the call center, they will have access to that conversation history, and will know what type of recommendations, etc the bot made for this user.

Not to mention, it will allow data scientists to very easily collect this conversation history to further refine the model and how it interacts with their users.

TL;DR: Redis can not only provide better user experiences, but help open entire new paths to revenue and communication channels with our customer's audiences.

&nbsp;

Finally, you can click on the **Chat - No History** link in the upper right corner of the UI (and then reload the page to clear the conversation history -- *that's another TO-DO on my list*).

This is the same chat we've seen before, talking to the same model as before. The difference is, there is no history here, and no context is carried between the questions.

You can start with the same question as before:

`What is the capital of Canada?`

And you should get a very similar answer. However, when you ask the follow-up question:

`How come it's not Toronto?`

The model will be very confused, as it will have no idea what you're talking about. Honest, you probably want to skip this demo part altogether, unless you're presenting something very basic to a non-technical audience, so they can understand the importance of the conversation history for chatbot UIs.