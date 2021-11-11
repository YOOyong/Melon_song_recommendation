from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core import serializers
from django.db import connection
import json

class IndexView(TemplateView):
    template_name = 'index.html'

# 플레이리스트에 수록된 노래 정보 띄워주는 api
class ShowPlayList(APIView):

    #GET요청이 들어오면!
    def get(self, request, *args, **kwargs):

        # playlist_id를 전달받았다
        pid = request.GET.get('playlist_id')

        # 데이터베이스에서 전달받은 playlist의 노래명,앨범아트,가수명을 불러온다.
        query = f"select song_name,apsa.thumb_url,artist_name,song_id from (select song_name,thumb_url,album_id,ars.song_id,artist_id,added_cnt from (select song_name,thumb_url,album_id,s.song_id,s.added_cnt from (select song_id from playlist as p join playlist_song as ps on p.playlist_id = ps.playlist_id where p.playlist_id = {pid}) as pps join song as s on pps.song_id = s.song_id order by added_cnt desc Limit 30) as aps join artist_song as ars on aps.song_id = ars.song_id) as apsa join artist as a on apsa.artist_id = a.artist_id group by song_id;"
        
        # DTO객체 보단 직접 json형식을 만들어서 보내보자
        # 커서 생성
        cursor = connection.cursor()
        
        # 쿼리실행
        cursor.execute(query)

        # 실행결과의 list
        rows = cursor.fetchall()

        # 각 데이터의 키값을 미리설정
        keys = ['song_name','thumb_url','artist_name']
        
        dict_data = []

        # row들을 돌면서 dict를 생성
        for row in rows:
            temp_dict = {}
            for k,v in zip(keys,row):
                temp_dict[k] = v
            dict_data.append(temp_dict)
        
        #json형식으로 response
        return HttpResponse(json.dumps(dict_data))