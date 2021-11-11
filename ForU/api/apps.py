from django.apps import AppConfig
from api.rec_model_loader import load_recommender

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        load_recommender()