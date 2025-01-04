from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import asyncio
import json
from datetime import datetime
import main as trading_bot
import logging
import traceback
from typing import Optional
import os
from dotenv import load_dotenv
from supabase import Client, create_client

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

# Инициализируем Supabase клиент без прокси
supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options={"headers": {"X-Client-Info": "supabase-py/1.0.3"}})

# HTML страница с интерфейсом
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
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    </head>
    <body>
        <div id="terminal"></div>
        <script>
            const terminal = document.getElementById('terminal');
            let lastTimestamp = null;

            function addMessage(message, type = 'normal') {
                const timestamp = new Date(message.created_at).toLocaleTimeString();
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${message.is_error ? 'error' : type}`;
                messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message.content}`;
                terminal.appendChild(messageDiv);
                terminal.scrollTop = terminal.scrollHeight;
            }

            async function fetchNewLogs() {
                try {
                    const query = lastTimestamp ? `?after_timestamp=${lastTimestamp}` : '';
                    const response = await axios.get(`/logs${query}`);
                    const logs = response.data;
                    
                    if (logs.length > 0) {
                        logs.forEach(log => {
                            addMessage(log);
                            lastTimestamp = log.created_at;
                        });
                    }
                } catch (error) {
                    console.error('Error fetching logs:', error);
                }
            }

            async function fetchStatus() {
                try {
                    const response = await axios.get('/status');
                    const status = response.data;
                    
                    if (status.error) {
                        addMessage({ 
                            content: `Bot Error: ${status.error}`,
                            created_at: new Date().toISOString(),
                            is_error: true 
                        }, 'error');
                    }
                } catch (error) {
                    console.error('Error fetching status:', error);
                }
            }

            // Получаем логи каждые 2 секунды
            setInterval(fetchNewLogs, 2000);
            
            // Проверяем статус каждые 5 секунд
            setInterval(fetchStatus, 5000);

            // Загружаем начальные логи
            fetchNewLogs();
            fetchStatus();
        </script>
    </body>
</html>
"""

class SupabaseLogger:
    def __init__(self, state=None):
        self.buffer = []
        self.last_flush = datetime.now()
        self.state = state

    async def write(self, text: str, log_type='info', action=None, is_error=False):
        if text.strip():
            log_entry = {
                "content": text.strip(),
                "is_error": is_error,
                "log_type": log_type,
                "action": action
            }
            
            # Добавляем состояние, если оно доступно
            if self.state:
                log_entry.update({
                    "price": self.state.current_price,
                    "eth_balance": self.state.current_eth,
                    "usdt_balance": self.state.current_usd,
                    "pnl_total": None,  # Будет обновлено при расчете PNL
                    "pnl_percentage": None  # Будет обновлено при расчете PNL
                })
            
            self.buffer.append(log_entry)
            logger.info(text.strip())
            
            if len(self.buffer) >= 100 or (datetime.now() - self.last_flush).seconds >= 1:
                await self.flush()

    async def update_state(self, state):
        self.state = state

    async def log_pnl(self, pnl):
        if self.buffer and self.buffer[-1]:
            self.buffer[-1]["pnl_total"] = pnl.get('total')
            self.buffer[-1]["pnl_percentage"] = pnl.get('percentage')

    async def log_hedges(self, hedges):
        try:
            # Сначала удаляем все существующие хеджи
            supabase.table('hedges').delete().neq('id', 0).execute()
            
            # Затем добавляем текущие хеджи
            if hedges:
                hedge_entries = [
                    {
                        "hedge_num": num,
                        "size": hedge['size'],
                        "price": hedge['price']
                    }
                    for num, hedge in hedges.items()
                ]
                supabase.table('hedges').insert(hedge_entries).execute()
        except Exception as e:
            logger.error(f"Error updating hedges: {e}")

    async def flush(self):
        if self.buffer:
            try:
                data = supabase.table('logs').insert(self.buffer).execute()
                self.buffer.clear()
                self.last_flush = datetime.now()
            except Exception as e:
                logger.error(f"Error writing to Supabase: {e}")

@app.get("/")
async def get():
    return HTMLResponse(HTML)

@app.get("/logs")
async def get_logs(after_timestamp: Optional[str] = None):
    try:
        query = supabase.table('logs').select('*').order('created_at', desc=False).limit(100)
        
        if after_timestamp:
            query = query.gt('created_at', after_timestamp)
            
        response = query.execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return []

@app.get("/status")
async def get_status():
    try:
        response = supabase.table('bot_status').select('*').single().execute()
        return response.data or {"running": False, "error": None}
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return {"running": False, "error": str(e)}

async def run_trading_bot():
    try:
        # Обновляем статус
        supabase.table('bot_status').upsert({
            "id": 1,
            "running": True,
            "error": None,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        # Создаем логгер
        supabase_logger = SupabaseLogger()
        
        # Запускаем бота
        import sys
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        class AsyncPrinter:
            async def write(self, text):
                await supabase_logger.write(text)
            
            def flush(self):
                pass

        sys.stdout = AsyncPrinter()
        sys.stderr = AsyncPrinter()
        
        try:
            # Запускаем бота напрямую в асинхронном режиме
            await trading_bot.main(logger=supabase_logger)
        except Exception as e:
            error_msg = f"Trading bot error: {str(e)}\n{traceback.format_exc()}"
            supabase.table('bot_status').upsert({
                "id": 1,
                "error": error_msg,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            logger.error(error_msg)
        finally:
            # Восстанавливаем оригинальные stdout и stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    except Exception as e:
        error_msg = f"Error starting bot: {str(e)}\n{traceback.format_exc()}"
        supabase.table('bot_status').upsert({
            "id": 1,
            "error": error_msg,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        logger.error(error_msg)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting trading bot...")
    await run_trading_bot()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 