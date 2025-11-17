import json
from typing import List, Dict
from openai import OpenAI
from contextlib import AsyncExitStack
import httpx
import logging

import openai

import prompt

logger = logging.getLogger(__name__)


# Import the tool server for type hinting
from .tool_server import UniversalToolServer 

class ToolLLM:
    
    """
    High-level helper that:
      - Brings up a tool server client & OpenAI client in one context
      - Caches the merged tool list
    """

    def __init__(
        self, 
        llm_base_url: str, 
        llm_api_key: str, 
        model: str, 
        tool_server_base_url: str 
    ):
        self.llm = OpenAI(base_url=llm_base_url, api_key=llm_api_key, timeout=300.0)
        self.model = model
        self.tool_server_base_url = tool_server_base_url 
        self._tools: List[dict] = None
        self.http_client = httpx.AsyncClient()

    async def __aenter__(self):
        # Enter the httpx client context
        await self.http_client.__aenter__()
        
        # Fetch tools from the API server
        try:
            logger.info(f"Fetching tools from {self.tool_server_base_url}/tools")
            response = await self.http_client.get(f"{self.tool_server_base_url}/tools")
            response.raise_for_status() # Raise an error on a bad response (4xx, 5xx)
            self._tools = response.json()
            logger.info(f"Successfully fetched {len(self._tools)} tools.")
        except httpx.RequestError as e:
            logger.error(f"Error fetching tools: {e}")
            # Exit the client if we fail, as we can't proceed
            await self.http_client.__aexit__(type(e), e, e.__traceback__)
            raise
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Exit the httpx client context
        if self.http_client:
            await self.http_client.__aexit__(exc_type, exc, tb)


    async def ask(self, query: str) -> str:

        try:
            if self._tools is None:
                raise RuntimeError("Tools not loaded. Use 'async with ToolLLM(...)'.")
            logger.info(f"Asking LLM: {query}")
            messages = [
                {"role": "user", "content": query}
            ]
        
            resp = self.llm.chat.completions.create(
                model=self.model, 
                messages=messages,
                #timeout=60.0,
                tools=self._tools,
                tool_choice="auto"  # Let the LLM decide to use tools
            )

            msg = resp.choices[0].message
            
            if msg.tool_calls:
                messages.append(msg)
                for call in msg.tool_calls:
                    try:
                        args = json.loads(call.function.arguments)
                        logger.info(f"LLM requesting tool '{call.function.name}' via API...")
                        api_payload = {"tool_name": call.function.name, "args": args}
                        response = await self.http_client.post(
                            f"{self.tool_server_base_url}/call",
                            json=api_payload
                        )
                        response.raise_for_status()
                        result = response.json()

                        
                        messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
                    except Exception as e:
                        error_msg = f"Error calling tool '{call.function.name}': {e}"
                        logger.error(error_msg)
                        messages.append({"role": "tool", "tool_call_id": call.id, "content": error_msg})

                        
                final_resp = self.llm.chat.completions.create(
                    model=self.model, messages=messages, tool_choice="none"
                )
                return final_resp.choices[0].message.content
            else:
                return msg.content
            
        
        except openai.APITimeoutError as e: # Catch the specific APITimeoutError
            print(f"LLM API call timed out: {e}")
            # Handle the timeout appropriately
            return f"Error: LLM API call timed out. Details: {e}"
            # Or raise a custom exception, return None, etc.
        except httpx.TimeoutException as e: # Optionally catch the underlying httpx timeout
            print(f"HTTP request timed out: {e}")
            return f"Error: HTTP request timed out. Details: {e}"
        except openai.APIError as e: # Catch other potential API errors
            print(f"LLM API error: {e}")
            return f"Error: LLM API error. Details: {e}"
        except Exception as e: # Catch any other unexpected errors
            print(f"An unexpected error occurred in LLM client: {e}")
            return f"Error: Unexpected error in LLM client. Details: {e}"