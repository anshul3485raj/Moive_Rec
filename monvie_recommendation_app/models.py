# models.py
from django.db import models
from django.contrib.auth.models import User

class Movie(models.Model):
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=200)
    release_date = models.DateField()
    runtime = models.IntegerField(help_text='Runtime in minutes')
    description = models.TextField(blank=True)
    poster_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return self.title

class UserInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    liked = models.BooleanField(default=False)
    disliked = models.BooleanField(default=False)
    watched = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    query = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} searched for '{self.query}' on {self.timestamp}"
