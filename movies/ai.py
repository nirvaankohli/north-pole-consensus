import requests
from pathlib import Path
from dotenv import load_dotenv
import os
import pandas as pd

class llm:

    def __init__(self, api_key="use_local"):

        self.base_url = "https://ai.hackclub.com/proxy/v1/chat/completions"

        self.env_path = Path(__file__).parent.parent / ".env"
        
        if api_key == "use_local":
        
            load_dotenv(dotenv_path=self.env_path)
            self.api_key = os.getenv("AI_API_KEY")
        
        else:
        
            self.api_key = api_key

    def make_request(self, user_prompt, system_prompt=None, model="google/gemini-2.5-flash",max_tokens=8000):

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        body = {

            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt} if system_prompt else {},
                {"role": "user", "content": user_prompt},
            ],

            "max_tokens": max_tokens,
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }

        response = requests.post(self.base_url, headers=headers, json=body)
        
        return response.json()

    def suggest_titles_based_on_preferences(self, preferences):

        self.movie_path = Path(__file__).parent / "results" / "movies.csv"

        self.df = pd.read_csv(self.movie_path)

        SYSTEM_PROMPT = """You are a helpful movie recommendation engine. Based on user preferences, suggest a list of movie titles that align with their interests. Provide only the titles in a comma-separated format without any additional text or explanations. Like This: ["Movie 1(Title)", "Movie 2(Title)", "Movie 3(Title)"] The brackets are important. The Titles need to be accurate and real movie titles."""

        USER_PROMPT = f"""Based on the following user preferences, suggest a list of movie titles that align with their interests: {preferences} Here is the list of movies to choose from: {self.df['Title'].tolist()}"""


        response = self.make_request(
            user_prompt=USER_PROMPT,
            system_prompt=SYSTEM_PROMPT,
        )

        import json

        print(f"LLM Response: {(response['choices'][0]['message']['content'])}")

        print(f"LLM Response(JSON): {json.loads(response['choices'][0]['message']['content'])}")

        return json.loads(response['choices'][0]['message']['content'])

