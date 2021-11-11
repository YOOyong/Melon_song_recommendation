from django.contrib import admin
from .models import UserPlaylist

# Register your models here.

class UserPlaylistAdmin(admin.ModelAdmin):
    raw_id_fields = ('playlist',)

admin.site.register(UserPlaylist, UserPlaylistAdmin)
