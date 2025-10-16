from pathlib import Path
from typing import Optional, Any
import os
import shutil
from datetime import datetime
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base # Only base is imported, Context removed as unused

# ------------------------------------------------------------------
# 🛡️ CRITICAL SECURITY CONFIGURATION & HELPER
# ------------------------------------------------------------------

# 1. DEFINE THE SECURE WORKSPACE ROOT
# This must be a path *outside* of your source code and critical system folders.
# Set via environment variable for security, falling back to a safe default.
# NOTE: Using resolve() is essential for normalization.
BASE_DIR = Path(os.environ.get("MCP_WORKSPACE", "/tmp/mcp_workspace")).resolve()

# Ensure the base directory exists when the server starts
if not BASE_DIR.exists():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created secure workspace directory at: {BASE_DIR}")


class PermissionError(Exception):
    """Custom exception for file access violations."""
    pass

def resolve_and_check_path(path_input: str, follow_symlinks: bool = True) -> Path:
    """
    Validates that the resolved path is strictly within the BASE_DIR.
    This prevents Path Traversal (CWE-22) and Absolute Path attacks.
    """
    # 1. Join the base path and the user input
    unsafe_full_path = BASE_DIR / path_input
    
    # 2. Resolve/Normalize: This removes '..', '//', and resolves symlinks
    # Using resolve() is critical for canonicalization.
    try:
        resolved_path = unsafe_full_path.expanduser().resolve(strict=follow_symlinks)
    except FileNotFoundError:
        # Allow non-existent paths (like for create_file) to be checked
        resolved_path = unsafe_full_path.expanduser().resolve(strict=False)

    # 3. Validate: Check if the resolved path starts with the secure BASE_DIR path string
    # String comparison is needed to ensure the path doesn't escape the boundary.
    if not str(resolved_path).startswith(str(BASE_DIR)):
        raise PermissionError(f"Access denied: Operation is outside the authorized workspace: {BASE_DIR}")
    
    return resolved_path

# ------------------------------------------------------------------
# MCP SERVER SETUP
# ------------------------------------------------------------------

# Create the MCP server
mcp = FastMCP("File Manager", dependencies=["python-magic"])

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialize any resources needed for the file manager"""
    # Ensure BASE_DIR exists (already checked above, but good for process isolation)
    if not BASE_DIR.exists():
         BASE_DIR.mkdir(parents=True, exist_ok=True)
         
    yield {"initialized_at": datetime.now().isoformat(), "workspace": str(BASE_DIR)}

mcp = FastMCP("File Manager", lifespan=lifespan)


# ------------------------------------------------------------------
# 🛡️ SECURE TOOL IMPLEMENTATIONS
# ------------------------------------------------------------------

@mcp.resource("file://{path}")
def get_file_info(path: str) -> str:
    """Get information about a file or directory"""
    try:
        # 🔑 SECURE PATH CHECK
        file_path = resolve_and_check_path(path)
        
        if not file_path.exists():
            return f"Path does not exist: {path}"
        
        if file_path.is_dir():
            # Only list contents relative to the workspace, not the full path
            contents = "\n".join(f.name for f in file_path.iterdir())
            return f"Directory (Workspace Relative): {path}\nContents:\n{contents}"
        else:
            stats = file_path.stat()
            return (
                f"File (Workspace Relative): {path}\n"
                f"Size: {stats.st_size} bytes\n"
                f"Last modified: {datetime.fromtimestamp(stats.st_mtime)}\n"
                f"Created: {datetime.fromtimestamp(stats.st_ctime)}"
            )
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"An error occurred: {e}"

# Tool to create a new directory
@mcp.tool()
def create_directory(path: str, parents: bool = False) -> str:
    """Create a new directory at the specified path"""
    try:
        # 🔑 SECURE PATH CHECK - must not follow symlinks for creation
        dir_path = resolve_and_check_path(path, follow_symlinks=False)
        dir_path.mkdir(parents=parents, exist_ok=True)
        return f"Directory created at {path} (in workspace)"
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Creation failed: {e}"

# Tool to create a new file
@mcp.tool()
def create_file(path: str, content: Optional[str] = None) -> str:
    """Create a new file at the specified path with optional content"""
    try:
        # 🔑 SECURE PATH CHECK - must not follow symlinks for creation
        file_path = resolve_and_check_path(path, follow_symlinks=False)
        
        file_path.touch()
        
        if content is not None:
            file_path.write_text(content)
            return f"File created at {path} with {len(content)} bytes of content"
        return f"Empty file created at {path}"
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Creation failed: {e}"

# Tool to write to a file
@mcp.tool()
def write_file(path: str, content: str, append: bool = False) -> str:
    """Write content to a file"""
    try:
        # 🔑 SECURE PATH CHECK
        file_path = resolve_and_check_path(path)
        
        if not file_path.exists():
            return f"Error: File does not exist at {path}"
        
        mode = "a" if append else "w"
        # Using open() within a secure check is now safe
        with file_path.open(mode) as f:
            f.write(content)
        
        action = "appended to" if append else "written to"
        return f"Content {action} {path} ({len(content)} bytes)"
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Write failed: {e}"

# Tool to read a file
@mcp.tool()
def read_file(path: str) -> str:
    """Read the contents of a file"""
    try:
        # 🔑 SECURE PATH CHECK
        file_path = resolve_and_check_path(path)
        
        if not file_path.exists():
            return f"Error: File does not exist at {path}"
        
        if file_path.is_dir():
            return f"Error: {path} is a directory, not a file"
        
        return file_path.read_text()
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Read failed: {e}"

# Tool to list directory contents
@mcp.tool()
def list_directory(path: str = ".", detailed: bool = False) -> str:
    """List contents of a directory"""
    try:
        # 🔑 SECURE PATH CHECK
        dir_path = resolve_and_check_path(path)
        
        if not dir_path.exists():
            return f"Error: Directory does not exist at {path}"
        
        if not dir_path.is_dir():
            return f"Error: {path} is not a directory"
        
        items = []
        for item in dir_path.iterdir():
            item_relative_to_base = item.relative_to(BASE_DIR)
            
            if detailed:
                stats = item.stat()
                items.append(
                    f"{item_relative_to_base.name}\n"
                    f"  Type: {'Directory' if item.is_dir() else 'File'}\n"
                    f"  Size: {stats.st_size} bytes\n"
                    f"  Modified: {datetime.fromtimestamp(stats.st_mtime)}"
                )
            else:
                items.append(item_relative_to_base.name)
        
        return f"Contents of {path} (in workspace):\n" + "\n".join(items)
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Listing failed: {e}"

# Tool to delete a file or directory
@mcp.tool()
def delete_path(path: str, recursive: bool = False) -> str:
    """Delete a file or directory"""
    try:
        # 🔑 SECURE PATH CHECK
        target_path = resolve_and_check_path(path)
        
        if not target_path.exists():
            return f"Error: Path does not exist at {path}"
        
        if target_path.is_dir():
            if recursive:
                shutil.rmtree(target_path)
                return f"Directory {path} and all contents deleted (in workspace)"
            else:
                try:
                    target_path.rmdir()
                    return f"Directory {path} deleted (in workspace)"
                except OSError as e:
                    return f"Error: Directory not empty. Use recursive=True to delete. {str(e)}"
        else:
            target_path.unlink()
            return f"File {path} deleted (in workspace)"
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Deletion failed: {e}"

# Tool to move/rename a file or directory
@mcp.tool()
def move_path(source: str, destination: str) -> str:
    """Move or rename a file or directory"""
    try:
        # 🔑 SECURE PATH CHECK on both source and destination
        src_path = resolve_and_check_path(source)
        # Note: destination must also be checked as it could contain '..'
        dest_path = resolve_and_check_path(destination)
        
        if not src_path.exists():
            return f"Error: Source path does not exist at {source}"
        
        shutil.move(str(src_path), str(dest_path))
        return f"Moved {source} to {destination} (within workspace)"
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Move failed: {e}"

# Tool to copy a file or directory
@mcp.tool()
def copy_path(source: str, destination: str) -> str:
    """Copy a file or directory"""
    try:
        # 🔑 SECURE PATH CHECK on both source and destination
        src_path = resolve_and_check_path(source)
        dest_path = resolve_and_check_path(destination)
        
        if not src_path.exists():
            return f"Error: Source path does not exist at {source}"
        
        if src_path.is_dir():
            shutil.copytree(str(src_path), str(dest_path))
        else:
            shutil.copy2(str(src_path), str(dest_path))
        
        return f"Copied {source} to {destination} (within workspace)"
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Copy failed: {e}"

# Tool to get current working directory (Modified to reflect workspace root)
@mcp.tool()
def get_current_directory() -> str:
    """Get the base working directory (the secure workspace root)"""
    return str(BASE_DIR)

# Tool to change directory (Only changes relative to the script/BASE_DIR, not OS wide)
@mcp.tool()
def change_directory(path: str) -> str:
    """
    Change the current process working directory (WARNING: This should be avoided 
    in a true MCP server if other clients share the process). 
    
    Args:
        path: Path to change to
    """
    try:
        # 🔑 SECURE PATH CHECK
        new_path = resolve_and_check_path(path)
        
        if not new_path.exists():
            return f"Error: Path does not exist at {path}"
        
        if not new_path.is_dir():
            return f"Error: {path} is not a directory"
        
        # Only change the directory if strictly necessary, ideally server shouldn't change
        os.chdir(str(new_path))
        return f"Changed working directory to {new_path}"
    except PermissionError as e:
        return f"Access Denied Error: {e}"
    except Exception as e:
        return f"Change directory failed: {e}"

# Tool to get file metadata as an image (for previews)
@mcp.tool()
def get_file_preview(path: str) -> Optional[Image]:
    """Get a preview image of a file if possible"""
    try:
        import magic
        from PIL import Image as PILImage
        
        # 🔑 SECURE PATH CHECK
        file_path = resolve_and_check_path(path)
        
        if not file_path.exists() or file_path.is_dir():
            return None
            
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(str(file_path))
        
        if file_type.startswith('image/'):
            img = PILImage.open(str(file_path))
            img.thumbnail((300, 300))  # Create thumbnail
            # The return is now inside the secure check and using the safe path
            return Image(data=img.tobytes(), format=img.format.lower())
    except ImportError:
        # If magic or PIL is not installed
        return None
    except PermissionError:
        # Handle access denied gracefully by returning None for a preview
        return None
    except Exception:
        # Catch image processing errors
        return None
    
    return None

# Prompt for file operations
@mcp.prompt()
def file_operation_prompt(operation: str, target: str) -> list[base.Message]:
    """Prompt template for file operations"""
    return [
        base.UserMessage(f"I want to perform a file operation: {operation} on {target}"),
        base.AssistantMessage("I can help with that. What specific operation would you like to perform?"),
    ]

if __name__ == "__main__":
    mcp.run()
