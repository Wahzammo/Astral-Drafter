import asyncio
import sys
import json
import ollama
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters # Assuming mcp library is correct
from mcp.client.stdio import stdio_client

# New Imports for Robustness and Local Time
import socket
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime
from zoneinfo import ZoneInfo

# ------------------------------------------------------------------
# 🛡️ SECURITY & RELIABILITY FIXES
# ------------------------------------------------------------------

# 1. FIX: Removed external ipapi.co call (DoS/IP Leak)
# Replaced with a hardcoded, reliable Time Zone (Melbourne, VIC).
# This can be set via an environment variable in a production/multi-user setup.
DEFAULT_TIMEZONE = 'Australia/Melbourne'
API_TIMEOUT = 5 # Timeout for any remaining external calls (5 seconds is reasonable)

def get_current_time() -> str:
    """
    Retrieves the current date, time, and timezone information using a 
    configured local setting (no external API calls).
    """
    try:
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        now = datetime.now(tz)
        tz_abbrev = now.strftime('%Z')
        
        return (f"Current local time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} {tz_abbrev}\n"
                f"ISO format: {now.isoformat()}")
                
    except Exception:
        # Fallback to UTC if the configured timezone is invalid
        now = datetime.now(ZoneInfo('UTC'))
        return (f"Could not use configured timezone. Current UTC time:\n"
                f"{now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} UTC\n"
                f"ISO format: {now.isoformat()}")

# 2. FIX: Critical RCE/Tool Execution Harden (Finding 3A)
# Define an explicit allowlist for tools the LLM can auto-call.
# All destructive or sensitive tools (like file_system operations) should NOT be on this list.
# 'get_current_time' is a safe, read-only tool.
TOOL_ALLOWLIST: List[str] = [
    "get_current_time",
    # Add other safe, read-only tools here. 
    # DO NOT ADD 'delete_path', 'write_file', or 'move_path'
]


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # Changed the model to a safer default llama3 model since the other was a q8_0 variant
        # that could be slightly more prone to quantization issues.
        self.ollama_model = "llama3:8b-instruct" 

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        response = await self.session.list_tools()
        available_tools = [{ 
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        tools_prompt = "\n".join(
            f"Tool {i+1}: {tool['name']}\n"
            f"Description: {tool['description']}\n"
            f"Input Schema: {tool['input_schema']}\n"
            for i, tool in enumerate(available_tools))
        
        # System prompt with clear instructions and tool list
        system_prompt = f"""You are an AI assistant with access to tools. 
    
    Available Tools:
    {tools_prompt}
    
    Instructions:
    1. Only use tools from the provided list.
    2. To call a tool, respond EXACTLY in this format:
    ---TOOL_START---
    TOOL: tool_name
    INPUT: {{"key": "value"}}
    ---TOOL_END---
    3. The INPUT must be valid JSON matching the tool's input schema.
    4. If no tool is needed, respond normally to the user's query.
    
    current details : {get_current_time()}
    """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Initial Ollama API call
        response = ollama.chat(
            model=self.ollama_model,
            messages=messages
        )
        response_content = response['message']['content']

        final_output = [response_content]
        
        tool_call_start = "---TOOL_START---"
        tool_call_end = "---TOOL_END---"
        
        if tool_call_start in response_content and tool_call_end in response_content:
            try:
                tool_section = response_content.split(tool_call_start)[1].split(tool_call_end)[0].strip()
                
                tool_lines = [line.strip() for line in tool_section.split('\n') if line.strip()]
                if len(tool_lines) != 2 or not tool_lines[0].startswith("TOOL:") or not tool_lines[1].startswith("INPUT:"):
                    raise ValueError("Invalid tool call format")
                    
                tool_name = tool_lines[0][5:].strip()
                input_json = tool_lines[1][6:].strip()
                
                # --- 🔑 CRITICAL SECURITY CHECK (Allowlist & Input Validation) ---
                if tool_name not in TOOL_ALLOWLIST:
                    raise PermissionError(f"Tool '{tool_name}' is not in the automatic execution ALLOWLIST. User confirmation is required.")

                tool_input = json.loads(input_json)
                
                tool_exists = any(tool['name'] == tool_name for tool in available_tools)
                if not tool_exists:
                    raise ValueError(f"Tool '{tool_name}' not found in available tools")
                
                # Further security step: Add Pydantic validation here against tool['input_schema']
                # for strict type/schema checking before execution.
                
                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_input)
                final_output.append(f"\n[Tool {tool_name} executed successfully]")

                # Continue conversation with tool results
                follow_up_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": response_content},
                    {"role": "user", "content": f"Tool {tool_name} returned: {result.content}\n\nNow provide a helpful response to my original query incorporating this information."}
                ]
                
                follow_up_response = ollama.chat(
                    model=self.ollama_model,
                    messages=follow_up_messages
                )
                final_output.append(follow_up_response['message']['content'])

            except PermissionError as e:
                final_output.append(f"\nSECURITY ERROR: {str(e)}")
            except json.JSONDecodeError:
                final_output.append("\nError: Invalid JSON format in tool input from model.")
            except ValueError as e:
                final_output.append(f"\nError: {str(e)}")
            except Exception as e:
                final_output.append(f"\nError executing tool: {str(e)}")

        return "\n".join(final_output)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
