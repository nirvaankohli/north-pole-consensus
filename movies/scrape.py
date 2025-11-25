import pandas as pd
from pathlib import Path

class scraper:

    def __init__(self, api_key="use_local"):

        self.movie_path = Path(__file__).parent / "results" / "movies.csv"        
        self.base_url = "http://www.omdbapi.com/"
        self.df = pd.read_csv(self.movie_path)

    def by_min_rating(self, min_rating):
        
        self.selected_df = self.df[self.df['Rating'] >= min_rating]

        return self.selected_df

    def by_min_year(self, min_year):
        
        self.selected_df = self.df[self.df['Year'] >= min_year]

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


if __name__ == "__main__":
    
    scraper = scraper()
    scraper.by_min_rating_and_year(5, 2000)
    print(scraper.get_random_movie("Rating", 1))