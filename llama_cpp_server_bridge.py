import http.server
import socketserver
import json
import requests
import os
import sys
import subprocess

LLAMA_CPP_API_URL = "http://localhost:8080/v1/chat/completions"
PORT = 8081

# Global reference to the server instance
server_instance = None

# Safe root directory for saving files
SAFE_SAVE_ROOT = os.path.abspath("./saved_files")

class DrafterBridgeServer(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Handle GET requests for model information"""
        if self.path == '/model_info':
            self._handle_model_info_request()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            # Check if this is a shutdown, save, or generation request
            if 'shutdown' in data:
                self._handle_shutdown_request()
            elif 'save_content' in data:
                self._handle_save_request(data)
            else:
                self._handle_generation_request(data)

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            self._send_error(f"Invalid JSON request: {e}", 400)
            return

    # Function to handle model info request
    def _handle_model_info_request(self):
        """Fetch and return model information from llama.cpp"""
        try:
            # Query the llama.cpp server for model info
            response = requests.get("http://localhost:8080/v1/models")
            response.raise_for_status()
            
            model_data = response.json()
            # Extract model name from the response
            model_name = "Unknown"
            if 'data' in model_data and len(model_data['data']) > 0:
                model_id = model_data['data'][0].get('id', 'Unknown')
                # Clean up the model name (remove path if present, works on both Windows and Unix)
                model_name = os.path.basename(model_id)
                # Remove .gguf extension if present
                if model_name.endswith('.gguf'):
                    model_name = model_name[:-5]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response_data = json.dumps({'model_name': model_name})
            self.wfile.write(response_data.encode('utf-8'))
            
        except requests.exceptions.RequestException as e:
            self._send_error(f"Could not fetch model info from llama.cpp: {e}", 503)
        except Exception as e:
            self._send_error(f"Error retrieving model info: {e}", 500)

    # Function to handle shutdown request
    def _handle_shutdown_request(self):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'message': 'Shutting down servers...'})
            self.wfile.write(response.encode('utf-8'))
            
            # Kill llama-server.exe
            try:
                subprocess.run(['taskkill', '/IM', 'llama-server.exe', '/F'], 
                             capture_output=True, check=False)
                print("Terminated llama-server.exe")
            except Exception as e:
                print(f"Error terminating llama-server: {e}")
            
            # Schedule this server to shut down
            import threading
            def shutdown_self():
                import time
                time.sleep(1)  # Give time for response to be sent
                print("Shutting down bridge server...")
                
                # Shutdown the HTTP server
                global server_instance
                if server_instance:
                    server_instance.shutdown()
                
                # Force exit the process
                os._exit(0)
            
            threading.Thread(target=shutdown_self, daemon=True).start()
            
        except Exception as e:
            self._send_error(f"Error during shutdown: {e}", 500)

    # NEW: Function to handle saving the file
    def _handle_save_request(self, data):
        content = data.get('save_content')
        output_path = data.get('output_path')

        if not content or not output_path:
            self._send_error("Missing 'save_content' or 'output_path' for save request.", 400)
            return
        
        try:
            # Construct full save path
            full_output_path = os.path.abspath(os.path.join(SAFE_SAVE_ROOT, output_path))
            # Ensure the resulting path is under SAFE_SAVE_ROOT
            if not full_output_path.startswith(SAFE_SAVE_ROOT + os.sep):
                self._send_error("Invalid path: writing outside of SAFE_SAVE_ROOT is not allowed.", 400)
                return

            output_dir = os.path.dirname(full_output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Write the final content to the file (safe path)
            with open(full_output_path, 'w', encoding='utf-8') as outfile:
                outfile.write(content)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'message': f'Successfully saved to {full_output_path}'})
            self.wfile.write(response.encode('utf-8'))

        except IOError as e:
            self._send_error(f"Could not write to file: {e}", 500)
        except Exception as e:
            self._send_error(f"An unexpected server error occurred: {e}", 500)

    # MODIFIED: This function now only handles generation and streaming
    def _handle_generation_request(self, data):
        conversation_history = data.get('conversation_history', [])
        if not conversation_history:
            self._send_error("Missing 'conversation_history' for generation request.", 400)
            return
        
        self._stream_to_llama_cpp(conversation_history)

    # MODIFIED: This function no longer writes to a file
    def _stream_to_llama_cpp(self, conversation_history):
        try:
            llama_cpp_payload = {
                "messages": conversation_history,
                "stream": True
            }

            response = requests.post(LLAMA_CPP_API_URL, json=llama_cpp_payload, stream=True)
            response.raise_for_status()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') 
            self.end_headers()

            for line in response.iter_lines():
                if line.startswith(b'data: '):
                    line = line[len(b'data: '):]
                    if line.strip() == b'[DONE]':
                        break
                    if line:
                        try:
                            chunk = json.loads(line)
                            content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content:
                                # REMOVED: outfile.write(content)
                                gui_response = json.dumps({"response": content})
                                self.wfile.write(gui_response.encode('utf-8') + b'\n')
                                self.wfile.flush()
                        except (json.JSONDecodeError, IndexError):
                            print(f"Warning: Could not decode JSON line: {line}")

        except requests.exceptions.RequestException as e:
            self._send_error(f"Could not connect to llama.cpp at {LLAMA_CPP_API_URL}: {e}", 503)

    def _send_error(self, message, code):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_response = json.dumps({'error': message})
        self.wfile.write(error_response.encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

if __name__ == "__main__":
    httpd = socketserver.TCPServer(("", PORT), DrafterBridgeServer)
    server_instance = httpd
    print(f"🚀 Astral Drafter BRIDGE server starting on http://localhost:{PORT}")
    print(f"Ready to forward requests to llama.cpp at {LLAMA_CPP_API_URL}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        httpd.server_close()
