import http.server
import socketserver
import json
import requests
import os

# --- Configuration ---
# This is the standard endpoint for a llama.cpp server running in OpenAI-compatible mode.
LLAMA_CPP_API_URL = "http://localhost:8080/v1/chat/completions"
PORT = 8081 # Using a different port (8081) so it doesn't clash with llama.cpp (8080)

class DrafterBridgeServer(http.server.BaseHTTPRequestHandler):
    
    def do_POST(self):
        """Handles POST requests and bridges them to the llama.cpp server."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            model = data.get('model') # We get this from the GUI, but llama.cpp already has a model loaded.
            prompt = data.get('prompt')
            output_path = data.get('output_path')
            
            if not all([prompt, output_path]):
                self._send_error("Missing 'prompt' or 'output_path' in request.", 400)
                return

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            self._send_error(f"Invalid JSON request: {e}", 400)
            return

        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as outfile:
                self._stream_to_llama_cpp(prompt, outfile)

        except IOError as e:
            self._send_error(f"Could not write to file: {e}", 500)
        except Exception as e:
            self._send_error(f"An unexpected server error occurred: {e}", 500)
    
    def _stream_to_llama_cpp(self, prompt, outfile):
        """Connects to llama.cpp, streams the response, and writes to client/file."""
        try:
            # The payload format is different here. It mimics OpenAI's API.
            llama_cpp_payload = {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
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
                            # The response structure is different from Ollama's.
                            content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content:
                                outfile.write(content)
                                # We need to wrap it in Ollama's format so the GUI can understand it.
                                gui_response = json.dumps({"response": content})
                                self.wfile.write(gui_response.encode('utf-8') + b'\n')
                                self.wfile.flush()
                        except (json.JSONDecodeError, IndexError):
                            print(f"Warning: Could not decode JSON line from llama.cpp: {line}")

        except requests.exceptions.RequestException as e:
            self._send_error(f"Could not connect to llama.cpp server at {LLAMA_CPP_API_URL}. Is it running?: {e}", 503)

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
    with socketserver.TCPServer(("", PORT), DrafterBridgeServer) as httpd:
        print(f"🚀 Astral Drafter BRIDGE server starting on http://localhost:{PORT}")
        print(f"Ready to forward requests to llama.cpp at {LLAMA_CPP_API_URL}")
        httpd.serve_forever()
