from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from backend.models.database import Movie
from backend.services.recommendation import recommender

movies_bp = Blueprint('movies', __name__)


@movies_bp.route('/movies')
def list_movies():
    genre_filter = request.args.get('genre', None)
    # Use popularity engine for the default browse page
    movies = recommender.get_popular_movies(top_n=50, genre_filter=genre_filter)
    return render_template('movie.html', movies=movies)


@movies_bp.route('/movie/<int:movie_id>', methods=['GET', 'POST'])
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST' and 'user_id' in session:
        rating = request.form.get('rating', type=float)
        text   = request.form.get('review')
        if rating and text:
            from backend.models.database import db, Review
            new_review = Review(rating=rating, text=text,
                                user_id=session['user_id'], movie_id=movie.id)
            db.session.add(new_review)
            db.session.commit()
            # Bust this user's cached recommendations so the next load is fresh
            recommender.invalidate_user_cache(session['user_id'])
            # Refresh TF-IDF index and content cache
            recommender.refresh_content_index()
            return redirect(url_for('movies.movie_detail', movie_id=movie_id))
        else:
            flash("Please provide both a star rating and a review text.", "error")

    # ── Content-Based: similar movies sidebar ──────────────────────
    similar_movies = recommender.get_similar_movies(movie.title, top_n=5)

    # ── Hybrid: personalised "You may also like" section ───────────
    hybrid_recs = []
    if 'user_id' in session:
        hybrid_recs = recommender.get_recommendations_for_user(
            user_id=session['user_id'],
            seed_movie_title=movie.title,
            top_n=6,
        )
    else:
        # For anonymous users fall back to popularity-based recommendations
        hybrid_recs = recommender.get_popular_movies(top_n=6)

    return render_template(
        'movie.html',
        movie=movie,
        similar_movies=similar_movies,
        hybrid_recs=hybrid_recs,
        single_view=True,
    )


@movies_bp.route('/search')
def search():
    query = request.args.get('q', '')
    genre = request.args.get('genre', '')
    year  = request.args.get('year', '')

    movies_query = Movie.query

    if query:
        movies_query = movies_query.filter(
            Movie.title.ilike(f'%{query}%') | Movie.description.ilike(f'%{query}%')
        )
    if genre:
        movies_query = movies_query.filter(Movie.genre.ilike(f'%{genre}%'))
    if year:
        if year.endswith('s'):
            decade = int(year[:4])
            movies_query = movies_query.filter(
                Movie.year >= str(decade), Movie.year < str(decade + 10)
            )
        else:
            movies_query = movies_query.filter(Movie.year == year)

    results = movies_query.all()
    return render_template('movie.html', movies=results, search_query=query)


@movies_bp.route('/api/recommend', methods=['POST'])
def api_recommend():
    """JSON API — returns hybrid recommendations for a given movie title and user."""
    data       = request.json or {}
    movie_title = data.get('title', '')
    user_id    = session.get('user_id', 0)
    top_n      = data.get('top_n', 6)

    recs = recommender.get_recommendations_for_user(
        user_id=user_id,
        seed_movie_title=movie_title,
        top_n=top_n,
    )

    return jsonify({
        'recommendations': [
            {'id': m.id, 'title': m.title, 'genre': m.genre,
             'year': m.year, 'image_url': m.image_url, 'rating': m.rating}
            for m in recs
        ]
    })


@movies_bp.route('/api/popular', methods=['GET'])
def api_popular():
    """JSON API — returns the top popular movies."""
    genre = request.args.get('genre', None)
    recs  = recommender.get_popular_movies(top_n=10, genre_filter=genre)
    return jsonify({
        'movies': [
            {'id': m.id, 'title': m.title, 'genre': m.genre,
             'year': m.year, 'image_url': m.image_url, 'rating': m.rating}
            for m in recs
        ]
    })
