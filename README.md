# 🚀 Astral-Drafter

<div align="center">

A lean, local-first drafting tool for creative writers, powered by a custom GUI and an Ollama-connected backend.

</div>

<div align="center">

</div>

<div align="center">
<img src="" alt="Astral-Drafter Interface" width="700">
<p><em>The Astral-Drafter user interface in action.</em></p>
</div>

## 📋 Overview
Astral-Drafter is a specialized tool for novel writers and other creative professionals who want to leverage local LLMs without the overhead of complex, generic interfaces. It provides a clean, distraction-free GUI for generating long-form prose, complete with essential features for managing a limited context window.

This project began as a fork of the powerful mcp-ollama_server and repurposes its robust back-end file handling to serve a single purpose: streamlining the creative drafting process.

- Unlike other UIs, Astral-Drafter is built on a LEAN philosophy:

- It's not a generic chatbot. It's a purpose-built drafting assistant.

- Your data stays local. All processing happens on your machine via Ollama.

- Maximum control, minimal bloat. No features you don't need for writing.
  

## ✨ Key Features
- **✍️ Focused Writing Interface**: A clean GUI designed for authors, not developers.

- **📊 Live Context Monitoring**: A real-time progress bar shows your estimated token usage to help you stay within your model's context window.

- **💾 Direct-to-File Saving**: Generated prose is automatically saved to a file you specify, creating a seamless workflow from prompt to draft.

- **🔒 Complete Data Privacy**: All models and data are processed locally via Ollama.

- **⚙️ Minimal Overhead**: A lightweight solution that respects your system's resources.

- **🤖 Model Agnostic**: Works with any of your custom Ollama models.


## 🚀 Quick Start
**Prerequisites**
- Python 3.8+ installed

- Ollama set up and running on your system

- Git for cloning the repository

# Installation & Setup

~~~
# 1. First install uv if you haven't already
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# 2. Clone your repository
#    Replace Wahzammo with your actual GitHub username
git clone [https://github.com/Wahzammo/Astral-Drafter.git](https://github.com/YOUR_GITHUB_USERNAME/Astral-Drafter.git)
cd Astral-Drafter

# 3. Verify an Ollama model is installed (e.g., your custom qwen3 model)
ollama pull qwen3-astral
~~~

## Running the Application
Astral-Drafter has two parts: the back-end server and the front-end GUI.

# Step 1: Start the Back-End Server

The server handles the connection to Ollama and saving files. You will need to modify the server code to handle the output_path functionality.

~~~
# Navigate to the file_system module and install its dependencies
cd file_system
uv sync

# Go back to the root and start the server
# (This command assumes you've modified the server to run stand-alone)
cd ..
uv run file_system/file_system.py 
~~~

# Step 2: Launch the Front-End GUI

The GUI is a single, self-contained HTML file.

Navigate to the gui folder (or wherever you've saved it).

Open the astral_nexus_drafter.html file in your web browser.

You can now paste your outlines and character sheets, specify an output file, and start generating prose.

## 🏗️ How It Works
The architecture is simple and efficient:

GUI (Browser): You input your text and output path into the astral_nexus_drafter.html interface. The live context monitor gives you instant feedback.

MCP Server (Python): The GUI sends the full prompt and output path to the local Python server.

Ollama: The server forwards the prompt to your selected Ollama model for generation.

File System & GUI: The server receives the generated prose, simultaneously saves it to your specified file and streams it back to the GUI for you to view in real-time.

## 🤝 Contributing
This is a personal tool, but ideas for improving the writer's workflow are always welcome.

Fork the Repository

Create a Feature Branch: git checkout -b feature/amazing-feature

Commit Your Changes: git commit -m 'Add some amazing feature'

Push to the Branch: git push origin feature/amazing-feature

Open a Pull Request

## ❓ FAQ
Q: Why not just use a generic tool like Open WebUI? A: Those tools are excellent but are general-purpose chatbots. Astral-Drafter is a specialized instrument with features tailored specifically for long-form creative writing, such as the context monitor and direct-to-file saving.

Q: How accurate is the context monitor? A: It's an estimation based on a common character-to-token ratio (~4 chars/token). It's designed to give you a good visual guide to avoid exceeding your context limit, not a precise count.

## 🙏 Acknowledgements
This project is a fork of and is deeply indebted to the fantastic work done on mcp-ollama_server. It provides the core back-end functionality that makes this tool possible.

Ollama for making local LLMs accessible to everyone.
