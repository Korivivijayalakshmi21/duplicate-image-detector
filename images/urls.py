from django.urls import path
from . import views

app_name = 'images'

urlpatterns = [
    path('', views.ImageLibraryView.as_view(), name='library'),
    path('upload/', views.ImageUploadView.as_view(), name='upload'),
    path('<int:pk>/', views.ImageDetailView.as_view(), name='detail'),
    path('<int:pk>/delete/', views.ImageDeleteView.as_view(), name='delete'),
    path('compare/', views.ImageCompareView.as_view(), name='compare'),
    path('groups/', views.DuplicateGroupListView.as_view(), name='groups'),
    path('groups/<int:pk>/', views.DuplicateGroupDetailView.as_view(), name='group_detail'),
]
