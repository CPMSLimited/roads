from django.shortcuts import render

def landing(request):
    return render(request, "website/landing.html")

def road_analysis(request):
    return render(request, "website/road_analysis.html")

def uploads(request):
    return render(request, "website/uploads.html")
