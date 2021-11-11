from django.db import models
from django.contrib.auth.models import User
from api.models import Playlist
# Create your models here.


class UserPlaylist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_playlist')
    playlist = models.ForeignKey(Playlist, related_name='user' ,null=True, blank=True ,on_delete=models.DO_NOTHING)


    def __str__(self) -> str:
        return self.user.username + " "  +str(self.playlist.playlist_id)