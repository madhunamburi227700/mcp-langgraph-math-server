# 🧮 LangGraph + MCP Tool Orchestration

This project demonstrates how to use [LangGraph](https://github.com/langchain-ai/langgraph) to orchestrate tool execution using a custom MCP (Model Context Protocol) server. It integrates natural language understanding via OpenAI and executes structured tool calls on a custom tool server (e.g., a calculator).

---

## 🚀 Features

- Natural language input → LLM (GPT-4o) → MCP tool selection
- LangGraph flow with `input → plan → call`
- MCP client-server architecture for modular tools
- Asynchronous execution
- CLI interface for interaction
- Visual flow rendering (optional)

---

## 📁 Project Structure

mcp-langgraph/
│
├── langgraph_flow/
│ └── tool_executor.py # MCPToolExecutor: handles tool listing/execution
│
├── mcp_server/
│ └── server.py # MCP Server that exposes tools (e.g., add, subtract)
│
├── prompts/
│ └── tool_selector_prompt.txt # Prompt to guide tool selection by LLM
│
├── main.py # Entry point (LangGraph + async CLI)
├── README.md # ← You're here
├── .env # Contains OPENAI_API_KEY
├── requirements.txt # Python dependencies

yaml
Copy
Edit

---

## 🧠 How It Works

1. User inputs a natural language query (e.g., "What is 5 plus 7?")
2. LLM (GPT-4o) interprets the query and outputs a JSON tool call:
   ```json
   {
     "tool_name": "add",
     "arguments": { "a": 5, "b": 7 }
   }
