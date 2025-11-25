from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
from pathlib import Path
import os

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")
