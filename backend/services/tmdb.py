import os
import requests
from urllib.parse import urljoin

# Load TMDB API key from environment or fallback to hardcoded (replace with secure config in production)
TMDB_API_KEY = os.getenv('TMDB_API_KEY', '8265bd1679663a7ea12ac168da84d2e8')
BASE_URL = 'https://api.themoviedb.org/3/'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/'


def _request(endpoint: str, params: dict = None):
    """Internal helper to perform a GET request to TMDB API.
    Args:
        endpoint: API endpoint path, e.g. 'movie/popular'.
        params: Additional query parameters.
    Returns:
        JSON response dict.
    Raises:
        requests.HTTPError on non‑200 responses.
    """
    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    url = urljoin(BASE_URL, endpoint)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def search_tmdb(query: str, page: int = 1):
    """Search TMDB for movies matching the query.
    Returns a list of movie dicts as returned by TMDB.
    """
    return _request('search/movie', {'query': query, 'page': page})


def get_movie_details(tmdb_id: int):
    """Fetch detailed information for a movie, including videos and credits.
    The `append_to_response` parameter pulls videos and credits in a single call.
    """
    return _request(f'movie/{tmdb_id}', {'append_to_response': 'videos,credits'})


def poster_url(path: str, size: str = 'w500'):
    """Construct full poster image URL.
    Size options: w92, w154, w185, w342, w500, w780, original.
    """
    if not path:
        return ''
    return f"{IMAGE_BASE_URL}{size}{path}"


def backdrop_url(path: str, size: str = 'w1280'):
    """Construct full backdrop image URL.
    Size options: w300, w780, w1280, original.
    """
    if not path:
        return ''
    return f"{IMAGE_BASE_URL}{size}{path}"


def get_trailer_key(movie_data: dict) -> str:
    """Extract the first YouTube trailer key from the movie's video list.
    Returns empty string if none found.
    """
    videos = movie_data.get('videos', {}).get('results', [])
    for vid in videos:
        if vid.get('site') == 'YouTube' and vid.get('type') == 'Trailer':
            return vid.get('key', '')
    return ''


def get_top_cast(movie_data: dict, limit: int = 5) -> list:
    """Return a list of top cast members (name and character).
    """
    cast = movie_data.get('credits', {}).get('cast', [])[:limit]
    return [{'name': c.get('name'), 'character': c.get('character')} for c in cast]


def get_director(movie_data: dict) -> str:
    """Extract director name from crew list.
    """
    crew = movie_data.get('credits', {}).get('crew', [])
    for member in crew:
        if member.get('job') == 'Director':
            return member.get('name', '')
    return ''
