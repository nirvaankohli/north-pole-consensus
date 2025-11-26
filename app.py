from flask import (
    Flask,
    render_template,
    session,
    request,
    redirect,
    url_for,
    jsonify,
    g,
)
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from dotenv import load_dotenv
from pathlib import Path
import random
from string import ascii_uppercase
import os
import json

ENV_PATH = Path(__file__).parent / ".env"
JSON_ROOMS = Path(__file__).parent / "data" / "rooms.json"
load_dotenv(ENV_PATH)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)


def update_rooms(rooms_data):
    print(f"Updating rooms.json with: {rooms_data}")
    try:
        with open(JSON_ROOMS, "w") as f:
            json.dump(rooms_data, f, indent=4)
        print("Successfully wrote to rooms.json")
    except Exception as e:
        print(f"Error writing to rooms.json: {e}")


def load_rooms():
    with open(JSON_ROOMS, "r") as f:
        return json.load(f)


def generate_code(rooms, length=6):

    while True:

        code = "".join(random.choices(ascii_uppercase, k=length))

        if code not in rooms:

            break

    return code


@app.route("/", methods=["GET", "POST"])
def index():

    rooms = load_rooms()

    session.clear()

    if request.method == "POST":
        print(f"Form data: {request.form}")

        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join")
        create = request.form.get("create")

        if not name:
            return render_template(
                "index.html", error="Please enter a name.", code=code, name=name
            )

        if join is not None and not code:
            return render_template(
                "index.html", error="Please enter a room code.", name=name
            )

        room = code

        if "create" in request.form:

            print("Creating new room...")

            room = generate_code(rooms)

            print(f"Generated code: {room}")

            rooms[room] = {"members": 0, "data": []}
            print(f"Rooms after addition: {rooms}")
            update_rooms(rooms)

        elif code not in rooms:
            print(f"Room {code} not found in {rooms}")
            return render_template(
                "index.html", error="Room does not exist.", name=name
            )

        session["room"] = room
        session["name"] = name

        return redirect(url_for("room", code=room))

    return render_template("index.html")


@app.route("/prompt_name", methods=["GET", "POST"])
def prompt_name():

    rooms = load_rooms()

    if "room" not in session:

        return redirect(url_for("index"))

    room = session["room"]
    session.clear()
    session["room"] = room

    if request.method == "POST":

        name = request.form.get("name")

        if not name:

            return render_template(
                "prompt_name.html", error="Please enter a name.", name=name
            )

    return_file = params.get("return_file") or "index"
    session.clear()

    return redirect(url_for(return_file))


@app.route("/room/<code>")
def room(code):

    rooms = load_rooms()

    try:

        current_room = session["room"]

    except:

        current_room = code
        session["room"] = code

    if current_room != code:

        return redirect(url_for("room", code=current_room))

    elif "name" not in session:

        return redirect(url_for("prompt_name"))

    if code not in rooms:
        return render_template("index.html", error="Room does not exist.")

    return render_template("room.html", code=code, messages=rooms[code]["data"])


@socketio.on("message")
def message(data):

    rooms = load_rooms()

    room = session.get("room")
    if room not in rooms:
        return

    content = {"name": session.get("name"), "message": data["data"]}
    send(content, to=room)
    rooms[room]["data"].append(content)
    update_rooms(rooms)


@socketio.on("connect")
def connect(auth):

    rooms = load_rooms()

    room = session.get("room")
    name = session.get("name")

    if not room or not name:
        return

    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")
    update_rooms(rooms)



@socketio.on("disconnect")
def disconnect():

    rooms = load_rooms()

    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        # if rooms[room]["members"] <= 0:
        #     del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} left room {room}")
    update_rooms(rooms)



if __name__ == "__main__":
    socketio.run(app, debug=True)
