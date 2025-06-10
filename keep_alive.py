from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def ping():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    threading.Thread(target=run).start()
