import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager 

# Import your tool server
from .tool_server import UniversalToolServer

# --- Configuration ---

# Define the project root (rml-generator/)
PROJECT_ROOT = Path(__file__).parent.parent 

# Initialize the tool server with the correct root path
tool_server = UniversalToolServer(root_path=PROJECT_ROOT)

# --- 2. CREATE THE NEW LIFESPAN FUNCTION ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the tool server.
    """
    # This runs on startup
    print("Lifespan: Tool server starting up...")
    await tool_server.__aenter__()
    
    yield # This is where your application runs
    
    # This runs on shutdown
    print("Lifespan: Tool server shutting down...")
    await tool_server.__aexit__(None, None, None)


app = FastAPI(
    title="Universal Tool Server",
    description="Exposes IoT and FileSystem tools over an API.",
    lifespan=lifespan  # --- 3. PASS THE LIFESPAN FUNCTION HERE ---
)

# --- API Models ---
class ToolCallRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any]

# --- API Endpoints ---

@app.get("/tools", description="Get the list of available tools in MCP format.")
async def get_tools():
    """
    This endpoint provides the tool definitions (the "MCP" part).
    """
    return await tool_server.get_mcp_tools()

@app.post("/call", description="Execute a specific tool.")
async def call_tool_endpoint(request: ToolCallRequest):
    """
    This endpoint executes a tool and returns the JSON result.
    """
    result = await tool_server.call_tool(request.tool_name, request.args)
    return result

# --- Run the Server ---
if __name__ == "__main__":
    print(f"Starting server, serving tools from project root: {PROJECT_ROOT}")
    # Run with the module command: python -m src.api_server
    uvicorn.run("src.api_server:app", host="127.0.0.1", port=8000, reload=True)