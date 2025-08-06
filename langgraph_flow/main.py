import os
import json
from typing import TypedDict, cast
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langgraph_flow.tool_executor import MCPToolExecutor
import re

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# ----- LangGraph State -----
class FlowState(TypedDict):
    input: str
    tool_name: str
    arguments: dict
    output: str

# ----- Load LLM & Prompt -----
with open("prompts/tool_selector_prompt.txt") as f:
    raw_prompt = f.read()

prompt = PromptTemplate.from_template(raw_prompt)
llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

# Initialize the tool executor
executor = MCPToolExecutor("calculator", command="python", args=["mcp_server/server.py"])

# ----- LangGraph Nodes -----
def input_node(state: FlowState) -> FlowState:
    return state

import re

async def plan_tool_call(state: FlowState) -> FlowState:
    input_text = state["input"]
    formatted_prompt = prompt.format(input=input_text)
    response = await llm.ainvoke([HumanMessage(content=formatted_prompt)])
    print("🧠 LLM Raw Response:", response.content)

    try:
        content = response.content
        if isinstance(content, list):
            content = "".join(str(part) for part in content)

        # ✅ Remove code block markdown (```json ... ```)
        content = re.sub(r"```(?:json)?\n([\s\S]*?)```", r"\1", content).strip()

        parsed = json.loads(content)
        return cast(FlowState, {
            **state,
            "tool_name": parsed["tool_name"],
            "arguments": parsed["arguments"]
        })
    except Exception as e:
        return cast(FlowState, {
            **state,
            "output": f"❌ Failed to parse tool call: {e}\nRaw response: {response.content}"
        })


async def call_mcp_tool(state: FlowState) -> FlowState:
    tool_name = state["tool_name"]
    arguments = state["arguments"]

    print(f"🔍 Calling tool: {tool_name}")
    print(f"📦 Arguments: {arguments}")

    # Validate tool exists
    available_tools = [t.name for t in await executor.list_tools()]
    if tool_name not in available_tools:
        return cast(FlowState, {
            **state,
            "output": f"❌ Unknown tool selected: '{tool_name}'. Available tools: {available_tools}"
        })

    try:
        result = await executor.execute_tool(tool_name, arguments)
        output = "\n".join(c.text for c in result.content if c.type == "text")
        return cast(FlowState, {**state, "output": output})
    except Exception as e:
        return cast(FlowState, {**state, "output": f"❌ MCP call failed: {e}"})


# ----- LangGraph Flow -----
def build_flow() -> Runnable:
    builder = StateGraph(FlowState)
    builder.add_node("input", input_node)
    builder.add_node("plan", plan_tool_call)
    builder.add_node("call", call_mcp_tool)

    builder.set_entry_point("input")
    builder.add_edge("input", "plan")
    builder.add_edge("plan", "call")
    builder.set_finish_point("call")

    return builder.compile()

# ----- Async Main Runner -----
import asyncio

async def main():
    await executor.initialize()  # Initialize MCP client
    tools = await executor.list_tools()
    print("🔧 Available tools:", [t.name for t in tools])
    flow = build_flow()

    while True:
        user_input = input("🧠 Ask me to calculate something: ")
        if user_input.strip().lower() in ["exit", "quit"]:
            break

        state: FlowState = {
            "input": user_input,
            "tool_name": "",
            "arguments": {},
            "output": ""
        }
        result = await flow.ainvoke(state)
        print("🧾 Result:", result["output"])

    await executor.cleanup()  # Properly close MCP client

if __name__ == "__main__":
    asyncio.run(main())
