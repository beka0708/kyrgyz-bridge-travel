from django.shortcuts import render

from apps.tours.models import Tour


def home(request):
    # Placeholder until the frontend stage; the real page is built from the mockups.
    tours = Tour.objects.published()
    return render(request, "pages/home.html", {"tours": tours})
