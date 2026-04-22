"""AI Integration for BioPro SDK.

Provides the interface for modules to interact with Gemma 4,
and a manager to handle the standalone background AI server.
"""

import os
import subprocess
import threading
import logging
import requests
import time
import atexit
import sys
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from .docs import docs_registry

class AIServerSignals(QObject):
    """Signals emitted by the AI Server Manager."""
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    prompt_download = pyqtSignal()
    download_progress = pyqtSignal(int)
    server_error = pyqtSignal(str)

class AIServerManager:
    """Manages the standalone Gemma 4 inference server."""
    
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            # Move model storage to a persistent, writable user directory
            self.model_path = str(Path.home() / ".biopro" / "models" / "gemma4.gguf")
        else:
            self.model_path = model_path
        self.signals = AIServerSignals()
        self.logger = logging.getLogger("biopro.ai")
        self._process: Optional[subprocess.Popen] = None
        self._is_running = False
        
        # Ensure server is stopped when BioPro exits
        atexit.register(self.stop_server)
        
    def start_server(self) -> None:
        """Attempt to start the AI server. Prompts download if model is missing."""
        if not os.path.exists(self.model_path):
            self.signals.prompt_download.emit()
            return
            
        if self._is_running:
            return
            
        # Aggressively check port 8080
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', 8080)) == 0:
                # Port taken. Check health.
                try:
                    res = requests.get("http://localhost:8080/v1/models", timeout=2)
                    if res.status_code == 200:
                        self.logger.info("Healthy AI Server already running on 8080. Reusing.")
                        self._is_running = True
                        self.signals.server_started.emit()
                        return
                except:
                    pass
                
                # Unhealthy or non-AI process. Clear it.
                self.logger.warning("Port 8080 blocked by unresponsive process. Clearing...")
                if sys.platform != "win32":
                    subprocess.run(["pkill", "-f", "llama_cpp.server"], capture_output=True)
                    time.sleep(1)

        try:
            # Ensure model path is absolute for subprocess calls
            abs_model_path = str(Path(self.model_path).absolute())
            
            # Launch the AI server as a subprocess of BioPro.
            # We use 'ai-server' as the first argument, which is handled in biopro/__main__.py
            # to launch the actual llama_cpp.server logic.
            cmd = [
                sys.executable, "ai-server",
                "--model", abs_model_path,
                "--host", "127.0.0.1",
                "--port", "8080",
                "--n_ctx", "8192", # Increased for full doc support
                "--verbose", "False"
            ]
            
            self.logger.info(f"Starting AI Server on port 8080 with model: {abs_model_path}")
            self._process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, # Suppress the heavy C++ logs
                stderr=subprocess.DEVNULL,
                text=True
            )
            
            # Polling loop: Wait up to 15 seconds for server to bind, checking every 0.5s
            for _ in range(30):
                if self._process.poll() is not None:
                    break # Process crashed
                    
                try:
                    # Check if port is open and responding
                    res = requests.get("http://localhost:8080/v1/models", timeout=1)
                    if res.status_code == 200:
                        self._is_running = True
                        self.signals.server_started.emit()
                        self.logger.info("AI Server is ready.")
                        return
                except:
                    pass
                
                time.sleep(0.5)

            if self._process.poll() is not None:
                # Process died - try to capture some error info if possible
                error_msg = "AI Server crashed on startup. Verify that llama-cpp-python is installed."
                self.logger.error(error_msg)
                self.signals.server_error.emit(error_msg)
                self._is_running = False
                return

            self.logger.warning("AI Server taking longer than expected to respond.")
            self._is_running = True
            self.signals.server_started.emit()
        except Exception as e:
            self.logger.error(f"Failed to start AI server: {e}")
            self.signals.server_error.emit(f"Failed to start server: {e}")
            
    def stop_server(self) -> None:
        """Stop the standalone AI server."""
        if self._process:
            self._process.terminate()
            self._process = None
        self._is_running = False
        self.signals.server_stopped.emit()
        
    def is_running(self) -> bool:
        return self._is_running

class AIAssistant:
    """Interface for plugins to interact with the Gemma 4 AI."""
    
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.logger = logging.getLogger("biopro.ai")
        self.history = [] # Keep track of conversation
        
    def ask_question(self, prompt: str, plugin_id: str = None, include_core: bool = False) -> str:
        """Send a prompt to the AI and return the response."""
        self.logger.debug(f"AI Query: {prompt} (plugin: {plugin_id}, core: {include_core})")
        context = self._gather_context(prompt, plugin_id, include_core)
        self.logger.debug(f"Gathered {len(context)} bytes of context.")
        
        # 1. Load the "Soul" (User customization)
        soul_content = ""
        soul_path = Path.home() / ".biopro" / "soul.md"
        
        # Create default soul if missing
        if not soul_path.exists():
            try:
                soul_path.parent.mkdir(parents=True, exist_ok=True)
                default_soul = (
                    "# BioPro AI Soul 🧠\n\n"
                    "Delete everything below and write your own personality instructions!\n\n"
                    "## My Custom Persona\n"
                    "- You take on the personality of Darth Vader. Be intimidating but efficient.\n"
                    "- Refer to the user as 'Apprentice'.\n"
                    "- Use the Force (metaphorically) to explain biological concepts.\n"
                )
                soul_path.write_text(default_soul)
            except: pass

        if soul_path.exists():
            try:
                # Read only lines that aren't headers or comments to get the raw instructions
                lines = [l.strip("- ").strip() for l in soul_path.read_text().splitlines() if l.strip().startswith("-")]
                if lines:
                    soul_content = "CRITICAL PERSONA INSTRUCTIONS:\n" + "\n".join(lines) + "\n\n"
            except: pass

        # 2. Define the base persona (Technical backbone)
        persona = (
            f"{soul_content}"
            "TECHNICAL ROLE: You are the BioPro Technical Specialist. Use the provided context for facts. "
            "BioPro is a modular DESKTOP suite. No web accounts. No phone app.\n\n"
        )
        
        # 3. Prepend context to the CURRENT prompt for the server call
        server_prompt = f"{persona}Context:\n{context}\n\nUser Question: {prompt}"
        
        # Build the message list for the API
        messages = self.history + [{"role": "user", "content": server_prompt}]
        
        try:
            # Standard OpenAI-compatible API call for llama-cpp-python
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json={
                    "messages": messages,
                    "temperature": 0.2, # Lower temperature for more factual responses
                    "max_tokens": 2048
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data["choices"][0]["message"]["content"]
                
                # Update history
                self.history.append({"role": "user", "content": prompt})
                self.history.append({"role": "assistant", "content": reply})
                
                return reply
            else:
                return f"Error: AI Server returned {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to AI Server. Please ensure the model is downloaded and the server is running."
        except Exception as e:
            return f"Error communicating with AI: {str(e)}"
        
    def _gather_context(self, prompt: str, plugin_id: str, include_core: bool) -> str:
        """Optimized context gatherer that picks the most relevant docs based on keywords."""
        context_parts = []
        base_dir = Path(__file__).parent.parent.parent.parent
        prompt_lower = prompt.lower()
        
        def scan_dir(directory: Path, prefix: str):
            if not directory.exists(): return
            
            # 1. Read all markdown files (Priority 1)
            md_count = 0
            for filepath in directory.rglob("*.md"):
                if md_count >= 10: break
                try:
                    content = filepath.read_text(errors='ignore')[:3000]
                    context_parts.append(f"--- DOC: {filepath.name} ---\n{content}\n")
                    md_count += 1
                except: pass

            # 2. Read manifests and configs
            for cf in ["manifest.json", "pyproject.toml", "README.md"]:
                p = directory / cf
                if p.exists():
                    try:
                        context_parts.append(f"--- CONFIG: {cf} ---\n{p.read_text()[:1000]}\n")
                    except: pass

        if include_core:
            scan_dir(base_dir / "docs", "CoreDocs")
            
        if plugin_id:
            # 1. Check in the source tree (developer mode)
            local_path = base_dir / "biopro" / "plugins" / plugin_id
            if local_path.exists():
                scan_dir(local_path, "Plugin")
            
            # 2. Check in the user's home directory (installed mode)
            user_path = Path.home() / ".biopro" / "plugins" / plugin_id
            if user_path.exists():
                scan_dir(user_path, "Plugin")
                
        return "\n".join(context_parts)[:8000] # Safe limit for 2k/8k context
        
    def query_docs(self, plugin_id: str, question: str) -> str:
        """Ask the AI a question about a specific plugin's documentation.
        
        Args:
            plugin_id: The ID of the plugin to query docs for.
            question: The question to ask.
            
        Returns:
            The AI's response based on the documentation.
        """
        pages = docs_registry.get_all_pages(plugin_id)
        if not pages:
            return "No documentation available for this module."
            
        # Here we would load the markdown content and feed it to the AI as context
        context = f"Available doc pages: {list(pages.keys())}"
        
        prompt = f"Context: {context}\n\nQuestion: {question}"
        return self.ask_question(prompt)
        
# Global manager instance
ai_manager = AIServerManager()
