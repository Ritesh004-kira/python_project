import json
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from backend.models.database import Movie, db, Review
from backend.services.recommendation import recommender

movies_bp = Blueprint('movies', __name__)

GENRE_LIST = [
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Documentary", "Drama", "Family", "Fantasy", "Horror",
    "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western",
]


@movies_bp.route('/movies')
def list_movies():
    genre_filter = request.args.get('genre', '')
    lang_filter  = request.args.get('lang', '')
    sort_by      = request.args.get('sort', 'popularity')   # popularity | imdb_rating | year
    page         = request.args.get('page', 1, type=int)
    per_page     = 40

    q = Movie.query
    if genre_filter:
        q = q.filter(Movie.genre.ilike(f"%{genre_filter}%"))
    if lang_filter == 'hi':
        q = q.filter(Movie.language == 'hi')
    elif lang_filter == 'en':
        q = q.filter(Movie.language == 'en')

    if sort_by == 'imdb_rating':
        q = q.order_by(Movie.imdb_rating.desc())
    elif sort_by == 'year':
        q = q.order_by(Movie.year.desc())
    else:
        q = q.order_by(Movie.popularity.desc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    movies     = pagination.items

    return render_template(
        'movies.html',
        movies=movies,
        genre_list=GENRE_LIST,
        genre_filter=genre_filter,
        lang_filter=lang_filter,
        sort_by=sort_by,
        pagination=pagination,
    )


@movies_bp.route('/movie/<int:movie_id>', methods=['GET', 'POST'])
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        rating = request.form.get('rating', type=float)
        text   = request.form.get('review', '').strip()
        if rating:
            # Check if user already reviewed this movie
            existing = Review.query.filter_by(
                user_id=session['user_id'], movie_id=movie.id
            ).first()
            if existing:
                existing.rating = rating
                existing.text   = text or existing.text
            else:
                new_review = Review(
                    rating=rating, text=text or "No comment.",
                    user_id=session['user_id'], movie_id=movie.id
                )
                db.session.add(new_review)

            # Recompute average user rating on this movie
            db.session.flush()
            all_reviews = Review.query.filter_by(movie_id=movie.id).all()
            movie.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1)

            db.session.commit()
            recommender.invalidate_user_cache(session['user_id'])
            recommender.refresh_content_index()
            return redirect(url_for('movies.movie_detail', movie_id=movie_id))
        else:
            flash("Please provide both a star rating and a review text.", "error")

    # Parse cast JSON
    cast_list = []
    if movie.cast:
        try:
            cast_list = json.loads(movie.cast)
        except Exception:
            pass

    # Similar + hybrid recs
    similar_movies = recommender.get_similar_movies(movie.title, top_n=12)

    hybrid_recs = []
    if 'user_id' in session:
        hybrid_recs = recommender.get_recommendations_for_user(
            user_id=session['user_id'],
            seed_movie_title=movie.title,
            top_n=12,
        )
    else:
        hybrid_recs = recommender.get_popular_movies(top_n=12)

    # User's existing review for this movie
    user_review = None
    if 'user_id' in session:
        user_review = Review.query.filter_by(
            user_id=session['user_id'], movie_id=movie.id
        ).first()

    return render_template(
        'movie_detail.html',
        movie=movie,
        cast_list=cast_list,
        similar_movies=similar_movies,
        hybrid_recs=hybrid_recs,
        user_review=user_review,
    )


@movies_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    genre = request.args.get('genre', '')
    lang  = request.args.get('lang', '')

    q = Movie.query
    if query:
        q = q.filter(
            Movie.title.ilike(f'%{query}%') |
            Movie.overview.ilike(f'%{query}%') |
            Movie.director.ilike(f'%{query}%')
        )
    if genre:
        q = q.filter(Movie.genre.ilike(f'%{genre}%'))
    if lang:
        q = q.filter(Movie.language == lang)

    results = q.order_by(Movie.popularity.desc()).limit(60).all()
    return render_template(
        'search.html',
        results=results,
        query=query,
        genre=genre,
        genre_list=GENRE_LIST,
    )


# ── JSON APIs ─────────────────────────────────────────────────────────

@movies_bp.route('/api/recommend', methods=['POST'])
def api_recommend():
    data        = request.json or {}
    movie_title = data.get('title', '')
    user_id     = session.get('user_id', 0)
    top_n       = data.get('top_n', 12)

    recs = recommender.get_recommendations_for_user(
        user_id=user_id, seed_movie_title=movie_title, top_n=top_n
    )
    return jsonify({'recommendations': [_movie_json(m) for m in recs]})


@movies_bp.route('/api/popular')
def api_popular():
    genre = request.args.get('genre')
    recs  = recommender.get_popular_movies(top_n=20, genre_filter=genre)
    return jsonify({'movies': [_movie_json(m) for m in recs]})


def _movie_json(m):
    return {
        'id': m.id, 'title': m.title, 'genre': m.genre,
        'year': m.year, 'image_url': m.image_url,
        'imdb_rating': m.imdb_rating, 'trailer_key': m.trailer_key,
    }
