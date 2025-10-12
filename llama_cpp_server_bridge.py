import http.server
import socketserver
import json
import requests
import os

LLAMA_CPP_API_URL = "http://localhost:8080/v1/chat/completions"
PORT = 8081

class DrafterBridgeServer(http.server.BaseHTTPRequestHandler):
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            # NEW: Check if this is a save request or a generation request
            if 'save_content' in data:
                self._handle_save_request(data)
            else:
                self._handle_generation_request(data)

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            self._send_error(f"Invalid JSON request: {e}", 400)
            return

    # NEW: Function to handle saving the file
    def _handle_save_request(self, data):
        content = data.get('save_content')
        output_path = data.get('output_path')

        if not content or not output_path:
            self._send_error("Missing 'save_content' or 'output_path' for save request.", 400)
            return
        
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Write the final content to the file
            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write(content)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'message': f'Successfully saved to {output_path}'})
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
    with socketserver.TCPServer(("", PORT), DrafterBridgeServer) as httpd:
        print(f"🚀 Astral Drafter BRIDGE server starting on http://localhost:{PORT}")
        print(f"Ready to forward requests to llama.cpp at {LLAMA_CPP_API_URL}")
        httpd.serve_forever()