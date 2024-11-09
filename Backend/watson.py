from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Awaitable, MutableSet

import httpx
import requests
from requests.exceptions import RequestException
from livekit.agents import llm
from livekit.agents import utils
from livekit.agents.pipeline.pipeline_agent import EventTypes
import sys

def generate_prompt_from_history(chat_ctx):
  prompt = ""
  for message in chat_ctx.messages:
    role, content = message.role, message.content
    if role == "system":
        prompt += f"<s> [INST]<<SYS>>\n{content}\n<</SYS>>\n\n"
    elif role == "assistant":
        prompt += f"{content} </s><s> [INST] "
    elif role in {"human", "user"}:
        prompt += f"{content} [/INST] "
  return prompt

@dataclass
class LLMOptions:
    model: str
    user: str | None
    temperature: float | None


class WatsonXLLM(llm.LLM, utils.EventEmitter[EventTypes]):
    def __init__(
        self,
        *,
        model: str = "sdaia/allam-1-13b-instruct",
        api_key: str | None = None,
        project_id: str | None = None,
        url: str = "https://eu-de.ml.cloud.ibm.com",  # Default URL
        user: str | None = None,
        temperature: float | None = 0.7,
        max_new_tokens: int = 400,
        decoding_method: str = "greedy",
        top_p: float = 1,
        repetition_penalty: float = 1.0,
        timeout: int = 60,
    ) -> None:
        super().__init__()
        api_key = api_key or os.environ.get("IBM_WATSONX_API_KEY")
        project_id = project_id or os.environ.get("IBM_WATSONX_PROJECT_ID")

        if api_key is None or project_id is None:
            raise ValueError("WatsonX API key and Project ID are required")

        self._opts = LLMOptions(model=model, user=user, temperature=temperature)
        self._client = IBMWatsonXAIWrapper(
            api_key=api_key,
            project_id=project_id,
            url=url,
            model_id=model,
            max_new_tokens=max_new_tokens,
            decoding_method=decoding_method,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            timeout=timeout,
        )
        self._running_fncs: MutableSet[asyncio.Task[Any]] = set()

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        fnc_ctx: llm.FunctionContext | None = None,  # Not used in this implementation
        temperature: float | None = None,  # For future compatibility, if WatsonX supports it.
        n: int | None = 1, # Not used in this implementation
        parallel_tool_calls: bool | None = None, # Not used in this implementation
    ) -> "WatsonXLLMStream":  # Return the specific stream type

        user = self._opts.user  # Not used in current WatsonX implementation
        if temperature is None:
            temperature = self._opts.temperature  # For future compatibility


        prompt = generate_prompt_from_history(chat_ctx)
        print("_"*50)
        print("Input prompt:",prompt)
        print("_"*50)
        return WatsonXLLMStream(llm=self, prompt=prompt, client=self._client, chat_ctx=chat_ctx)


class WatsonXLLMStream(llm.LLMStream):
    def __init__(
        self,
        llm: WatsonXLLM,
        prompt: str,
        client: IBMWatsonXAIWrapper,
        chat_ctx: llm.ChatContext,
    ) -> None:
        super().__init__(llm=llm, chat_ctx=chat_ctx, fnc_ctx=None) # No function context for now
        self._prompt = prompt
        self._client = client
        self._response = None

    async def _main_task(self) -> None: 
        try:
            response_text = self._client.generate_text(self._prompt)
            chunk = llm.ChatChunk(
                choices=[
                    llm.Choice(
                        delta=llm.ChoiceDelta(content=response_text, role="assistant"),
                        index=0,
                    )
                ],
                request_id="watsonx_request_id", # Replace with actual request ID if available
            )
            await self._event_ch.asend(chunk)  # Send the chunk
        except Exception as e:  # Catch and log errors during generation
            # You might want to re-raise the exception or handle it differently
            # depending on your error handling strategy.
            raise  # Re-raise for now so the error is propagated

    async def aclose(self) -> None:
        return await super().aclose()

    async def __anext__(self) -> llm.ChatChunk:
        if self._response is None:
            response_text = self._client.generate_text(self._prompt)
            self._response = response_text  # Store the entire response
            # Simulate streaming by yielding a single chunk
            return llm.ChatChunk(
                choices=[
                    llm.Choice(
                        delta=llm.ChoiceDelta(content=response_text, role="assistant"),
                        index=0,  # Only one choice for now
                    )
                ],
                request_id="watsonx_request_id"
            )        
        raise StopAsyncIteration

class IBMWatsonXAIWrapper:
    def __init__(self, api_key, project_id, url, model_id="sdaia/allam-1-13b-instruct", max_new_tokens=400, decoding_method="greedy", temperature=0.7, top_p=1, repetition_penalty=1.0, timeout=60):
        self.api_key = api_key
        self.project_id = project_id
        self.base_url = url
        self.url = f"{url}/ml/v1/text/generation?version=2023-05-29"
        self.model_id = model_id
        self.timeout = timeout
        
        self.parameters = {
            "decoding_method": decoding_method,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty
        }
        
        self.access_token = self.get_access_token()
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        print(f"Debug: Initialized with model_id: {self.model_id}")

    def get_access_token(self):
        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key
        }
        
        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()["access_token"]
        except RequestException as e:
            print(f"Error obtaining access token: {str(e)}")
            sys.exit(1)

    def generate_text(self, prompt):
        body = {
            "input": f"<s> [INST] {prompt} [/INST]",
            "parameters": self.parameters,
            "model_id": self.model_id,
            "project_id": self.project_id
        }
        try:
            print("Generating response...", end="", flush=True)
            response = requests.post(
                self.url,
                headers=self.headers,
                json=body,
                timeout=self.timeout
            )
            print("\rGeneration complete.   ")
            
            if response.status_code != 200:
                raise Exception(f"Non-200 response: {response.text}")
            
            data = response.json()
            return data.get('results', [{}])[0].get('generated_text', "No text generated")
        except RequestException as e:
            print(f"\nError: API request failed - {str(e)}")
            return f"Error: API request failed - {str(e)}"
        except Exception as e:
            print(f"\nError: {str(e)}")
            return f"Error: {str(e)}"