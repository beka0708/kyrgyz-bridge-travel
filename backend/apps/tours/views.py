from django.shortcuts import get_object_or_404, render

from apps.core.maps import map_config

from .models import Tour


def tour_list(request):
    tours = Tour.objects.published()
    tour_type = request.GET.get("type")
    if tour_type:
        tours = tours.filter(tour_type=tour_type)
    return render(request, "pages/tour_list.html", {"tours": tours, "tour_type": tour_type})


def tour_detail(request, slug):
    # Staff can preview unpublished tours from the admin («Смотреть на сайте»).
    tours = Tour.objects.all() if request.user.is_staff else Tour.objects.published()
    tour = get_object_or_404(tours.prefetch_related("days", "images", "list_items"), slug=slug)
    route_props = {
        "map": map_config(),
        "days": [
            {
                "day_number": day.day_number,
                "title": day.title,
                "waypoints": day.waypoints,
                "track": day.track,
                "track_source": day.track_source,
            }
            for day in tour.days.all()
        ],
    }
    return render(request, "pages/tour_detail.html", {"tour": tour, "route_props": route_props})
