from django.contrib import admin
from django.urls import path, include
from django.urls.resolvers import URLPattern
from api import views

app_name = 'api'

urlpatterns = [
    path('singer_recommend_api', views.SingerRecommend.as_view(), name = 'singer_recommend'),
    path('recently_hot_api', views.RecentlyHot.as_view(), name = 'recently_hot'),
    path('tag_recommend', views.TagRecommend.as_view(), name = 'tag_recommend'),
    path('recent_singer_api', views.RecentSingerRecommend.as_view(), name = 'recent_singer_api'),
    path('als_recommend_api', views.AlsRecommend.as_view(), name = 'als_recommend_api'),
    path('unchae_recommend_api', views.UnchaeRecommender.as_view(), name='unchae_recommend'),
    path('tag_search_api', views.TagSearchApi.as_view(), name= 'tag_search_api'),
    path('my_tag_api', views.Mytags.as_view(), name= 'my_tag_api'),
    
]   