from flask import Blueprint, render_template, session
from backend.services.recommendation import recommender

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    motd    = recommender.get_movie_of_the_day()
    popular = recommender.get_popular_movies(top_n=8)

    # Personalised section: hybrid engine for logged-in users,
    # popularity fallback for anonymous visitors.
    if session.get('user_id'):
        personal_recs = recommender.get_recommendations_for_user(
            user_id=session['user_id'],
            seed_movie_title=motd.title if motd else None,
            top_n=8,
        )
        rec_label = f"Recommended for You, {session['user_name'].split()[0]}"
        rec_engine_label = "Hybrid AI · Popularity + Content + Collaborative"
    else:
        personal_recs = popular
        rec_label = "Top Picks Right Now"
        rec_engine_label = "Popularity Engine"

    return render_template(
        'index.html',
        motd=motd,
        popular=popular,
        personal_recs=personal_recs,
        rec_label=rec_label,
        rec_engine_label=rec_engine_label,
    )

@main_bp.route('/about')
def about():
    return render_template('about.html')
