from django.urls import path
from scrapper import views

urlpatterns = [
    path('scrap/', views.scrap, name="scrap"),
]