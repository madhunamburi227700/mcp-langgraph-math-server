# mcp-langgraph-math-server
An MCP (Model Context Protocol) tool server that uses LangGraph flows to perform basic math operations like add, subtract, multiply, divide, and evaluate expressions. Powered by LangChain, LangGraph, and OpenAI.

# MCP LangGraph Math Server

This project is a Model Context Protocol (MCP) server that exposes math tools using LangGraph flows. It supports operations such as:

- Addition (`add`)
- Subtraction (`subtract`)
- Multiplication (`multiply`)
- Division (`divide`)
- Math expression evaluation (`evaluate_expression`)

These tools are defined using LangChain’s `RunnableLambda` and orchestrated by LangGraph. The server runs over standard IO and is compatible with GPT-based chatbots using MCP.
