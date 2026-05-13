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
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(255), nullable=False)
    year = db.Column(db.String(4), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    rating = db.Column(db.Float, default=0.0)

    reviews = db.relationship('Review', backref='movie', lazy=True, order_by="Review.created_at.desc()")

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Float, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_info = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class RecommendationCache(db.Model):
    """
    Stores serialised recommendation results keyed by a string.

    Key format conventions:
      "hybrid_user_{user_id}"          — personalised homepage recs
      "popular_top{n}"                 — global popularity list
      "popular_genre_{genre}_top{n}"   — genre-filtered popularity
      "content_{movie_id}_top{n}"      — content-based similar movies
      "motd"                           — Movie of the Day id
    """
    __tablename__ = 'recommendation_cache'

    id         = db.Column(db.Integer, primary_key=True)
    cache_key  = db.Column(db.String(255), unique=True, nullable=False, index=True)
    # Comma-separated movie IDs in ranked order, e.g. "42,7,301,88"
    movie_ids  = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_valid(self):
        return datetime.utcnow() < self.expires_at

    def get_ids(self):
        """Deserialise the stored comma-separated IDs back to a list of ints."""
        return [int(x) for x in self.movie_ids.split(',') if x.strip()]

    @staticmethod
    def set(cache_key, movie_list, ttl_seconds=3600):
        """
        Upsert a cache entry.
        :param cache_key: Unique string key.
        :param movie_list: List of Movie ORM objects (ordered).
        :param ttl_seconds: How long (seconds) before this entry expires. Default 1 hour.
        """
        from datetime import timedelta
        ids_str = ','.join(str(m.id) for m in movie_list)
        expires = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        entry = RecommendationCache.query.filter_by(cache_key=cache_key).first()
        if entry:
            entry.movie_ids  = ids_str
            entry.created_at = datetime.utcnow()
            entry.expires_at = expires
        else:
            entry = RecommendationCache(
                cache_key=cache_key,
                movie_ids=ids_str,
                expires_at=expires,
            )
            db.session.add(entry)
        db.session.commit()

    @staticmethod
    def get(cache_key):
        """
        Fetch a valid (non-expired) cache entry and return ordered Movie objects,
        or None if missing / expired.
        """
        entry = RecommendationCache.query.filter_by(cache_key=cache_key).first()
        if not entry or not entry.is_valid():
            return None
        ids = entry.get_ids()
        # Preserve the ranked order by fetching all and re-sorting
        movies_map = {m.id: m for m in Movie.query.filter(Movie.id.in_(ids)).all()}
        return [movies_map[i] for i in ids if i in movies_map]

    @staticmethod
    def invalidate(cache_key):
        """Delete a single cache entry."""
        RecommendationCache.query.filter_by(cache_key=cache_key).delete()
        db.session.commit()

    @staticmethod
    def invalidate_for_user(user_id):
        """Delete all cached recs that belong to a specific user."""
        RecommendationCache.query.filter(
            RecommendationCache.cache_key.like(f'%user_{user_id}%')
        ).delete(synchronize_session=False)
        db.session.commit()

    @staticmethod
    def purge_expired():
        """Remove all expired entries (call periodically or on startup)."""
        RecommendationCache.query.filter(
            RecommendationCache.expires_at < datetime.utcnow()
        ).delete(synchronize_session=False)
        db.session.commit()
