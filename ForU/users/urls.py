from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from .views import UserDetailView, UserPreferInfo

app_name = 'users'
urlpatterns = [
    path('login/', LoginView.as_view(template_name = 'login_templates/login.html'), name = 'login'),
    path('logout/', LogoutView.as_view(), name= 'logout'),
    path('<str:username>', UserDetailView.as_view(), name='user_info'),
    path('<str:username>/info', UserPreferInfo.as_view(), name = 'user_prefer_info'),
]

