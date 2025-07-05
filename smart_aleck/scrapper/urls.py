from django.urls import path
from scrapper import views

urlpatterns = [
    path('scrap/', views.scrap, name="scrap"),
    path('upsert/', views.PineUpsertAPI.as_view(), name="vector upload"),
    path('query/', views.SimpleQueryAPI.as_view(), name="vector query"),
    path('assistant/', views.AssistantAPI.as_view(), name="assistant query"),
]
