import requests
from bs4 import BeautifulSoup
import time
import pandas as pd

def scrape_list(list_id, num_pages):
    
    base_url = f"https://www.imdb.com/list/{list_id}/" 
    all_movies = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.5"
    }

    for i in range(1, num_pages + 1):

        url = f"{base_url}?page={i}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        
        movie_items = soup.select("li.ipc-metadata-list-summary-item")
        
        for movie_item in movie_items:

            title_tag = movie_item.select_one('h3.ipc-title__text')
            title = title_tag.get_text(strip=True).split('. ', 1)[-1] if title_tag else "N/A"
            
            metadata_items = movie_item.select('span.dli-title-metadata-item')
            year = metadata_items[0].get_text(strip=True) if metadata_items else "N/A"
            
            rating_tag = movie_item.select_one('span.ipc-rating-star--base')
            rating = rating_tag.get_text(strip=True).split('(')[0] if rating_tag else "N/A"
                    
            all_movies.append({
                'Title': title,
                'Year': year,
                'Rating': rating
            })

    return all_movies

def main():
    
    total = 1200
    per_page = 25
    num_pages = (total // per_page) - 1
    movies = scrape_list("ls040154031", num_pages)
    
    df = pd.DataFrame(movies)
    df.to_csv("movies.csv", index=False)

    print(df.head(5))
    print(df.shape)

if __name__ == "__main__":
    main()
