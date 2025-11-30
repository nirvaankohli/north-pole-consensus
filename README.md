# North Pole Consensus

North Pole Consensus helps families and friends stop arguing over what to watch. Join a room, swipe movie cards in a Tinder‑style interface, and let the app aggregate votes and AI suggestions to produce a shortlist or final pick everyone agrees on. 

*Based on a true struggle*

## What it does

The basic idea: everyone joins a room, swipes on movies they like or dislike, and the app figures out what you should watch together. It uses some AI to suggest movies based on what you say you like, and tracks which movies everyone agrees on.

Features:

- Create/join rooms with a shareable code(& Link)
- Swipe interface for voting on movies
- AI suggestions based on your preferences(Survey at the start)
- Real-time updates when people vote
- Tracks mutual likes across the group
- Personalized recommendations using collaborative filtering

## Setup

You need Python 3.11 & the requirements installed in `requirements.txt`

### Install

```
git clone https://github.com/nirvaankohli/north-pole-consensus.git
cd north-pole-consensus
pip install -r requirements.txt
```

Create a `.env` file:
```
SECRET_KEY=your_secret_key_here
OMDB_API_KEY=your_omdb_api_key
AI_API_KEY=your_ai_api_key
BASE_URL=http://127.0.0.1:5000/
```

Oh, and the API key should be from ai.hackclub.com

Run it:
```
python app.py
```

Go to `http://127.0.0.1:5000`

## How to use it

**Create a room:**
- Enter your name, hit "Create Room"
- Share the 6-letter code with your friends

**Join a room:**
- Enter your name and the room code someone gave you

**Vote on movies:**
1. Everyone fills out a quick survey about what they like (genres, actors, minimum rating, etc.)
2. The host starts the session
3. Swipe right if you like a movie, left if you don't
4. The app shows you movies based on what you said you like and what similar users voted for
5. Keep voting until everyone's done at least 10-20 movies
6. Check what movies everyone liked

## How it works

The recommendation system is pretty straightforward:
- Compares your votes with other people in the room to find similar tastes
- Shows you movies that people with similar preferences liked
- Weighs movies higher if multiple people already liked them
- Matches your survey responses (genres, actors) against movie metadata
- Combines all this with IMDB ratings to rank suggestions

Voting ends when either everyone's voted on 20 movies, or everyone's done at least 10 and there's at least one movie everyone likes.

## Tech stack

Backend: Flask + Flask-SocketIO for real-time stuff
Frontend: Vanilla JavaScript with Socket.IO
Data: Pandas for movie data manipulation
APIs: OMDB for movie metadata, Hack Club AI API (Gemini 2.5 flash - for fast responses) for recommendations

## Config

Environment variables you need:
- `SECRET_KEY` - Flask session secret
- `OMDB_API_KEY` - Get one from http://www.omdbapi.com/
- `AI_API_KEY` - For the AI recommendations
- `BASE_URL` - Where you're hosting this (default: http://127.0.0.1:5000/)

## API stuff

Main routes:
- `/` - Landing page
- `/room/<code>` - Room interface
- `/prompt-name/<code>` - Name entry for direct links - Happens when session is not registered

Socket events:
- `submit_survey` - User submits preferences
- `start_chat` - Host starts voting
- `vote` - Someone votes on a movie
- `request_more_movies` - Get more movies to vote on
- `check_mutual_likes` - See what everyone liked
- `message` - Chat messages

## License

MIT License - see LICENSE file
