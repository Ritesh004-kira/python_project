from backend.app import create_app
from backend.models.database import Movie

app = create_app()
with app.app_context():
    total = Movie.query.count()
    with_trailer = Movie.query.filter(Movie.trailer_key != None, Movie.trailer_key != "").count()
    with_poster = Movie.query.filter(Movie.image_url != None, Movie.image_url != "").count()
    print(f"Total Movies: {total}")
    print(f"Movies with Trailer: {with_trailer}")
    print(f"Movies with Poster: {with_poster}")
