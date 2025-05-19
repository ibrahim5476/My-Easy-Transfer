from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),  # URL pour l'inscription
    path('home/', views.home, name='home'),]
path('', views.home, name='home')
from django.shortcuts import render
