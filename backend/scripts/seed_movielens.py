import os
import sys
import zipfile
import urllib.request
import pandas as pd
from datetime import datetime
import uuid

# Project root is two levels up from backend/scripts/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from backend.app import create_app

DATA_DIR    = os.path.join(PROJECT_ROOT, 'backend', 'data')
DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
ZIP_PATH    = os.path.join(DATA_DIR, 'ml-latest-small.zip')
EXTRACT_DIR = DATA_DIR
MOVIES_CSV  = os.path.join(DATA_DIR, "ml-latest-small", "movies.csv")
RATINGS_CSV = os.path.join(DATA_DIR, "ml-latest-small", "ratings.csv")

PLACEHOLDER_IMAGE = "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800"

def download_and_extract():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(MOVIES_CSV):
        print("Downloading MovieLens Small dataset...")
        urllib.request.urlretrieve(DATASET_URL, ZIP_PATH)
        print("Extracting...")
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
        print("Extraction complete.")

def seed_database():
    app = create_app()
    with app.app_context():
        # Import models HERE, inside the app context, so SQLAlchemy
        # can fully instrument (bind) the ORM classes before we use them.
        from backend.models.database import db, Movie, User, Review
        
        # Clear existing data to avoid duplicates
        print("Clearing existing database...")
        db.drop_all()
        db.create_all()

        print("Loading movies.csv...")
        # We will load the first 1000 movies to keep it lightweight for demo purposes
        movies_df = pd.read_csv(MOVIES_CSV).head(1000)
        
        movie_dict = {}
        for index, row in movies_df.iterrows():
            title_parts = row['title'].rsplit(' (', 1)
            clean_title = title_parts[0]
            year = title_parts[1].replace(')', '') if len(title_parts) > 1 and title_parts[1].replace(')', '').isdigit() else "Unknown"
            
            # Format genres for display and ML
            genre_str = row['genres'].replace('|', ', ') if row['genres'] != '(no genres listed)' else 'Unknown'
            
            movie = Movie(
                id=row['movieId'],
                title=clean_title,
                genre=genre_str,
                year=year,
                description=f"A cinematic experience in the {genre_str} genre.",
                image_url=PLACEHOLDER_IMAGE,
                rating=0.0
            )
            db.session.add(movie)
            movie_dict[row['movieId']] = movie

        print("Loading ratings.csv...")
        ratings_df = pd.read_csv(RATINGS_CSV)
        # Filter ratings to only include movies we just inserted
        ratings_df = ratings_df[ratings_df['movieId'].isin(movie_dict.keys())]
        
        # Create users based on ratings
        unique_users = ratings_df['userId'].unique()
        user_dict = {}
        print(f"Creating {len(unique_users)} users...")
        for uid in unique_users:
            # Ensure UID is a python int
            uid_int = int(uid)
            user = User(
                id=uid_int,
                name=f"MovieLens User {uid_int}",
                email=f"user{uid_int}_{uuid.uuid4().hex[:6]}@movielens.test",
                password="password123" # Insecure, but for mock purposes only
            )
            db.session.add(user)
            user_dict[uid_int] = user
            
        db.session.commit()
            
        print("Inserting reviews...")
        reviews_to_add = []
        for index, row in ratings_df.iterrows():
            review = Review(
                rating=float(row['rating']),
                text=f"Imported from MovieLens dataset.",
                user_id=int(row['userId']),
                movie_id=int(row['movieId'])
            )
            reviews_to_add.append(review)
            
            # Update movie average rating simple calculation
            movie_dict[row['movieId']].rating = round((movie_dict[row['movieId']].rating + row['rating']) / 2.0, 1)

        db.session.bulk_save_objects(reviews_to_add)
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    download_and_extract()
    seed_database()
