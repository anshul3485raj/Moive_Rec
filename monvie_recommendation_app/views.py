import requests
import json
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.http import JsonResponse
from django.middleware.csrf import get_token
from .models import SearchHistory , Movie
from django.utils.timezone import now
# TMDb API Key (Replace with your actual API key)
TMDB_API_KEY = "32853102d718fa723628c30fd7f85532"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Temporary storage for likes/dislikes
MOVIE_LIKES = {}

class HomeView(View):
    """Renders the homepage with movie search functionality."""
    def get(self, request):
        return render(request, 'home.html')

class MovieSearchView(View):
    """Fetches movie details dynamically using TMDb API."""
    def get(self, request):
        query = request.GET.get("movie", "").strip().lower()
        if not query:
            return JsonResponse({"error": "No movie name provided"}, status=400)

        # TMDb Search API Call
        search_url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"
        search_response = requests.get(search_url).json()

        if "results" not in search_response or not search_response["results"]:
            return JsonResponse({"error": "Movie not found"}, status=404)

        # Get the first movie match
        movie = search_response["results"][0]
        movie_id = movie["id"]

        # Fetch full movie details
        details_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,reviews,recommendations,similar"
        details_response = requests.get(details_url).json()

        # Extract relevant details
        movie_data = {
            "id": movie_id,
            "title": details_response.get("title"),
            "poster": f"https://image.tmdb.org/t/p/w500{details_response.get('poster_path')}" if details_response.get('poster_path') else "",
            "overview": details_response.get("overview"),
            "vote_average": details_response.get("vote_average"),
            "vote_count": details_response.get("vote_count"),
            "genres": ", ".join([genre["name"] for genre in details_response.get("genres", [])]),
            "release_date": details_response.get("release_date"),
            "runtime": f"{details_response.get('runtime')} min" if details_response.get("runtime") else "N/A",
            "status": details_response.get("status"),
            "likes": MOVIE_LIKES.get(movie_id, {"likes": 0, "dislikes": 0}),
            "cast_details": {
                cast["name"]: {
                    "image": f"https://image.tmdb.org/t/p/w500{cast['profile_path']}" if cast.get('profile_path') else "",
                    "character": cast["character"]
                } for cast in details_response.get("credits", {}).get("cast", [])[:5]  # Top 5 Cast Members
            },
            "reviews": {
                review["content"]: "Good" if review["author_details"].get("rating", 5) >= 5 else "Bad"
                for review in details_response.get("reviews", {}).get("results", [])[:3]  # First 3 Reviews
            },
            "movie_cards": {
                f"https://image.tmdb.org/t/p/w500{rec['poster_path']}": rec["title"]
                for rec in details_response.get("recommendations", {}).get("results", [])[:4]  # First 4 Recommendations
                if rec.get("poster_path")
            },
            "similar_movies": {
                f"https://image.tmdb.org/t/p/w500{sim['poster_path']}": sim["title"]
                for sim in details_response.get("similar", {}).get("results", [])[:4]  # First 4 Similar Movies
                if sim.get("poster_path")
            }
        }

        return JsonResponse(movie_data)

class LikeDislikeView(View):
    """Handles like and dislike functionality for movies."""
    def post(self, request):
        try:
            data = json.loads(request.body)  # Parse JSON data
            movie_id = str(data.get("movie_id"))  # Ensure movie_id is a string
            action = data.get("action")

            if not movie_id or action not in ["like", "dislike"]:
                return JsonResponse({"error": "Invalid request"}, status=400)

            # Initialize likes/dislikes if not present
            if movie_id not in MOVIE_LIKES:
                MOVIE_LIKES[movie_id] = {"likes": 0, "dislikes": 0}

            if action == "like":
                MOVIE_LIKES[movie_id]["likes"] += 1
            elif action == "dislike":
                MOVIE_LIKES[movie_id]["dislikes"] += 1

            return JsonResponse({
                "likes": MOVIE_LIKES[movie_id]["likes"],
                "dislikes": MOVIE_LIKES[movie_id]["dislikes"]
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    def get(self, request):
        """Returns CSRF token for AJAX requests."""
        return JsonResponse({"csrfToken": get_token(request)})



## views.py - Include a like/dislike view
from django.http import JsonResponse
from .models import Movie, UserInteraction, SearchHistory
import json
from django.utils.timezone import now

def like_dislike_movie(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            movie_id = data.get('movie_id')
            action = data.get('action')

            if not movie_id or action not in ['like', 'dislike']:
                return JsonResponse({'error': 'Invalid data'}, status=400)

            movie = Movie.objects.get(id=movie_id)

            # Check if there's already a like/dislike for this movie (no user-based filtering)
            interaction = UserInteraction.objects.filter(user=None, movie=movie).first()
            if interaction:
                if action == 'like' and interaction.liked:
                    return JsonResponse({'error': 'Already liked'}, status=400)
                if action == 'dislike' and interaction.disliked:
                    return JsonResponse({'error': 'Already disliked'}, status=400)
            else:
                interaction = UserInteraction(user=None, movie=movie)

            if action == 'like':
                interaction.liked = True
                interaction.disliked = False
            elif action == 'dislike':
                interaction.liked = False
                interaction.disliked = True

            interaction.save()

            likes_count = UserInteraction.objects.filter(movie=movie, liked=True).count()
            dislikes_count = UserInteraction.objects.filter(movie=movie, disliked=True).count()

            return JsonResponse({'likes': likes_count, 'dislikes': dislikes_count})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def search_movies(request):
    query = request.GET.get('query')
    if query:
        SearchHistory.objects.create(user=None, query=query, timestamp=now())
    results = Movie.objects.filter(title__icontains=query)
    return render(request, 'search_results.html', {'results': results})
