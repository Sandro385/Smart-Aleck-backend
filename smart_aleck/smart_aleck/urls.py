from django.contrib import admin
from django.urls import path, include
from scrapper import urls as scrap_urls
urlpatterns = [
    path('admin/', admin.site.urls),
    path('scrap/', include(scrap_urls)),
]
