# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time
import random

app = Flask(__name__)
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")


def background_thread():
    """后台线程定时推送数据"""
    while True:
        data = {"value": random.randint(1, 100)}  # 这里换成你的实时数据
        socketio.emit("update", data)
        print(data)
        time.sleep(2)


if __name__ == "__main__":
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    socketio.run(app, debug=True)
