import os
os.environ["LIVEKIT_URL"]="ws://127.0.0.1:7880"
os.environ["LIVEKIT_API_KEY"]="devkey"
os.environ["LIVEKIT_API_SECRET"]="secret"
os.environ["OPENAI_API_KEY"]="" #! Add your OpenAI API key (for whisper and text-to-speech)

import asyncio
from watson import WatsonXLLM
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm, tokenize
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero, elevenlabs, llama_index, deepgram
from livekit.plugins.elevenlabs.tts import Voice, VoiceSettings
from livekit import rtc
from llama_index.core.schema import MetadataMode
from llama_index.core.retrievers import (
    BaseRetriever,
    VectorIndexRetriever,
    KeywordTableSimpleRetriever
)
from livekit.agents.pipeline import VoicePipelineAgent
import os
from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.chat_engine.types import ChatMode
from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

PERSIST_DIR="./index"
storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
index = load_index_from_storage(storage_context)
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

async def entrypoint(ctx: JobContext):
    # Create an initial chat context with a system prompt
    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    system_msg = llm.ChatMessage(
        role="system",
        content=system_prompt,
    ) 
    initial_ctx = llm.ChatContext()
    initial_ctx.messages.append(system_msg)
    
    async def _will_synthesize_assistant_reply(
        assistant: VoicePipelineAgent, chat_ctx: llm.ChatContext
    ):
        ctx_msg = system_msg.copy()
        user_msg = chat_ctx.messages[-1]
        #retriever = index.as_retriever()
        retriever = VectorIndexRetriever(
          index = index,
          similarity_top_k = 1,
          embed_model = embed_model
        )
        nodes = await retriever.aretrieve(user_msg.content)
        # ctx_msg.content += "\n\n---" + "\nContext that might help answer the user's question:"
        # for node in nodes:
        #     node_content = node.get_content(metadata_mode=MetadataMode.LLM)
        #     ctx_msg.content += f"\n\n{node_content}"
        
        ctx_msg.content = "Context that might help answer the user's question:"
        for node in nodes:
            node_content = node.get_content(metadata_mode=MetadataMode.LLM)
            ctx_msg.content += f"\n\n{node_content}"
        ctx_msg.content += "\n\n---\n\n" + system_msg.content
        
        chat_ctx.messages[0] = ctx_msg
        return assistant.llm.chat(chat_ctx=chat_ctx)

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    llm_plugin = WatsonXLLM(model="sdaia/allam-1-13b-instruct",
                            api_key="", #! Add your IBM WatsonX API key
                            project_id="") #! Add your IBM WatsonX Project ID
    
    assistant = VoicePipelineAgent(
        vad=silero.VAD.load(min_silence_duration=1.0),
        stt=openai.STT(detect_language=True),
        llm=llm_plugin,
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
        allow_interruptions=False,
        will_synthesize_assistant_reply=_will_synthesize_assistant_reply
    )

    # Start the voice assistant with the LiveKit room
    assistant.start(ctx.room)

    # Handle incoming chat messages
    chat = rtc.ChatManager(ctx.room)
    
    async def answer_from_text(txt: str):
        ctx_msg = system_msg.copy()
        chat_ctx = assistant.chat_ctx.copy()
        chat_ctx.append(role="user", text=txt)
        user_msg = chat_ctx.messages[-1]
        
        retriever = VectorIndexRetriever(
          index = index,
          similarity_top_k = 1,
          embed_model = embed_model
        )
        nodes = await retriever.aretrieve(user_msg.content)
        ctx_msg.content = "Context that might help answer the user's question:"
        for node in nodes:
            node_content = node.get_content(metadata_mode=MetadataMode.LLM)
            ctx_msg.content += f"\n\n{node_content}"
        ctx_msg.content += "\n\n---\n\n" + system_msg.content
        
        chat_ctx.messages[0] = ctx_msg
        stream = llm_plugin.chat(chat_ctx=chat_ctx)
        await assistant.say(stream)
    @chat.on("message_received")
    
    def on_chat_received(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(answer_from_text(msg.message))

    # Initial interaction
    await asyncio.sleep(1)
    await assistant.say("Hello, I'm مُرْشِدْ. Your assistant in your journey to Saudi Arabia. How can I help you today?", allow_interruptions=False)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, initialize_process_timeout=100, shutdown_process_timeout=100))