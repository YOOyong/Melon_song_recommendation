from rest_framework import serializers
from .models import Song, Artist


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ('artist_id','artist_name','thumb_url',)
        read_only_fields = fields


class SongSerializer(serializers.ModelSerializer):
    artists = ArtistSerializer(read_only = True, many = True)
    class Meta:
        model = Song
        fields = ('song_id','song_name','artists','thumb_url','album_id',)
