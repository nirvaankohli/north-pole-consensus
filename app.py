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
import uuid
import csv
from collections import defaultdict
from movies.scrape import scraper

ENV_PATH = Path(__file__).parent / ".env"
JSON_ROOMS = Path(__file__).parent / "data" / "rooms.json"
MOVIES_CSV = Path(__file__).parent / "movies" / "results" / "movies.csv"
load_dotenv(ENV_PATH)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

movie_scraper = scraper(api_key="use_local")


def clear_rooms():

    with open(JSON_ROOMS, "w") as f:

        json.dump({}, f, indent=4)


def default_member_rooms(name, is_host=False):

    return {
        "name": name,
        "is_host": is_host,
        "survey": {"preferences": None, "min_rating": None},
        "movie_choices": {},  # {movie_id: "like" | "dislike"}
    }


def get_initial_random_feed(min_rating=None):

    rooms = load_rooms()
    total_members_in_room = len(rooms[session["room"]]["members"].keys())

    if min_rating:

        if min_rating < 0:

            min_rating = 0

        elif min_rating > 8:

            min_rating = 7

        movie_scraper.by_min_rating(min_rating)

    else:

        movie_scraper.selected_df = movie_scraper.get_all()

    max_suggestions = 0.7 * 10

    try:

        suggested_titles = rooms[session["room"]]["members"][session["member_id"]].get(
            "suggested_from_llm", []
        )

    except Exception as e:

        suggested_titles = []

    max_suggestions = 0.7 * total_members_in_room * 10

    if len(suggested_titles) > 0:

        if len(suggested_titles) > max_suggestions:

            suggested_titles = random.sample(suggested_titles, int(max_suggestions))

        _, suggested_titles = movie_scraper.exclude_list_of_titles(suggested_titles)

        suggested_titles = suggested_titles.to_dict(orient="records")

    else:

        suggested_titles = []

    random_movies = movie_scraper.get_random_movies(
        n=10 - len(suggested_titles),
        priority="Rating",
        pool=min(len(movie_scraper.selected_df) - 5, total_members_in_room * 19),
    )

    random_movies.extend(suggested_titles)
    print(random_movies, suggested_titles)

    movies = []

    for movie in random_movies:

        more_movie_info = movie_scraper.enrich_movie_details(
            movie["Title"], movie["Year"]
        )

        movies.append(
            {
                "id": movie["id"],
                "title": movie["Title"],
                "year": str(movie["Year"]),
                "poster": more_movie_info.get("poster", "N/A"),
                "plot": more_movie_info.get("plot", "No description available."),
                "genre": more_movie_info.get("genre", "N/A"),
                "director": more_movie_info.get("director", "N/A"),
                "actors": more_movie_info.get("actors", "N/A"),
                "rating": float(movie["Rating"]),
                "score": float(movie["Rating"]),
            }
        )

    return movies


def calculate_personalized_feed(room_data, member_id, min_rating=None):

    current_member = room_data["members"][member_id]
    current_choices = current_member["movie_choices"]

    if min_rating:
        filtered_df = movie_scraper.by_min_rating(min_rating)
    else:
        filtered_df = movie_scraper.get_all()

    all_movies = {}
    for idx, row in filtered_df.iterrows():
        all_movies[str(idx)] = {
            "id": str(idx),
            "title": row["Title"],
            "year": str(row["Year"]),
            "rating": float(row["Rating"]),
        }

    # Filter out already rated movies
    unrated_movies = {
        mid: m for mid, m in all_movies.items() if mid not in current_choices
    }

    total_choices = sum(
        len(member["movie_choices"]) for member in room_data["members"].values()
    )
    if total_choices == 0:
        return get_initial_random_feed(min_rating)

    mutual_likes = room_data.get("mutual_likes", {})

    movie_scores = defaultdict(lambda: {"score": 0, "voters": 0})

    for other_id, other_member in room_data["members"].items():

        if other_id == member_id:

            continue

        common_likes = set()
        common_dislikes = set()

        for mid, choice in current_choices.items():

            if mid in other_member["movie_choices"]:

                if choice == other_member["movie_choices"][mid]:

                    if choice == "like":

                        common_likes.add(mid)

                    else:

                        common_dislikes.add(mid)

        similarity = len(common_likes) + len(common_dislikes)

        for mid, choice in other_member["movie_choices"].items():

            if mid in unrated_movies:

                if choice == "like":

                    movie_scores[mid]["score"] += 1 + similarity * 0.5
                    movie_scores[mid]["voters"] += 1

                elif choice == "dislike":

                    movie_scores[mid]["score"] -= 0.5 + similarity * 0.3

    sorted_movies = []
    seen_titles = set()
    user_preferences = current_member.get("survey", {}).get("preferences", "").lower()

    for mid, movie in unrated_movies.items():

        if movie["title"] in seen_titles:
            continue
        seen_titles.add(movie["title"])

        collaborative_score = movie_scores[mid]["score"]
        base_score = movie["rating"] / 10.0

        mutual_likes_boost = 0

        if mid in mutual_likes:

            num_likes = len(mutual_likes[mid])

            mutual_likes_boost = num_likes * (2 + num_likes)

        preference_boost = 0
        if user_preferences:
            details = movie_scraper.enrich_movie_details(movie["title"], movie["year"])
            movie_text = (
                f"{details['genre']} {details['actors']} {details['director']}".lower()
            )
            if any(pref in movie_text for pref in user_preferences.split()):
                preference_boost = 2

            movie["poster"] = details["poster"]
            movie["plot"] = details["plot"]
            movie["genre"] = details["genre"]
            movie["director"] = details["director"]
            movie["actors"] = details["actors"]
        else:
            details = movie_scraper.enrich_movie_details(movie["title"], movie["year"])
            movie["poster"] = details["poster"]
            movie["plot"] = details["plot"]
            movie["genre"] = details["genre"]
            movie["director"] = details["director"]
            movie["actors"] = details["actors"]

        final_score = (
            collaborative_score * 2.5
            + base_score
            + mutual_likes_boost
            + preference_boost
        )
        sorted_movies.append({**movie, "score": final_score})

    sorted_movies.sort(key=lambda x: x["score"], reverse=True)

    return sorted_movies[:5]


clear_rooms()


def update_rooms(rooms_data):
    try:
        with open(JSON_ROOMS, "w") as f:
            json.dump(rooms_data, f, indent=4)
    except Exception as e:
        pass


def load_rooms():
    with open(JSON_ROOMS, "r") as f:
        return json.load(f)


def check_voting_complete(room_data):
    members = room_data["members"]
    mutual_likes = room_data.get("mutual_likes", {})

    if len(members) == 0:
        return False, []

    everyone_done_10 = all(
        len(member["movie_choices"]) >= 10 for member in members.values()
    )

    if everyone_done_10:
        top_movies = []
        for movie_id, likers in mutual_likes.items():
            top_movies.append(
                {"movie_id": movie_id, "likes": len(likers), "likers": likers}
            )

        if len(top_movies) == 0:
            for member in members.values():
                for movie_id, choice in member["movie_choices"].items():
                    if choice == "like":
                        if not any(m["movie_id"] == movie_id for m in top_movies):
                            top_movies.append(
                                {"movie_id": movie_id, "likes": 1, "likers": []}
                            )
                        break
                if len(top_movies) >= 3:
                    break

        top_movies.sort(key=lambda x: x["likes"], reverse=True)
        return True, top_movies[:3]

    return False, []


clear_rooms()


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

    error = request.args.get("error")
    code = request.args.get("code", "")
    name = request.args.get("name", "")

    if request.method == "POST":

        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join")
        create = request.form.get("create")

        if not name:
            return redirect(
                url_for("index", error="Please enter a name.", code=code, name=name)
            )

        if join is not None and not code:
            return redirect(
                url_for("index", error="Please enter a room code.", name=name)
            )

        room = code

        if "create" in request.form:

            room = generate_code(rooms)

            if "member_id" not in session:
                session["member_id"] = str(uuid.uuid4())

            member_id = session["member_id"]

            rooms[room] = {
                "members": {member_id: default_member_rooms(name, is_host=True)},
                "host": member_id,
                "chat_started": False,
                "data": [],
                "mutual_likes": {},  # {"movie_id": [member_ids who liked it]}
            }

            update_rooms(rooms)

        elif code not in rooms:
            return redirect(url_for("index", error="Room does not exist.", name=name))

        session["room"] = room
        session["name"] = name
        if "member_id" not in session:
            session["member_id"] = str(uuid.uuid4())

        if (
            "join" in request.form
            and code in rooms
            and session["member_id"] not in rooms[code]["members"]
        ):

            if rooms[code].get("chat_started", False):

                return redirect(
                    url_for(
                        "index",
                        error="This room has already started. You cannot join.",
                        name=name,
                    )
                )

            rooms[code]["members"][session["member_id"]] = default_member_rooms(
                session["name"]
            )

            update_rooms(rooms)

        return redirect(url_for("room", code=room))

    return render_template("index.html", error=error, code=code, name=name)


@app.route("/clear-sesh/<return_file>")
def clear_sesh(return_file="index"):

    session.clear()

    return redirect(url_for(return_file))


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

        session["name"] = name
        if "member_id" not in session:
            session["member_id"] = str(uuid.uuid4())

        if room in rooms:

            if rooms[room].get("chat_started", False):

                session.clear()

                return redirect(url_for("index"))

            rooms[room]["members"][session["member_id"]] = default_member_rooms(name)
            update_rooms(rooms)

        return redirect(url_for("room", code=room))

    return render_template("prompt_name.html")


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

        return redirect(url_for("index", error="Room does not exist."))
    member_id = session.get("member_id")

    if member_id not in rooms[code]["members"] and rooms[code].get(
        "chat_started", False
    ):
        return redirect(
            url_for("index", error="This room has already started. You cannot join.")
        )

    is_host = rooms[code]["host"] == member_id
    chat_started = rooms[code].get("chat_started", False)

    personalized_feed = []

    if chat_started:

        user_survey = rooms[code]["members"][member_id].get("survey", {})
        min_rating = None

        if isinstance(user_survey, dict):

            min_rating = user_survey.get("min_rating")

        personalized_feed = calculate_personalized_feed(
            rooms[code], member_id, min_rating=min_rating
        )

    return render_template(
        "room.html",
        code=code,
        messages=rooms[code]["data"],
        is_host=is_host,
        chat_started=chat_started,
        movies=personalized_feed,
    )


@socketio.on("movie_choice")
def movie_choice(data):
    rooms = load_rooms()
    room = session.get("room")
    member_id = session.get("member_id")

    if room not in rooms:
        return

    movie_id = data.get("movie_id")
    choice = data.get("choice")

    if movie_id and choice in ["like", "dislike"]:
        rooms[room]["members"][member_id]["movie_choices"][movie_id] = choice

        if "mutual_likes" not in rooms[room]:

            rooms[room]["mutual_likes"] = {}

        if choice == "like":

            if movie_id not in rooms[room]["mutual_likes"]:

                rooms[room]["mutual_likes"][movie_id] = []

            if member_id not in rooms[room]["mutual_likes"][movie_id]:

                rooms[room]["mutual_likes"][movie_id].append(member_id)

        elif choice == "dislike":

            if movie_id in rooms[room]["mutual_likes"]:

                if member_id in rooms[room]["mutual_likes"][movie_id]:

                    rooms[room]["mutual_likes"][movie_id].remove(member_id)

                if not rooms[room]["mutual_likes"][movie_id]:
                    del rooms[room]["mutual_likes"][movie_id]

        update_rooms(rooms)

        member_choices = len(rooms[room]["members"][member_id]["movie_choices"])
        print(f"Member {member_id} has made {member_choices} choices")

        is_complete, top_movies = check_voting_complete(rooms[room])

        if is_complete and not rooms[room].get("voting_complete", False):
            rooms[room]["voting_complete"] = True
            update_rooms(rooms)

            print(f"Voting complete! Top movies: {top_movies}")

            movie_details = []
            for movie_info in top_movies:
                movie_id = movie_info["movie_id"]
                found = False
                for idx, row in movie_scraper.df.iterrows():
                    if str(idx) == movie_id or str(row.get("id", "")) == str(movie_id):
                        movie_details.append(
                            {
                                "title": row["Title"],
                                "year": str(row["Year"]),
                                "rating": float(row["Rating"]),
                                "likes": movie_info["likes"],
                            }
                        )
                        found = True
                        break
                if not found:
                    print(f"Warning: Could not find movie with id {movie_id}")

            print(f"Emitting voting_complete with {len(movie_details)} movies")
            emit(
                "voting_complete",
                {"top_movies": movie_details},
                to=room,
                broadcast=True,
            )

        emit("feed_update", {"member_id": member_id}, to=room, include_self=False)


@socketio.on("get_updated_feed")
def get_updated_feed():

    rooms = load_rooms()
    room = session.get("room")
    member_id = session.get("member_id")

    if room not in rooms:
        return

    user_survey = rooms[room]["members"][member_id].get("survey", {})
    min_rating = None

    if isinstance(user_survey, dict):

        min_rating = user_survey.get("min_rating")

    personalized_feed = calculate_personalized_feed(
        rooms[room], member_id, min_rating=min_rating
    )

    emit("updated_feed", {"movies": personalized_feed})


@socketio.on("message")
def message(data):

    rooms = load_rooms()

    room = session.get("room")

    if data.get("data").startswith("survey"):
        return

    if room not in rooms:
        return

    if not rooms[room].get("chat_started", False):
        return

    content = {"name": session.get("name"), "message": data["data"]}
    send(content, to=room)
    rooms[room]["data"].append(content)
    update_rooms(rooms)


@socketio.on("survey")
def survey(data):

    import movies.ai as movies_ai

    llm_cli = movies_ai.llm()

    rooms = load_rooms()
    room = session.get("room")
    member_id = session.get("member_id")

    if room not in rooms:
        return

    rooms[room]["members"][member_id]["survey"] = data["data"]

    try:

        rooms[room]["members"][member_id]["suggested_from_llm"] = (
            llm_cli.suggest_titles_based_on_preferences(data["data"]["preferences"])
        )

    except Exception as e:

        rooms[room]["members"][member_id]["suggested_from_llm"] = []

    update_rooms(rooms)


@socketio.on("start_chat")
def start_chat():
    rooms = load_rooms()
    room = session.get("room")
    member_id = session.get("member_id")

    if room not in rooms:
        return

    for member in rooms[room]["members"]:

        survey = rooms[room]["members"][member]["survey"]
        if isinstance(survey, dict):
            if survey.get("preferences") is None or survey.get("min_rating") is None:
                return
        else:

            if None in survey:
                return

    if rooms[room]["host"] == member_id:
        rooms[room]["chat_started"] = True
        update_rooms(rooms)
        emit("chat_started", to=room)


@socketio.on("connect")
def connect(auth):

    rooms = load_rooms()

    room = session.get("room")
    name = session.get("name")

    if not room or not name:
        return

    try:

        if (
            len(rooms[room]["members"].keys()) == 1
            and session.get("member_id") in rooms[room]["members"].keys()
        ):

            # likely the host

            join_room(room)
            send({"name": name, "message": "has entered the room"}, to=room)

            return
        if room not in rooms:
            leave_room(room)
            return

    except Exception as e:

        pass

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)

    member_id = session.get("member_id")

    try:

        if member_id and member_id not in rooms[room]["members"]:
            if rooms[room].get("chat_started", False):
                return
            rooms[room]["members"][member_id] = default_member_rooms(name)

    except Exception as e:

        pass

    update_rooms(rooms)


@socketio.on("disconnect")
def disconnect():

    rooms = load_rooms()

    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:

        pass

    send({"name": name, "message": "has left the room"}, to=room)
    update_rooms(rooms)


if __name__ == "__main__":
    socketio.run(app, debug=True)
