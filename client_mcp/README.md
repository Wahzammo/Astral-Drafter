# MCP Client

This repository contains a client implementation for interacting with MCP (Model-Client-Plugin) server scripts. It enables communication between Ollama LLM models and tool-based servers through a standardized interface.

## Overview

The MCP Client provides a bridge between Ollama language models and server-side tools. It:

1. Connects to MCP-compatible server scripts (Python or JavaScript)
2. Discovers available tools exposed by the server
3. Processes user queries through Ollama LLM
4. Detects when the LLM wants to use tools and executes them
5. Returns results back to the LLM to generate a final response

## Features

- **Tool Discovery**: Automatically detects and lists tools from connected servers
- **Interactive Chat Loop**: Provides a command-line interface for interacting with the system
- **Timezone Awareness**: Includes current time and timezone information with each query
- **Error Handling**: Robust error handling for tool calls and response processing

## Prerequisites

- Python 3.7+
- MCP library
- Ollama (with llama3.2:3b-instruct-q8_0 model or similar)
- ZoneInfo library (Python 3.9+ or backported)

## Installation

1. Install the required dependencies:
   ```bash
   pip install mcp-client ollama zoneinfo
   ```

2. Ensure Ollama is installed and the specified model is downloaded:
   ```bash
   ollama pull llama3.2:3b-instruct-q8_0
   ```

## Usage

Run the client by specifying the path to an MCP-compatible server script:

```bash
python client.py path/to/server_script.py
```

The client supports both Python (.py) and JavaScript (.js) server scripts.

## API Reference

### `MCPClient` Class

The main class handling the MCP client functionality.

#### `__init__()`

Initializes the client with default configuration.

#### `connect_to_server(server_script_path: str)`

Connects to an MCP server specified by the script path.

**Parameters:**
- `server_script_path` (str): Path to the server script (.py or .js)

**Raises:**
- `ValueError`: If the server script is not a .py or .js file

#### `process_query(query: str) -> str`

Processes a user query using Ollama and available tools.

**Parameters:**
- `query` (str): The user's input query

**Returns:**
- String containing the LLM's response, potentially including tool execution results

#### `chat_loop()`

Runs an interactive chat loop for continuous user interaction.

#### `cleanup()`

Cleans up resources and connections.

### Helper Functions

#### `get_current_time() -> str`

Retrieves the current date, time, and timezone information.

**Returns:**
- Formatted string with local time in both 12-hour and ISO formats, along with timezone abbreviation

## Tool Calling Format

The LLM will call tools using a specific format:

```
---TOOL_START---
TOOL: tool_name
INPUT: {"key": "value"}
---TOOL_END---
```

The client parses this format, validates the tool exists, and then calls the appropriate tool with the provided input parameters.

## Error Handling

The client handles various error scenarios:
- Invalid JSON in tool input
- Non-existent tools
- Server connection issues
- General exceptions during tool execution

## Example Workflow

1. Client connects to an MCP server
2. User enters a query
3. Query is sent to Ollama with available tools information
4. Ollama decides if a tool is needed
5. If yes, the client extracts the tool call and executes it
6. Tool results are sent back to Ollama for final response
7. Complete response is displayed to the user

## Customization

- Change the Ollama model by modifying `self.ollama_model` in the `__init__` method
- Adjust the system prompt in `process_query` to change how the LLM interacts with tools
- Modify `get_current_time()` if different timezone handling is required

## Limitations

- Only supports synchronous tool calls (one at a time)
- Limited to CLI interaction
- Requires server script to follow MCP protocol
