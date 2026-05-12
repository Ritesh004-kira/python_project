"""
services/recommendation.py

Hybrid Recommendation Engine for Moctale
==========================================
Architecture:
  User Preferences
        ↓
  Hybrid Engine (weighted combination)
    ├── Popularity Engine   (review count × avg rating)
    ├── Content-Based Engine (TF-IDF cosine similarity)
    └── Collaborative Engine (TensorFlow Neural CF)
        ↓
  Final Combined Output
"""

import os
import random
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

try:
    import tensorflow as tf
    HAS_TF = True
except ImportError:
    HAS_TF = False

# Resolve data dir relative to this file: backend/services/ -> backend/ -> backend/data/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_BACKEND_DIR, "data", "cf_model.keras")


# ─────────────────────────────────────────────
# 1. POPULARITY ENGINE
# ─────────────────────────────────────────────
class PopularityEngine:
    """
    Ranks movies by a popularity score:
        score = avg_rating × log(1 + num_reviews)
    This rewards movies that are both highly rated AND widely reviewed.
    """

    def get_popular_movies(self, top_n=10, genre_filter=None):
        """Returns the top_n most popular movies, optionally filtered by genre."""
        from backend.models.database import Movie, Review
        import math

        movies = Movie.query.all()
        if not movies:
            return []

        scored = []
        for m in movies:
            if genre_filter and genre_filter.lower() not in m.genre.lower():
                continue
            num_reviews = len(m.reviews)
            avg_rating = (
                sum(r.rating for r in m.reviews) / num_reviews
                if num_reviews > 0 else 0.0
            )
            popularity_score = avg_rating * math.log1p(num_reviews)
            scored.append((m, popularity_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:top_n]]

    def get_trending_today(self):
        """Returns the single top-scored movie to serve as 'Movie of the Day'."""
        results = self.get_popular_movies(top_n=1)
        return results[0] if results else None


# ─────────────────────────────────────────────
# 2. CONTENT-BASED ENGINE
# ─────────────────────────────────────────────
class ContentBasedEngine:
    """
    Uses TF-IDF vectorisation on genre + description to find movies
    with similar thematic content using cosine similarity.
    """

    def __init__(self):
        self.tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.movie_df = None
        self.cosine_sim = None

    def _build_index(self):
        """Load movies from DB and build the TF-IDF cosine similarity matrix."""
        from backend.models.database import Movie

        movies = Movie.query.all()
        if not movies:
            return False

        rows = []
        for m in movies:
            # Normalise genre separator  ("Action|Comedy" → "Action Comedy")
            genre_text = m.genre.replace("|", " ").replace(",", " ")
            rows.append({
                "id": m.id,
                "title": m.title,
                "content": f"{genre_text} {genre_text} {m.description}",  # genre weighted ×2
            })

        self.movie_df = pd.DataFrame(rows)
        tfidf_matrix = self.tfidf.fit_transform(self.movie_df["content"])
        self.cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
        return True

    def get_similar_movies(self, movie_title, top_n=5):
        """Returns the top_n most content-similar movies for a given title."""
        if self.movie_df is None:
            if not self._build_index():
                return []

        matches = self.movie_df.index[self.movie_df["title"] == movie_title].tolist()
        if not matches:
            return []

        idx = matches[0]
        sim_scores = list(enumerate(self.cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1: top_n + 1]
        movie_indices = [i[0] for i in sim_scores]
        rec_ids = self.movie_df["id"].iloc[movie_indices].tolist()

        from backend.models.database import Movie
        return Movie.query.filter(Movie.id.in_(rec_ids)).all()

    def get_scores_for_movies(self, seed_movie_title, candidate_ids):
        """
        Returns a dict {movie_id: similarity_score} for hybrid weighting.
        """
        if self.movie_df is None:
            if not self._build_index():
                return {}

        matches = self.movie_df.index[self.movie_df["title"] == seed_movie_title].tolist()
        if not matches:
            return {}

        idx = matches[0]
        scores = {}
        for cid in candidate_ids:
            rows = self.movie_df.index[self.movie_df["id"] == cid].tolist()
            if rows:
                scores[cid] = float(self.cosine_sim[idx][rows[0]])
        return scores

    def invalidate_cache(self):
        """Call this after new movies are added to the database."""
        self.movie_df = None
        self.cosine_sim = None


# ─────────────────────────────────────────────
# 3. COLLABORATIVE FILTERING ENGINE (TensorFlow Neural CF)
# ─────────────────────────────────────────────
class CollaborativeEngine:
    """
    Neural Collaborative Filtering using TensorFlow/Keras.
    Architecture: user_embedding ⊕ movie_embedding → Dense layers → rating prediction
    """

    def __init__(self):
        self.model = None
        self.max_user_id = 1
        self.max_movie_id = 1
        self._try_load_model()

    def _try_load_model(self):
        """Load a previously trained model from disk if it exists."""
        if not HAS_TF:
            return
        if os.path.exists(MODEL_PATH):
            try:
                self.model = tf.keras.models.load_model(MODEL_PATH)
                print(f"[CollaborativeEngine] Loaded model from {MODEL_PATH}")
            except Exception as e:
                print(f"[CollaborativeEngine] Could not load model: {e}")

    def _build_model(self, num_users, num_movies, embedding_dim=32):
        user_input = tf.keras.layers.Input(shape=(1,), name="user_id")
        movie_input = tf.keras.layers.Input(shape=(1,), name="movie_id")

        user_emb = tf.keras.layers.Embedding(num_users + 1, embedding_dim)(user_input)
        movie_emb = tf.keras.layers.Embedding(num_movies + 1, embedding_dim)(movie_input)

        user_vec = tf.keras.layers.Flatten()(user_emb)
        movie_vec = tf.keras.layers.Flatten()(movie_emb)

        x = tf.keras.layers.Concatenate()([user_vec, movie_vec])
        x = tf.keras.layers.Dense(128, activation="relu")(x)
        x = tf.keras.layers.Dropout(0.2)(x)
        x = tf.keras.layers.Dense(64, activation="relu")(x)
        x = tf.keras.layers.Dense(1, activation="linear")(x)

        model = tf.keras.Model(inputs=[user_input, movie_input], outputs=x)
        model.compile(optimizer="adam", loss="mean_squared_error", metrics=["mae"])
        return model

    def train(self, epochs=10, batch_size=256):
        """Fetch all reviews from the DB and train the neural CF model."""
        if not HAS_TF:
            print("[CollaborativeEngine] TensorFlow not available — skipping training.")
            return False

        from backend.models.database import Review
        reviews = Review.query.all()
        if not reviews:
            print("[CollaborativeEngine] No reviews found — skipping training.")
            return False

        user_ids  = np.array([r.user_id  for r in reviews])
        movie_ids = np.array([r.movie_id for r in reviews])
        ratings   = np.array([r.rating   for r in reviews], dtype=np.float32)

        self.max_user_id  = int(user_ids.max())
        self.max_movie_id = int(movie_ids.max())

        self.model = self._build_model(self.max_user_id, self.max_movie_id)

        print(f"[CollaborativeEngine] Training on {len(reviews)} reviews "
              f"(users={self.max_user_id}, movies={self.max_movie_id}) ...")

        self.model.fit(
            [user_ids, movie_ids],
            ratings,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.1,
            verbose=1,
        )

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        self.model.save(MODEL_PATH)
        print(f"[CollaborativeEngine] Model saved to {MODEL_PATH}")
        return True

    def predict_scores(self, user_id, movie_ids):
        """
        Returns a dict {movie_id: predicted_rating} for a list of movie IDs.
        Falls back to 0.0 when TF is unavailable or model untrained.
        """
        if not HAS_TF or self.model is None:
            return {mid: 0.0 for mid in movie_ids}

        uid_arr  = np.array([user_id]   * len(movie_ids))
        mid_arr  = np.array(movie_ids)
        preds    = self.model.predict([uid_arr, mid_arr], verbose=0).flatten()
        return {mid: float(score) for mid, score in zip(movie_ids, preds)}

    def get_top_n(self, user_id, top_n=5, exclude_ids=None):
        """
        Returns the top_n Movie objects predicted to be most enjoyable for user_id.
        """
        from backend.models.database import Movie
        all_movies = Movie.query.all()
        if not all_movies:
            return []

        candidates = [m for m in all_movies
                      if exclude_ids is None or m.id not in exclude_ids]
        candidate_ids = [m.id for m in candidates]

        scores = self.predict_scores(user_id, candidate_ids)
        ranked = sorted(candidates, key=lambda m: scores.get(m.id, 0.0), reverse=True)
        return ranked[:top_n]


# ─────────────────────────────────────────────
# 4. HYBRID ENGINE
# ─────────────────────────────────────────────
class HybridRecommendationEngine:
    """
    Combines Popularity, Content-Based, and Collaborative engines
    with configurable weights to produce a final recommendation list.

    Default weights:
      popularity     = 0.2
      content_based  = 0.4
      collaborative  = 0.4  (falls back to 0.0 when model is untrained)
    """

    WEIGHTS = {
        "popularity":    0.20,
        "content_based": 0.40,
        "collaborative": 0.40,
    }

    def __init__(self):
        self.popularity   = PopularityEngine()
        self.content      = ContentBasedEngine()
        self.collaborative = CollaborativeEngine()

    # ------------------------------------------------------------------
    # Public API  (all methods are cache-aware)
    # ------------------------------------------------------------------

    def get_movie_of_the_day(self):
        """Returns the single most popular movie, cached for 6 hours."""
        from backend.models.database import RecommendationCache
        cached = RecommendationCache.get('motd')
        if cached:
            return cached[0]

        result = self.popularity.get_trending_today()
        if result:
            RecommendationCache.set('motd', [result], ttl_seconds=21600)
        return result

    def get_popular_movies(self, top_n=10, genre_filter=None):
        """Popularity-ranked list, cached for 2 hours."""
        from backend.models.database import RecommendationCache
        key = f'popular_genre_{genre_filter}_top{top_n}' if genre_filter else f'popular_top{top_n}'
        cached = RecommendationCache.get(key)
        if cached:
            return cached

        result = self.popularity.get_popular_movies(top_n=top_n, genre_filter=genre_filter)
        if result:
            RecommendationCache.set(key, result, ttl_seconds=7200)
        return result

    def get_similar_movies(self, movie_title, top_n=5):
        """Content-based similar movies, cached for 12 hours."""
        from backend.models.database import Movie, RecommendationCache
        seed = Movie.query.filter_by(title=movie_title).first()
        if not seed:
            return []
        key = f'content_{seed.id}_top{top_n}'
        cached = RecommendationCache.get(key)
        if cached:
            return cached

        result = self.content.get_similar_movies(movie_title, top_n=top_n)
        if result:
            RecommendationCache.set(key, result, ttl_seconds=43200)
        return result

    def get_recommendations_for_user(self, user_id, seed_movie_title=None, top_n=8):
        """
        Full hybrid pipeline, cached per user for 1 hour.
        Cache is busted automatically when the user submits a new review.
        """
        from backend.models.database import RecommendationCache
        key = f'hybrid_user_{user_id}_top{top_n}'
        cached = RecommendationCache.get(key)
        if cached:
            return cached

        # ── Engine 1: Popularity scores ─────────────────────────────
        from backend.models.database import Movie
        import math
        all_movies = Movie.query.all()
        if not all_movies:
            return []

        all_ids   = [m.id for m in all_movies]
        movie_map = {m.id: m for m in all_movies}

        pop_raw = {}
        for m in all_movies:
            nr = len(m.reviews)
            ar = sum(r.rating for r in m.reviews) / nr if nr > 0 else 0.0
            pop_raw[m.id] = ar * math.log1p(nr)

        # ── Engine 2: Content-based scores ──────────────────────────
        cb_raw = (
            self.content.get_scores_for_movies(seed_movie_title, all_ids)
            if seed_movie_title else {mid: 0.0 for mid in all_ids}
        )

        # ── Engine 3: Collaborative scores ──────────────────────────
        cf_raw = self.collaborative.predict_scores(user_id, all_ids)

        # ── Normalise & combine ──────────────────────────────────────
        def normalise(d):
            vals = list(d.values())
            lo, hi = min(vals), max(vals)
            if hi == lo:
                return {k: 0.0 for k in d}
            return {k: (v - lo) / (hi - lo) for k, v in d.items()}

        pop_n = normalise(pop_raw)
        cb_n  = normalise(cb_raw)
        cf_n  = normalise(cf_raw)
        w     = self.WEIGHTS

        hybrid_scores = {
            mid: (
                w["popularity"]    * pop_n.get(mid, 0.0)
                + w["content_based"] * cb_n.get(mid,  0.0)
                + w["collaborative"] * cf_n.get(mid,  0.0)
            )
            for mid in all_ids
        }

        ranked_ids = sorted(hybrid_scores, key=hybrid_scores.get, reverse=True)

        if seed_movie_title:
            from backend.models.database import Movie as M
            seed = M.query.filter_by(title=seed_movie_title).first()
            if seed and seed.id in ranked_ids:
                ranked_ids.remove(seed.id)

        result = [movie_map[mid] for mid in ranked_ids[:top_n] if mid in movie_map]

        # Store in cache
        if result:
            RecommendationCache.set(key, result, ttl_seconds=3600)

        return result

    def invalidate_user_cache(self, user_id):
        """
        Call this after a user submits a review so their next page load
        gets freshly computed recommendations.
        """
        from backend.models.database import RecommendationCache
        RecommendationCache.invalidate_for_user(user_id)

    def train_collaborative(self, epochs=10):
        """Triggers collaborative model training. Call from a training script."""
        return self.collaborative.train(epochs=epochs)

    def refresh_content_index(self):
        """Rebuild TF-IDF index and clear content-based cache entries."""
        from backend.models.database import RecommendationCache
        self.content.invalidate_cache()
        # Wipe all content-similarity cache rows
        from backend.models.database import db
        RecommendationCache.query.filter(
            RecommendationCache.cache_key.like('content_%')
        ).delete(synchronize_session=False)
        db.session.commit()


# ─────────────────────────────────────────────
# Singleton used across the Flask app
# ─────────────────────────────────────────────
recommender = HybridRecommendationEngine()
