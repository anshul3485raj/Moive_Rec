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
    def get(self, request):
        query = request.GET.get("movie", "").strip()
        if not query:
            return JsonResponse({"error": "No movie name provided"}, status=400)

        # Search movie via TMDb API
        search_url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"
        search_response = requests.get(search_url).json()

        if "results" not in search_response or not search_response["results"]:
            return JsonResponse({"error": "Movie not found"}, status=404)

        movie_data = search_response["results"][0]
        movie_id = movie_data["id"]

        # Fetch full movie details
        details_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,reviews,recommendations,similar"
        details_response = requests.get(details_url).json()

        # Extract fields
        title = details_response.get("title")
        genre = ", ".join([g["name"] for g in details_response.get("genres", [])])
        release_date = details_response.get("release_date") or "2000-01-01"
        runtime = details_response.get("runtime") or 0
        description = details_response.get("overview")
        poster_path = details_response.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""

        # Save to DB (or update if already exists)
        movie, created = Movie.objects.get_or_create(
            title=title,
            defaults={
                "genre": genre,
                "release_date": release_date,
                "runtime": runtime,
                "description": description,
                "poster_url": poster_url
            }
        )

        # Save query to SearchHistory
        SearchHistory.objects.create(user=None, query=query, timestamp=now())

        return JsonResponse({
            "id": movie.id,
            "title": movie.title,
            "poster": movie.poster_url,
            "overview": movie.description,
            "genres": movie.genre,
            "release_date": str(movie.release_date),
            "runtime": f"{movie.runtime} min",
            "status": "Stored",
            "likes": {
                "likes": UserInteraction.objects.filter(movie=movie, liked=True).count(),
                "dislikes": UserInteraction.objects.filter(movie=movie, disliked=True).count()
            },
            "similar_movies": {
                f"https://image.tmdb.org/t/p/w500{sim['poster_path']}": sim["title"]
                for sim in details_response.get("similar", {}).get("results", [])[:4]
                if sim.get("poster_path")
            }
        })

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
