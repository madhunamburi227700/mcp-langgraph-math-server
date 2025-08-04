import asyncio
import json
import logging
import os
from typing import Any
import httpx
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool, CallToolResult

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Configuration:
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")

    def load_config(self, file_path: str) -> dict[str, Any]:
        with open(file_path, "r") as f:
            return json.load(f)

    @property
    def openai_api_key(self) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        return self.api_key

class MCPServer:
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self.session: ClientSession | None = None
        self.exit_stack = None

    async def initialize(self) -> None:
        from contextlib import AsyncExitStack
        self.exit_stack = AsyncExitStack()
        await self.exit_stack.__aenter__()

        command = self.config["command"]
        args = self.config.get("args", [])
        server_params = StdioServerParameters(command=command, args=args)

        try:
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.session = session
            logging.info(f"Initialized server: {self.name}")
        except Exception as e:
            logging.error(f"Failed to initialize server '{self.name}': {e}")
            raise

    async def list_tools(self) -> list[Tool]:
        assert self.session is not None, "MCP server session not initialized"
        tools_response = await self.session.list_tools()
        tools = []
        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                tools.extend([Tool(**tool) if isinstance(tool, dict) else tool for tool in item[1]])
        return tools

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
        assert self.session is not None, "MCP server session not initialized"
        return await self.session.call_tool(tool_name, arguments)

    async def cleanup(self) -> None:
        if self.exit_stack:
            await self.exit_stack.aclose()

class LLMClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_response(self, messages: list[dict[str, str]]) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"Error from OpenAI: {e}")
            return "Error: Failed to get response from OpenAI."

class ChatSession:
    def __init__(self, servers: list[MCPServer], llm: LLMClient) -> None:
        self.servers = servers
        self.llm = llm

    async def start(self) -> None:
        for server in self.servers:
            await server.initialize()

        all_tools = []
        for server in self.servers:
            tools = await server.list_tools()
            all_tools.extend(tools)

        tool_descriptions = "\n".join(
            f"- {tool.name}: {tool.description}\n  Required args: {', '.join(tool.inputSchema.get('properties', {}).keys())}"
            for tool in all_tools
        )

        messages = [ {
            "role": "system",
            "content": (
                "You are a helpful assistant.\n"
                "When a tool is needed, respond ONLY with JSON in this format:\n"
                '{"tool": "tool_name", "arguments": {"arg_name": "value"}}\n'
                "Use only the correct argument names shown below. Do not add any explanation or extra text.\n\n"
                f"Available tools:\n{tool_descriptions}"
            )
        }]

        print("\nAvailable tools:")
        for tool in all_tools:
            print(f"- {tool.name}: {tool.description}")

        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break

            messages.append({"role": "user", "content": user_input})
            llm_response = self.llm.get_response(messages)
            print("\nLLM Response:\n", llm_response)

            if llm_response.startswith("{"):
                try:
                    parsed = json.loads(llm_response)
                    tool_name = parsed["tool"]
                    arguments = parsed.get("arguments", {})

                    for server in self.servers:
                        tools = await server.list_tools()
                        if any(tool.name == tool_name for tool in tools):
                            print(f"\nExecuting {tool_name} with args: {arguments}")
                            result = await server.execute_tool(tool_name, arguments)
                            print("Tool Output:")
                            for content in result.content:
                                if content.type == "text":
                                    print(content.text)
                            break
                    else:
                        print("Tool not found")
                except Exception as e:
                    print(f"Error parsing LLM response: {e}")
            else:
                print(f"OpenAI: {llm_response}")

async def main():
    config = Configuration()
    servers_config = config.load_config("mcp_simple_chatbot/servers_config.json")

    servers = [
        MCPServer(name, conf)
        for name, conf in servers_config["mcpServers"].items()
    ]
    llm = LLMClient(config.openai_api_key)

    chat = ChatSession(servers, llm)
    await chat.start()

if __name__ == "__main__":
    asyncio.run(main())