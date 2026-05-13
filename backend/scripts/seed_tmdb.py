"""
backend/scripts/seed_tmdb.py

Seeds the database with real movie data from TMDB API.
Fetches Hollywood (popular + top_rated + now_playing) and Bollywood movies.
For each movie, fetches trailer (YouTube key) + cast + director.

Usage (from project root):
    python backend/scripts/seed_tmdb.py
"""

import os
import sys
import time
import json
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"
TMDB_BASE    = "https://api.themoviedb.org/3"
IMG_BASE     = "https://image.tmdb.org/t/p"

GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}


def tmdb_get(path, params=None, retries=3):
    p = {"api_key": TMDB_API_KEY, **(params or {})}
    for attempt in range(retries):
        try:
            r = requests.get(f"{TMDB_BASE}{path}", params=p, timeout=15)
            if r.status_code == 429:
                print("  Rate-limited — sleeping 12s")
                time.sleep(12)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  Error {e} (attempt {attempt+1})")
            time.sleep(3)
    return None


def poster(path, size="w500"):
    return f"{IMG_BASE}/{size}{path}" if path else "https://via.placeholder.com/500x750?text=No+Poster"


def backdrop(path, size="w1280"):
    return f"{IMG_BASE}/{size}{path}" if path else ""


def get_movie_detail(tmdb_id):
    """Fetch trailer, cast, director for a movie."""
    data = tmdb_get(f"/movie/{tmdb_id}", {"append_to_response": "videos,credits"})
    if not data:
        return None, None, None, None

    # Trailer
    trailer_key = None
    for v in (data.get("videos") or {}).get("results", []):
        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
            trailer_key = v["key"]
            break

    # Cast (top 5)
    credits = data.get("credits") or {}
    cast_list = [c["name"] for c in (credits.get("cast") or [])[:5]]

    # Director
    director = None
    for crew in (credits.get("crew") or []):
        if crew.get("job") == "Director":
            director = crew["name"]
            break

    runtime = data.get("runtime") or None
    return trailer_key, json.dumps(cast_list), director, runtime


def fetch_pages(endpoint, pages=25, extra_params=None):
    """Fetch multiple pages of movie results from a list endpoint."""
    movies = []
    for page in range(1, pages + 1):
        params = {"page": page, **(extra_params or {})}
        data = tmdb_get(endpoint, params)
        if not data:
            continue
        movies.extend(data.get("results", []))
        if page % 5 == 0:
            print(f"    Fetched page {page}/{pages} — total so far: {len(movies)}")
    return movies


def seed():
    from backend.app import create_app
    from backend.models.database import db, Movie, User, Review, RecommendationCache

    app = create_app()
    with app.app_context():
        print("=== Dropping existing tables ===")
        db.drop_all()
        db.create_all()

        seen_ids = set()
        to_insert = []

        # ── Collect movies from multiple sources ──────────────────────
        sources = [
            ("/movie/popular",            3, {}),
            ("/movie/top_rated",          3, {}),
            ("/movie/now_playing",        2, {}),
            ("/movie/upcoming",           2, {}),
            ("/discover/movie",           3, {"with_original_language": "hi", "sort_by": "popularity.desc"}),  # Bollywood
            ("/discover/movie",           2, {"with_original_language": "hi", "sort_by": "vote_average.desc", "vote_count.gte": 50}),
            ("/discover/movie",           2, {"with_genres": "28", "sort_by": "popularity.desc"}),   # Action
            ("/discover/movie",           2, {"with_genres": "878", "sort_by": "popularity.desc"}),  # Sci-Fi
            ("/discover/movie",           2, {"with_genres": "27",  "sort_by": "popularity.desc"}),  # Horror
            ("/discover/movie",           2, {"with_genres": "35",  "sort_by": "popularity.desc"}),  # Comedy
            ("/discover/movie",           2, {"with_genres": "10749","sort_by": "popularity.desc"}), # Romance
            ("/discover/movie",           2, {"with_genres": "53",  "sort_by": "popularity.desc"}),  # Thriller
        ]

        for endpoint, pages, extra in sources:
            label = extra.get("with_original_language", extra.get("with_genres", endpoint))
            print(f"\n-> Fetching {endpoint}  [{label}]  ({pages} pages)")
            raw = fetch_pages(endpoint, pages=pages, extra_params=extra)
            for m in raw:
                mid = m.get("id")
                if not mid or mid in seen_ids:
                    continue
                seen_ids.add(mid)
                to_insert.append(m)

        print(f"\n=== Collected {len(to_insert)} unique movies ===")
        print("=== Fetching detail (trailer + cast) for each — this takes a few minutes ===\n")

        inserted = 0
        for i, m in enumerate(to_insert, 1):
            mid = m["id"]
            title = m.get("title") or m.get("name", "Unknown")
            year_raw = (m.get("release_date") or "")[:4]
            year = year_raw if year_raw.isdigit() else "N/A"
            lang = m.get("original_language", "en")

            genre_ids = m.get("genre_ids", [])
            genre_str = ", ".join(GENRE_MAP.get(gid, "") for gid in genre_ids if gid in GENRE_MAP) or "General"

            overview = m.get("overview") or ""
            tagline  = (overview[:120] + "…") if len(overview) > 120 else overview
            imdb_rating = round(float(m.get("vote_average") or 0.0), 1)
            imdb_votes  = int(m.get("vote_count") or 0)
            popularity  = float(m.get("popularity") or 0.0)

            poster_url   = poster(m.get("poster_path"))
            backdrop_url_val = backdrop(m.get("backdrop_path"))

            # Fetch detail (trailer + cast)
            trailer_key, cast_json, director, runtime = get_movie_detail(mid)

            movie = Movie(
                id           = mid,
                tmdb_id      = mid,
                title        = title,
                genre        = genre_str,
                year         = year,
                description  = tagline,
                overview     = overview,
                image_url    = poster_url,
                backdrop_url = backdrop_url_val,
                trailer_key  = trailer_key,
                imdb_rating  = imdb_rating,
                imdb_votes   = imdb_votes,
                rating       = imdb_rating,   # seed user rating = imdb for now
                cast         = cast_json,
                director     = director,
                runtime      = runtime,
                language     = lang,
                popularity   = popularity,
            )
            db.session.add(movie)
            inserted += 1

            if inserted % 50 == 0:
                db.session.commit()
                print(f"  Committed {inserted}/{len(to_insert)}: {title}")

            # Be polite to TMDB API
            time.sleep(0.25)

        db.session.commit()
        print(f"\n=== {inserted} movies inserted ===")

        # ── Demo user accounts ────────────────────────────────────────
        print("Creating demo users...")
        from werkzeug.security import generate_password_hash
        demo_users = [
            ("Alice",  "alice@example.com",  "alice123"),
            ("Bob",    "bob@example.com",    "bob123"),
            ("Priya",  "priya@example.com",  "priya123"),
            ("Rahul",  "rahul@example.com",  "rahul123"),
            ("Sarah",  "sarah@example.com",  "sarah123"),
        ]
        for name, email, pwd in demo_users:
            u = User(name=name, email=email, password=generate_password_hash(pwd))
            db.session.add(u)
        db.session.commit()
        print("Demo users created (passwords hashed).")
        print("\nSeeding complete! Run `python run.py` to start the server.")


if __name__ == "__main__":
    seed()
