import os
from flask import Flask, render_template_string
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_KEY", "")
)

# Simple HTML template
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot</title>
</head>
<body>
    <h1>Trading Bot Status</h1>
    <p>Bot is running. Check logs in Supabase.</p>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/health')
def health():
    return {"status": "ok"}

if __name__ == '__main__':
    app.run() 