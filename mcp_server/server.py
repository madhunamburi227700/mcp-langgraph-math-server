import asyncio
import math
from pydantic import BaseModel
from mcp.types import Tool, TextContent
from mcp.server import Server
from mcp.server.stdio import stdio_server

class CalcInput(BaseModel):
    numbers: list[float]

class ExpressionInput(BaseModel):
    expression: str

async def serve() -> None:
    server = Server("calculator")

    # ✅ List of available tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name="add", description="Add numbers", inputSchema=CalcInput.model_json_schema()),
            Tool(name="subtract", description="Subtract numbers", inputSchema=CalcInput.model_json_schema()),
            Tool(name="multiply", description="Multiply numbers", inputSchema=CalcInput.model_json_schema()),
            Tool(name="divide", description="Divide numbers", inputSchema=CalcInput.model_json_schema()),
            Tool(name="evaluate_expression", description="Evaluate a math expression", inputSchema=ExpressionInput.model_json_schema()),
        ]

    # ✅ Tool executor
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name in {"add", "subtract", "multiply", "divide"}:
                data = CalcInput(**arguments)
                nums = data.numbers
                if len(nums) < 2:
                    return [TextContent(type="text", text="❌ Provide at least two numbers.")]
                result = nums[0]
                if name == "add":
                    result = sum(nums)
                elif name == "subtract":
                    for n in nums[1:]: result -= n
                elif name == "multiply":
                    result = 1
                    for n in nums: result *= n
                elif name == "divide":
                    for n in nums[1:]:
                        if n == 0:
                            return [TextContent(type="text", text="❌ Division by zero")]
                        result /= n
                return [TextContent(type="text", text=f"✅ {name}: {nums} -> {result}")]

            elif name == "evaluate_expression":
                expr = ExpressionInput(**arguments).expression
                # ⚠️ Safe eval
                allowed_names = {
                    k: v for k, v in math.__dict__.items() if not k.startswith("__")
                }
                result = eval(expr, {"__builtins__": None}, allowed_names)
                return [TextContent(type="text", text=f"✅ Expression: {expr} -> {result}")]

            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error: {e}")]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    asyncio.run(serve())
