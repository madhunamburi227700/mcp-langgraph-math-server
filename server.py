import asyncio
from typing import TypedDict
from mcp.types import Tool, TextContent
from mcp.server import Server
from mcp.server.stdio import stdio_server

from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda

# -----------------------
# LangGraph Flow State
# -----------------------
class FlowState(TypedDict):
    input: str
    output: str

# -----------------------
# LangGraph Nodes (Tool Logic)
# -----------------------
def add_node(state: FlowState) -> dict:
    try:
        nums = list(map(float, state["input"].split()))
        result = sum(nums)
        return {"output": f"add: {nums} -> {result}"}
    except Exception as e:
        return {"output": f"Error in add: {e}"}

def subtract_node(state: FlowState) -> dict:
    try:
        nums = list(map(float, state["input"].split()))
        result = nums[0]
        for n in nums[1:]:
            result -= n
        return {"output": f"subtract: {nums} -> {result}"}
    except Exception as e:
        return {"output": f"Error in subtract: {e}"}

def multiply_node(state: FlowState) -> dict:
    try:
        nums = list(map(float, state["input"].split()))
        result = 1
        for n in nums:
            result *= n
        return {"output": f"multiply: {nums} -> {result}"}
    except Exception as e:
        return {"output": f"Error in multiply: {e}"}

def divide_node(state: FlowState) -> dict:
    try:
        nums = list(map(float, state["input"].split()))
        result = nums[0]
        for n in nums[1:]:
            if n == 0:
                return {"output": f"Division by zero in {nums}"}
            result /= n
        return {"output": f"divide: {nums} -> {result}"}
    except Exception as e:
        return {"output": f"Error in divide: {e}"}

def evaluate_expression_node(state: FlowState) -> dict:
    try:
        expr = state["input"]
        result = eval(expr, {"__builtins__": None}, {})
        return {"output": f"result: {expr} = {result}"}
    except Exception as e:
        return {"output": f"Error in expression: {e}"}

# -----------------------
# LangGraph Flow Builder
# -----------------------
def create_math_flow(operation: str):
    graph = StateGraph(FlowState)

    node_map = {
        "add": add_node,
        "subtract": subtract_node,
        "multiply": multiply_node,
        "divide": divide_node,
        "evaluate_expression": evaluate_expression_node,
    }

    if operation not in node_map:
        raise ValueError(f"Unsupported operation: {operation}")

    graph.add_node(operation, RunnableLambda(node_map[operation]))
    graph.set_entry_point(operation)
    graph.set_finish_point(operation)
    return graph.compile()

# -----------------------
# MCP Tool Server
# -----------------------
async def serve():
    server = Server("mcp-langgraph-math")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="add",
                description="Add space-separated numbers like '3 5 2'",
                inputSchema={"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]}
            ),
            Tool(
                name="subtract",
                description="Subtract space-separated numbers like '10 4 1'",
                inputSchema={"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]}
            ),
            Tool(
                name="multiply",
                description="Multiply space-separated numbers like '2 3 4'",
                inputSchema={"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]}
            ),
            Tool(
                name="divide",
                description="Divide numbers like '100 5 2'",
                inputSchema={"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]}
            ),
            Tool(
                name="evaluate_expression",
                description="Evaluate full math expression like '5*2+3'",
                inputSchema={"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]}
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name in {"add", "subtract", "multiply", "divide", "evaluate_expression"}:
                flow = create_math_flow(name)
                result = flow.invoke(FlowState(input=arguments["input"], output=""))
                return [TextContent(type="text", text=result["output"])]
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

# -----------------------
# Run the server
# -----------------------
if __name__ == "__main__":
    asyncio.run(serve())
