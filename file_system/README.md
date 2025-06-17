# File Manager MCP Server

This repository contains a FastMCP server implementation that provides file system management capabilities. The server exposes various tools for interacting with files and directories through a standardized MCP (Model-Client-Plugin) interface.

## Overview

The File Manager MCP server allows language models or other clients to perform common file system operations including:

- Creating, reading, updating, and deleting files and directories
- Moving and copying files
- Listing directory contents
- Getting file information and metadata
- Changing the working directory
- Generating file previews for image files

## Features

- **File Operations**: Complete CRUD operations for files and directories
- **Path Management**: Tools for navigating and manipulating filesystem paths
- **Resource Access**: URI-based access to file information
- **File Preview**: Optional image thumbnails for supported file types
- **Flexible Path Handling**: Support for relative paths, absolute paths, and user home directory expansion

## Prerequisites

- Python 3.6+
- FastMCP library
- python-magic library (optional, for file preview functionality)
- PIL/Pillow (optional, for image manipulation)

## Installation

1. Install the required dependencies:
   ```bash
   pip install fastmcp python-magic pillow
   ```

## Server Initialization

The server initializes with the name "File Manager" and sets up a lifespan context manager for resource initialization and cleanup:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("File Manager", dependencies=["python-magic"])

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialize any resources needed for the file manager"""
    yield {"initialized_at": datetime.now().isoformat()}

mcp = FastMCP("File Manager", lifespan=lifespan)
```

## API Reference

### Resource Handlers

#### `get_file_info(path: str) -> str`

Returns information about a file or directory at the specified path.

**URI Format**: `file://{path}`

**Returns**:
- For directories: List of contents
- For files: Size, modification time, and creation time

### File Operation Tools

#### `create_directory(path: str, parents: bool = False) -> str`

Creates a new directory at the specified path.

**Parameters**:
- `path`: The path where the directory should be created
- `parents`: If True, create parent directories as needed

#### `create_file(path: str, content: Optional[str] = None) -> str`

Creates a new file at the specified path with optional content.

**Parameters**:
- `path`: The path where the file should be created
- `content`: Optional content to write to the file

#### `write_file(path: str, content: str, append: bool = False) -> str`

Writes content to a file, either overwriting or appending.

**Parameters**:
- `path`: Path to the file
- `content`: Content to write
- `append`: If True, append to the file instead of overwriting

#### `read_file(path: str) -> str`

Reads the contents of a file.

**Parameters**:
- `path`: Path to the file

#### `list_directory(path: str = ".", detailed: bool = False) -> str`

Lists contents of a directory.

**Parameters**:
- `path`: Path to the directory (defaults to current directory)
- `detailed`: If True, include detailed information about each item

#### `delete_path(path: str, recursive: bool = False) -> str`

Deletes a file or directory.

**Parameters**:
- `path`: Path to delete
- `recursive`: If True, delete directories recursively (including contents)

#### `move_path(source: str, destination: str) -> str`

Moves or renames a file or directory.

**Parameters**:
- `source`: Current path
- `destination`: New path

#### `copy_path(source: str, destination: str) -> str`

Copies a file or directory.

**Parameters**:
- `source`: Path to copy from
- `destination`: Path to copy to

#### `get_current_directory() -> str`

Returns the current working directory.

#### `change_directory(path: str) -> str`

Changes the current working directory.

**Parameters**:
- `path`: Path to change to

#### `get_file_preview(path: str) -> Optional[Image]`

Generates a preview image of a file if possible (primarily for image files).

**Parameters**:
- `path`: Path to the file

**Returns**:
- `Image` object containing a thumbnail if the file is an image
- `None` if the file is not an image or if there was an error

### Prompt Templates

#### `file_operation_prompt(operation: str, target: str) -> list[base.Message]`

Template for file operation prompts to guide interactions.

**Parameters**:
- `operation`: The operation to perform (e.g., "read", "write", "delete")
- `target`: The target file or directory

## Path Handling

All tools consistently handle paths using Python's `pathlib` with:
- User home directory expansion (`~` gets expanded)
- Conversion to absolute paths
- Proper error handling for non-existent paths

## Error Handling

Each tool includes robust error handling for common scenarios:
- Non-existent files or directories
- Permission issues
- Type mismatches (e.g., trying to read a directory as a file)
- Empty directory deletion without recursive flag

## Running the Server

To start the MCP server:

```bash
python file_system.py
```

## Usage with MCP Clients

This server can be used with any MCP-compatible client, allowing language models to interact with the file system through natural language requests.

## Security Considerations

- This server provides direct file system access
- Use appropriate security measures when deploying
- Consider implementing path constraints to prevent access to sensitive system areas
