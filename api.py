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
bot_status = {"running": False, "error": None}

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
            .error {
                color: #ff0000;
            }
        </style>
    </head>
    <body>
        <div id="terminal"></div>
        <script>
            let ws;
            let reconnectAttempts = 0;
            const maxReconnectAttempts = 5;
            const reconnectDelay = 5000;

            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    const timestamp = new Date().toLocaleTimeString();
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message';
                    if (data.error) {
                        messageDiv.className += ' error';
                    }
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
                    
                    if (reconnectAttempts < maxReconnectAttempts) {
                        reconnectAttempts++;
                        setTimeout(connect, reconnectDelay);
                    } else {
                        messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> Failed to reconnect after ${maxReconnectAttempts} attempts. Please refresh the page.`;
                    }
                };

                ws.onopen = function() {
                    reconnectAttempts = 0;
                    const timestamp = new Date().toLocaleTimeString();
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message';
                    messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> Connected to server`;
                    terminal.appendChild(messageDiv);
                };
            }

            connect();
        </script>
    </body>
</html>
"""

class TerminalPrinter:
    def __init__(self, queue: Queue):
        self.queue = queue

    def write(self, text: str):
        if text.strip():  # Игнорируем пустые строки
            self.queue.put({"message": text, "error": False})
            logger.info(text.strip())  # Дублируем в логи

    def flush(self):
        pass

async def broadcast_message(message: dict):
    disconnected = set()
    for websocket in active_websockets:
        try:
            await websocket.send_json(message)
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
    return {
        "status": "healthy" if bot_status["running"] and not bot_status["error"] else "unhealthy",
        "bot_running": bot_status["running"],
        "bot_error": bot_status["error"],
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            if not message_queue.empty():
                message = message_queue.get()
                await websocket.send_json(message)
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_websockets.remove(websocket)

def run_trading_bot():
    try:
        bot_status["running"] = True
        bot_status["error"] = None
        import sys
        sys.stdout = TerminalPrinter(message_queue)
        sys.stderr = TerminalPrinter(message_queue)
        trading_bot.main()
    except Exception as e:
        error_msg = f"Trading bot error: {str(e)}"
        logger.error(error_msg)
        bot_status["error"] = error_msg
        message_queue.put({"message": error_msg, "error": True})
    finally:
        bot_status["running"] = False

@app.on_event("startup")
async def startup_event():
    logger.info("Starting trading bot...")
    thread = threading.Thread(target=run_trading_bot, daemon=True)
    thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 