from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketState
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import Set
from datetime import datetime
import main as trading_bot
import threading
from queue import Queue
import logging
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_websockets: Set[WebSocket] = set()
message_queue = Queue()
bot_status = {"running": False, "error": None}

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
            .system {
                color: #ffff00;
            }
        </style>
    </head>
    <body>
        <div id="terminal"></div>
        <script>
            let ws = null;
            let reconnectAttempts = 0;
            const maxReconnectAttempts = 5;
            const reconnectDelay = 5000;
            const terminal = document.getElementById('terminal');
            let pingInterval = null;

            function addMessage(message, type = 'normal') {
                const timestamp = new Date().toLocaleTimeString();
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${type}`;
                messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
                terminal.appendChild(messageDiv);
                terminal.scrollTop = terminal.scrollHeight;
            }

            function setupPingInterval() {
                if (pingInterval) {
                    clearInterval(pingInterval);
                }
                pingInterval = setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        try {
                            ws.send(JSON.stringify({ type: 'ping' }));
                        } catch (e) {
                            addMessage('Error sending ping: ' + e.message, 'error');
                            ws.close();
                        }
                    }
                }, 15000);
            }

            function connect() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.close();
                }

                addMessage('Connecting to server...', 'system');
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                addMessage(`Attempting to connect to ${wsUrl}`, 'system');
                
                try {
                    ws = new WebSocket(wsUrl);
                    
                    ws.onmessage = function(event) {
                        try {
                            const data = JSON.parse(event.data);
                            if (data.type === 'pong') {
                                return; // Игнорируем pong сообщения в выводе
                            }
                            addMessage(data.message, data.error ? 'error' : 'normal');
                        } catch (e) {
                            addMessage('Error parsing message: ' + e.message, 'error');
                        }
                    };
                    
                    ws.onclose = function(event) {
                        if (pingInterval) {
                            clearInterval(pingInterval);
                            pingInterval = null;
                        }

                        const reason = event.reason || 'Unknown reason';
                        const code = event.code;
                        addMessage(`WebSocket connection closed. Code: ${code}, Reason: ${reason}`, 'error');
                        
                        if (reconnectAttempts < maxReconnectAttempts) {
                            reconnectAttempts++;
                            const delay = reconnectDelay * reconnectAttempts;
                            addMessage(`Reconnecting in ${delay/1000} seconds (attempt ${reconnectAttempts}/${maxReconnectAttempts})...`, 'system');
                            setTimeout(connect, delay);
                        } else {
                            addMessage(`Failed to reconnect after ${maxReconnectAttempts} attempts. Please refresh the page.`, 'error');
                        }
                    };

                    ws.onerror = function(error) {
                        addMessage('WebSocket error occurred', 'error');
                        console.error('WebSocket error:', error);
                    };

                    ws.onopen = function() {
                        reconnectAttempts = 0;
                        addMessage('Connected to server', 'system');
                        setupPingInterval();
                    };
                } catch (e) {
                    addMessage('Error creating WebSocket connection: ' + e.message, 'error');
                }
            }

            connect();

            window.onbeforeunload = function() {
                if (ws) {
                    ws.close();
                }
                if (pingInterval) {
                    clearInterval(pingInterval);
                }
            };
        </script>
    </body>
</html>
"""

class TerminalPrinter:
    def __init__(self, queue: Queue):
        self.queue = queue

    def write(self, text: str):
        if text.strip():
            self.queue.put({"message": text.strip(), "error": False})
            logger.info(text.strip())

    def flush(self):
        pass

async def broadcast_message(message: dict):
    disconnected = set()
    for websocket in active_websockets:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            disconnected.add(websocket)
    
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
        "connections": len(active_websockets),
        "timestamp": datetime.now().isoformat()
    }

async def keep_alive(websocket: WebSocket):
    try:
        while True:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({"type": "ping"})
            await asyncio.sleep(15)
    except Exception as e:
        logger.error(f"Keep-alive error: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        logger.info(f"WebSocket headers: {websocket.headers}")
        logger.info(f"Client connecting from: {websocket.client}")
        
        await websocket.accept()
        active_websockets.add(websocket)
        logger.info(f"New WebSocket connection. Active connections: {len(active_websockets)}")
        
        await websocket.send_json({"message": "Connected to Weaver Trading Bot", "error": False})
        
        # Запускаем keep-alive в отдельной задаче
        keep_alive_task = asyncio.create_task(keep_alive(websocket))
        
        try:
            while True:
                try:
                    data = await websocket.receive_json()
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        continue
                        
                    # Обработка других типов сообщений
                    logger.info(f"Received message: {data}")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    continue
                    
                # Отправляем сообщения из очереди
                while not message_queue.empty():
                    try:
                        message = message_queue.get_nowait()
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Error sending message: {e}")
                        message_queue.put(message)
                        break

                await asyncio.sleep(0.1)
                
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected normally")
        finally:
            keep_alive_task.cancel()
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}\n{traceback.format_exc()}")
    finally:
        active_websockets.remove(websocket)
        logger.info(f"WebSocket connection closed. Active connections: {len(active_websockets)}")

def run_trading_bot():
    try:
        bot_status["running"] = True
        bot_status["error"] = None
        import sys
        sys.stdout = TerminalPrinter(message_queue)
        sys.stderr = TerminalPrinter(message_queue)
        trading_bot.main()
    except Exception as e:
        error_msg = f"Trading bot error: {str(e)}\n{traceback.format_exc()}"
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