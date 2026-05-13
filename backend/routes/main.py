from flask import Blueprint, render_template, session
from backend.models.database import Movie
from backend.services.recommendation import recommender

main_bp = Blueprint('main', __name__)

GENRE_ROWS = [
    ("Trending Now",   None,      "popularity"),
    ("Action",         "Action",  "popularity"),
    ("Bollywood",      None,      "popularity"),   # language=hi handled separately
    ("Drama",          "Drama",   "imdb_rating"),
    ("Sci-Fi",         "Sci-Fi",  "imdb_rating"),
    ("Comedy",         "Comedy",  "popularity"),
    ("Thriller",       "Thriller","imdb_rating"),
    ("Romance",        "Romance", "imdb_rating"),
    ("Horror",         "Horror",  "popularity"),
]


def _genre_movies(genre, sort_by, lang=None, limit=18):
    """Return movies for a genre row, sorted by given field."""
    q = Movie.query
    if genre:
        q = q.filter(Movie.genre.ilike(f"%{genre}%"))
    if lang:
        q = q.filter(Movie.language == lang)
    if sort_by == "popularity":
        q = q.order_by(Movie.popularity.desc())
    else:
        q = q.order_by(Movie.imdb_rating.desc())
    return q.limit(limit).all()


@main_bp.route('/')
def index():
    # ── Hero: pick top-5 most popular movies with a backdrop ──────────
    hero_movies = (
        Movie.query
        .filter(Movie.backdrop_url != '', Movie.backdrop_url.isnot(None))
        .order_by(Movie.popularity.desc())
        .limit(5)
        .all()
    )

    # ── Genre rows ────────────────────────────────────────────────────
    rows = []
    for label, genre, sort_by in GENRE_ROWS:
        if label == "Bollywood":
            movies = _genre_movies(None, "popularity", lang="hi")
        elif label == "Trending Now":
            movies = _genre_movies(None, "popularity")
        else:
            movies = _genre_movies(genre, sort_by)
        if movies:
            rows.append({"label": label, "movies": movies})

    # ── Personalised section ──────────────────────────────────────────
    if session.get('user_id'):
        personal_recs = recommender.get_recommendations_for_user(
            user_id=session['user_id'], top_n=18
        )
        rec_label = f"Recommended for You"
        rec_engine = "AI · Hybrid Engine"
    else:
        personal_recs = []
        rec_label = ""
        rec_engine = ""

    return render_template(
        'index.html',
        hero_movies=hero_movies,
        rows=rows,
        personal_recs=personal_recs,
        rec_label=rec_label,
        rec_engine=rec_engine,
    )


@main_bp.route('/about')
def about():
    return render_template('about.html')
