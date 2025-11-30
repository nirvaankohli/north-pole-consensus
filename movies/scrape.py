import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os
import requests
import logging

logger = logging.getLogger(__name__)


class scraper:

    def __init__(self, api_key="use_local"):

        self.movie_path = Path(__file__).parent / "results" / "movies.csv"
        self.base_url = "http://www.omdbapi.com/"
        self.df = pd.read_csv(self.movie_path)
        self.df["id"] = self.df.index.astype(str)
        self.selected_df = self.df.copy()
        self.env_path = Path(__file__).parent.parent / ".env"
        if api_key == "use_local":
            load_dotenv(dotenv_path=self.env_path)
            self.api_key = os.getenv("OMDB_API_KEY")
            if not self.api_key:
                logger.error("OMDB_API_KEY not found in .env file!")
            else:
                logger.info(
                    f"OMDB API Key loaded: {self.api_key[:4]}...{self.api_key[-4:]}"
                )
        else:
            self.api_key = api_key
            logger.info("Using provided API key")

    def exclude_list_of_titles(self, exclude_titles):

        return_exclude = self.selected_df[
            self.selected_df["Title"].isin(exclude_titles)
        ]
        self.selected_df = self.selected_df[
            ~self.selected_df["Title"].isin(exclude_titles)
        ]

        return self.selected_df, return_exclude

    def by_min_rating(self, min_rating):

        self.selected_df = self.selected_df[self.selected_df["Rating"] >= min_rating]

        return self.selected_df

    def by_min_year(self, min_year):

        self.selected_df = self.selected_df[self.selected_df["Year"] >= min_year]

        return self.selected_df

    def by_max_rating(self, max_rating):

        self.selected_df = self.selected_df[self.selected_df["Rating"] <= max_rating]

        return self.selected_df

    def by_max_year(self, max_year):

        self.selected_df = self.selected_df[self.selected_df["Year"] <= max_year]

        return self.selected_df

    def by_specific_title(self, title):

        self.selected_df = self.selected_df[
            self.selected_df["Title"].str.contains(title, case=False, na=False)
        ]

        return self.selected_df

    def by_specific_year(self, year):

        self.selected_df = self.df[self.df["Year"] == year]

        return self.selected_df

    def by_specific_rating(self, rating):

        self.selected_df = self.df[self.df["Rating"] == rating]

        return self.selected_df

    def by_min_rating_and_year(self, min_rating, min_year):

        self.selected_df = self.df[
            (self.df["Rating"] >= min_rating) & (self.df["Year"] >= min_year)
        ]

        return self.selected_df

    def get_random_movie(self, priority="None", pool=15):

        if priority == "None":

            return self.selected_df.sample(n=1)

        elif priority == "Rating":

            return (
                self.selected_df.sort_values(by="Rating", ascending=False)
                .head(pool)
                .sample(n=1)
            )

        elif priority == "Year":

            return (
                self.selected_df.sort_values(by="Year", ascending=False)
                .head(pool)
                .head(pool)
                .sample(n=1)
            )

        else:

            return (
                self.selected_df[
                    self.selected_df["Title"].str.contains(
                        priority, case=False, na=False
                    )
                ]
                .head(pool)
                .sample(n=1)
            )

    def get_random_movies(self, n=10, priority="None", pool=15):

        if priority == "None":

            sample_size = min(n, len(self.selected_df))
            random_sample = self.selected_df.sample(n=sample_size)
            movies = []

            for idx, row in random_sample.iterrows():

                movie_dict = row.to_dict()
                movies.append(movie_dict)

            return movies

        else:

            movies = []

            for _ in range(n):

                movie = self.get_random_movie(priority=priority, pool=pool)
                movie_dict = movie.iloc[0].to_dict()
                movies.append(movie_dict)

            return movies

    def max_min_rating(self):

        max_rating = self.df["Rating"].max()
        min_rating = self.df["Rating"].min()

        return max_rating, min_rating

    def query(self, query):

        self.selected_df = self.df[
            self.df["Title"].str.contains(query, case=False, na=False)
        ]

        return self.selected_df

    def get_all(self):

        return self.df

    def load_movies(self, min_rating=None):
        df = self.df.copy()

        if min_rating is not None:
            df = df[df["Rating"] >= min_rating]

        movies = {}
        for idx, row in df.iterrows():
            movies[row["id"]] = {
                "id": row["id"],
                "title": row["Title"],
                "year": str(row["Year"]),
                "rating": float(row["Rating"]),
            }

        return movies

    def get_info_from_params(self, params):
        if not self.api_key:
            logger.error("Cannot make OMDB request - API key not set")
            return {"Response": "False", "Error": "API key not configured"}

        params["apikey"] = self.api_key

        try:
            logger.debug(f"OMDB Request: {self.base_url} with params: {params}")
            r = requests.get(f"{self.base_url}", params=params, timeout=5)
            data = r.json()
            logger.debug(f"OMDB Response: {data}")
            return data
        except requests.exceptions.Timeout:
            logger.error("OMDB API request timed out")
            return {"Response": "False", "Error": "Request timeout"}
        except Exception as e:
            logger.error(f"OMDB API request failed: {str(e)}")
            return {"Response": "False", "Error": str(e)}

    def get_info_from_title(self, title):

        params = {"t": title}

        return self.get_info_from_params(params)

    def enrich_movie_details(self, title, year=None):
        logger.info(f"Enriching movie: '{title}' ({year if year else 'no year'})")

        try:
            info = self.get_info_from_title(title)

            if not info:
                logger.warning(f"Movie '{title}' - No response from OMDB")
                return self._default_movie_details()

            if info.get("Response") == "True":
                poster = info.get("Poster", "N/A")
                plot = info.get("Plot", "No description available.")

                if poster and poster != "N/A":
                    logger.info(f"✓ Movie '{title}' - Poster found: {poster[:50]}...")
                else:
                    logger.warning(f"✗ Movie '{title}' - No poster available")

                if plot and plot != "No description available.":
                    logger.info(f"✓ Movie '{title}' - Plot found: {plot[:50]}...")
                else:
                    logger.warning(f"✗ Movie '{title}' - No plot available")

                return {
                    "poster": poster,
                    "plot": plot,
                    "genre": info.get("Genre", "N/A"),
                    "director": info.get("Director", "N/A"),
                    "actors": info.get("Actors", "N/A"),
                }
            else:
                error_msg = info.get("Error", "Unknown error")
                logger.warning(f"✗ Movie '{title}' - OMDB returned error: {error_msg}")
                return self._default_movie_details()

        except Exception as e:
            logger.error(f"✗ Movie '{title}' - Exception: {str(e)}", exc_info=True)
            return self._default_movie_details()

    def _default_movie_details(self):
        return {
            "poster": "N/A",
            "plot": "No description available.",
            "genre": "N/A",
            "director": "N/A",
            "actors": "N/A",
        }

    def get_info_from_id(self, id):

        params = {"i": id}

        return self.get_info_from_params(params)

    def get_info_from_search(self, search, y=None):

        params = {"s": search}

        if y:
            params["y"] = y

        return self.get_info_from_params(params)

    def get_info_from_list(self, l, year=None):

        params = {"s": l}

        if year:
            params["y"] = year

        return self.get_info_from_params(params)


if __name__ == "__main__":

    scraper = scraper()
    scraper.by_min_rating_and_year(5, 2000)
    print(scraper.get_info_from_list("Home Alone", 1990))
    print(scraper.max_min_rating())
