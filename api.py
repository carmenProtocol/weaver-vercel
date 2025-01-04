from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    allow_origins=["*"],  # В продакшене лучше указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            .system {
                color: #ffff00;
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
            const terminal = document.getElementById('terminal');

            function addMessage(message, type = 'normal') {
                const timestamp = new Date().toLocaleTimeString();
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${type}`;
                messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
                terminal.appendChild(messageDiv);
                terminal.scrollTop = terminal.scrollHeight;
            }

            function connect() {
                addMessage('Connecting to server...', 'system');
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                addMessage(`Attempting to connect to ${wsUrl}`, 'system');
                
                ws = new WebSocket(wsUrl);
                
                // Увеличиваем таймаут
                ws.timeout = 30000;
                
                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        addMessage(data.message, data.error ? 'error' : 'normal');
                    } catch (e) {
                        addMessage('Error parsing message: ' + e.message, 'error');
                    }
                };
                
                ws.onclose = function(event) {
                    const reason = event.reason || 'Unknown reason';
                    const code = event.code;
                    addMessage(`WebSocket connection closed. Code: ${code}, Reason: ${reason}`, 'error');
                    
                    if (reconnectAttempts < maxReconnectAttempts) {
                        reconnectAttempts++;
                        addMessage(`Reconnecting (attempt ${reconnectAttempts}/${maxReconnectAttempts})...`, 'system');
                        setTimeout(connect, reconnectDelay);
                    } else {
                        addMessage(`Failed to reconnect after ${maxReconnectAttempts} attempts. Please refresh the page.`, 'error');
                    }
                };

                ws.onerror = function(error) {
                    addMessage('WebSocket error: ' + (error.message || 'Unknown error'), 'error');
                    console.error('WebSocket error:', error);
                };

                ws.onopen = function() {
                    reconnectAttempts = 0;
                    addMessage('Connected to server', 'system');
                };
            }

            // Проверка состояния соединения каждые 30 секунд
            setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    try {
                        ws.send(JSON.stringify({ type: 'ping' }));
                    } catch (e) {
                        addMessage('Error sending ping: ' + e.message, 'error');
                    }
                }
            }, 30000);

            connect();

            // Обработка закрытия страницы
            window.onbeforeunload = function() {
                if (ws) {
                    ws.close();
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
        if text.strip():  # Игнорируем пустые строки
            self.queue.put({"message": text.strip(), "error": False})
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
        "connections": len(active_websockets),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        # Логируем заголовки запроса
        logger.info(f"WebSocket headers: {websocket.headers}")
        logger.info(f"Client connecting from: {websocket.client}")
        
        await websocket.accept()
        active_websockets.add(websocket)
        logger.info(f"New WebSocket connection. Active connections: {len(active_websockets)}")
        
        # Отправляем приветственное сообщение
        await websocket.send_json({"message": "Connected to Weaver Trading Bot", "error": False})
        
        while True:
            try:
                # Проверяем входящие сообщения (например, ping)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)  # Увеличили таймаут
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Проверяем, живо ли соединение
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    raise WebSocketDisconnect()
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                continue

            # Отправляем сообщения из очереди
            while not message_queue.empty():
                try:
                    message = message_queue.get_nowait()
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    message_queue.put(message)  # Возвращаем сообщение в очередь
                    break

            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")
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