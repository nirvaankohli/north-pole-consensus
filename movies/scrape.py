import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os
import requests


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
        else:
            self.api_key = api_key

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

        params["apikey"] = self.api_key

        r = requests.get(f"{self.base_url}", params=params)
        data = r.json()

        return data

    def get_info_from_title(self, title):

        params = {"t": title}

        return self.get_info_from_params(params)

    def enrich_movie_details(self, title, year=None):
        try:
            info = self.get_info_from_title(title)
            if info and info.get("Response") == "True":
                return {
                    "poster": info.get("Poster", "N/A"),
                    "plot": info.get("Plot", "No description available."),
                    "genre": info.get("Genre", "N/A"),
                    "director": info.get("Director", "N/A"),
                    "actors": info.get("Actors", "N/A"),
                }
        except:
            pass
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
