from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportView.as_view(), name='home'),
    path('export/csv/', views.ExportCSVView.as_view(), name='export_csv'),
]
