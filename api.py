from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio
import json
from typing import Set
from datetime import datetime
import main as trading_bot
import threading
from queue import Queue
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
active_websockets: Set[WebSocket] = set()
message_queue = Queue()

# HTML страница с терминальным интерфейсом
HTML = """
<!DOCTYPE html>
<html>
    <head>
        <title>Weaver Trading Bot</title>
        <style>
            body {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                margin: 0;
                padding: 20px;
            }
            #terminal {
                background-color: #000000;
                border: 1px solid #00ff00;
                padding: 20px;
                height: 80vh;
                overflow-y: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .timestamp {
                color: #888888;
            }
            .message {
                margin: 5px 0;
            }
        </style>
    </head>
    <body>
        <div id="terminal"></div>
        <script>
            const terminal = document.getElementById('terminal');
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const timestamp = new Date().toLocaleTimeString();
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${data.message}`;
                terminal.appendChild(messageDiv);
                terminal.scrollTop = terminal.scrollHeight;
            };
            
            ws.onclose = function(event) {
                const timestamp = new Date().toLocaleTimeString();
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                messageDiv.style.color = '#ff0000';
                messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> WebSocket connection closed. Reconnecting...`;
                terminal.appendChild(messageDiv);
                setTimeout(() => window.location.reload(), 5000);
            };
        </script>
    </body>
</html>
"""

class TerminalPrinter:
    def __init__(self, queue: Queue):
        self.queue = queue

    def write(self, text: str):
        if text.strip():  # Игнорируем пустые строки
            self.queue.put(text)
            logger.info(text.strip())  # Дублируем в логи

    def flush(self):
        pass

async def broadcast_message(message: str):
    disconnected = set()
    for websocket in active_websockets:
        try:
            await websocket.send_json({"message": message})
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            disconnected.add(websocket)
    
    # Удаляем отключенные сокеты
    active_websockets.difference_update(disconnected)

@app.get("/")
async def get():
    return HTMLResponse(HTML)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            if not message_queue.empty():
                message = message_queue.get()
                await websocket.send_json({"message": message})
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_websockets.remove(websocket)

def run_trading_bot():
    try:
        import sys
        sys.stdout = TerminalPrinter(message_queue)
        sys.stderr = TerminalPrinter(message_queue)
        trading_bot.main()
    except Exception as e:
        logger.error(f"Trading bot error: {e}")
        message_queue.put(f"Error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting trading bot...")
    thread = threading.Thread(target=run_trading_bot, daemon=True)
    thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 