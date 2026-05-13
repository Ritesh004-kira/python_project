from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews = db.relationship('Review', backref='user', lazy=True)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)        # TMDB movie ID used directly
    tmdb_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    title = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(255), nullable=False)
    year = db.Column(db.String(4), nullable=False)
    description = db.Column(db.Text, nullable=False)    # short tagline
    overview = db.Column(db.Text, nullable=True)        # full TMDB overview
    image_url = db.Column(db.String(500), nullable=True)    # poster (w500)
    backdrop_url = db.Column(db.String(500), nullable=True) # wide banner (w1280)
    trailer_key = db.Column(db.String(100), nullable=True)  # YouTube video key
    imdb_rating = db.Column(db.Float, default=0.0)         # TMDB vote_average
    imdb_votes = db.Column(db.Integer, default=0)          # TMDB vote_count
    rating = db.Column(db.Float, default=0.0)              # user-computed avg
    cast = db.Column(db.Text, nullable=True)               # JSON: top 5 actors
    director = db.Column(db.String(200), nullable=True)
    runtime = db.Column(db.Integer, nullable=True)         # minutes
    language = db.Column(db.String(10), nullable=True)     # 'en', 'hi', etc.
    popularity = db.Column(db.Float, default=0.0)          # TMDB popularity score

    reviews = db.relationship('Review', backref='movie', lazy=True, order_by="Review.created_at.desc()")

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Float, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)

class RecommendationCache(db.Model):
    __tablename__ = 'recommendation_cache'

    id         = db.Column(db.Integer, primary_key=True)
    cache_key  = db.Column(db.String(255), unique=True, nullable=False, index=True)
    movie_ids  = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_valid(self):
        return datetime.utcnow() < self.expires_at

    def get_ids(self):
        return [int(x) for x in self.movie_ids.split(',') if x.strip()]

    @staticmethod
    def set(cache_key, movie_list, ttl_seconds=3600):
        from datetime import timedelta
        ids_str = ','.join(str(m.id) for m in movie_list)
        expires = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        entry = RecommendationCache.query.filter_by(cache_key=cache_key).first()
        if entry:
            entry.movie_ids  = ids_str
            entry.created_at = datetime.utcnow()
            entry.expires_at = expires
        else:
            entry = RecommendationCache(cache_key=cache_key, movie_ids=ids_str, expires_at=expires)
            db.session.add(entry)
        db.session.commit()

    @staticmethod
    def get(cache_key):
        entry = RecommendationCache.query.filter_by(cache_key=cache_key).first()
        if not entry or not entry.is_valid():
            return None
        ids = entry.get_ids()
        movies_map = {m.id: m for m in Movie.query.filter(Movie.id.in_(ids)).all()}
        return [movies_map[i] for i in ids if i in movies_map]

    @staticmethod
    def invalidate(cache_key):
        RecommendationCache.query.filter_by(cache_key=cache_key).delete()
        db.session.commit()

    @staticmethod
    def invalidate_for_user(user_id):
        RecommendationCache.query.filter(
            RecommendationCache.cache_key.like(f'%user_{user_id}%')
        ).delete(synchronize_session=False)
        db.session.commit()

    @staticmethod
    def purge_expired():
        RecommendationCache.query.filter(
            RecommendationCache.expires_at < datetime.utcnow()
        ).delete(synchronize_session=False)
        db.session.commit()
