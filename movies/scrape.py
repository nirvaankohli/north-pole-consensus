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
        if api_key == "use_local":
            load_dotenv()
            self.api_key = os.getenv("OMDB_API_KEY")
        else:
            self.api_key = api_key

    def by_min_rating(self, min_rating):
        
        self.selected_df = self.df[self.df['Rating'] >= min_rating]

        return self.selected_df

    def by_min_year(self, min_year):
        
        self.selected_df = self.df[self.df['Year'] >= min_year]

        return self.selected_df

    def by_max_rating(self, max_rating):
        
        self.selected_df = self.df[self.df['Rating'] <= max_rating]

        return self.selected_df

    def by_max_year(self, max_year):
        
        self.selected_df = self.df[self.df['Year'] <= max_year]

        return self.selected_df

    def by_specific_title(self, title):
        
        self.selected_df = self.df[self.df['Title'].str.contains(title, case=False, na=False)]

        return self.selected_df
    
    def by_specific_year(self, year):
        
        self.selected_df = self.df[self.df['Year'] == year]

        return self.selected_df

    def by_specific_rating(self, rating):
        
        self.selected_df = self.df[self.df['Rating'] == rating]

        return self.selected_df

    def by_min_rating_and_year(self, min_rating, min_year):
        
        self.selected_df = self.df[(self.df['Rating'] >= min_rating) & (self.df['Year'] >= min_year)]

        return self.selected_df

    def get_random_movie(self, priority="None", pool=15):
        
        if priority == "None":
        
            return self.selected_df.sample(n=1)

        elif priority == "Rating":
        
            return self.selected_df.sort_values(by='Rating', ascending=False).head(pool).sample(n=1)
        
        elif priority == "Year":
        
            return self.selected_df.sort_values(by='Year', ascending=False).head(pool).head(pool).sample(n=1)
        
        else:   

            return self.selected_df[self.selected_df['Title'].str.contains(priority, case=False, na=False)].head(pool).sample(n=1)
    def max_min_rating(self):
        
        max_rating = self.df['Rating'].max()
        min_rating = self.df['Rating'].min()
        
        return max_rating, min_rating

    def query(self, query):

        self.selected_df = self.df[self.df['Title'].str.contains(query, case=False, na=False)]

        return self.selected_df

    def get_all(self):

        return self.df
    
    def get_info_from_params(self, params):

        params["apikey"] = self.api_key

        r = requests.get(f"{self.base_url}", params=params)
        data = r.json()

        return data

    def get_info_from_title(self, title):

        params = {"t": title}

        return self.get_info_from_params(params)

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