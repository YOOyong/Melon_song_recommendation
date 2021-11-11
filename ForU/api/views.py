from collections import defaultdict
from django.shortcuts import render
from api.rec_model_loader import get_recommender
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Song,RecentSongs,UserTags,UserRecomTagNames,UnchaeRecommend
from .serializers import *
from django.core import serializers
from users.models import UserPlaylist
import json 
from ast import literal_eval
import random
import numpy as np
from django.db import connection
from datetime import datetime
from dateutil.relativedelta import relativedelta

class SingerRecommend(APIView):

    def get(self, request, *args, **kwargs):
        rec = get_recommender()
        if request.user.is_authenticated:
            user = request.user
            user_playlist_id = user.user_playlist.playlist.playlist_id
            
            user_playlist = rec.train.iloc[[user_playlist_id]]
        else:
            user_playlist = rec.train.sample(1)

        artist_list , song_list = rec.singer_recommend(user_playlist)
    
        artist_serializer = ArtistSerializer(Artist.objects.filter(artist_id__in = artist_list), many = True)
        song_serializer = SongSerializer(Song.objects.filter(song_id__in= song_list) ,many = True)
        
        data = {
            'artists' : artist_serializer.data,
            'songs' : song_serializer.data,
        }
        
        return Response(data)


# 최신 발매 인기곡 
class RecentlyHot(APIView):

    # GET요청 수신
    def get(self, request, *args, **kwargs):

        # 최근날짜 입력 하는 부분, datetime.now()로 바꾸면 계속해서 최신화된 날짜로 만들 수 있음
        recent_date = datetime.strptime('2020-04-23',"%Y-%m-%d")

        # 최신의 날짜로 부터 한달전의 날짜
        recent_date_month_ago = recent_date - relativedelta(months=1)
       
        # 질의를 하기위한 쿼리문
        query = f'''select 1 id,thumb_url,artist_name,song_name,genre_big_name,added_cnt,album_id from (select sa.song_id,sa.thumb_url,artist_name,song_name,artist_main_genre,added_cnt,album_id from (select artist_id,s.song_id,song_name,thumb_url,added_cnt,album_id from (select song_id,song_name,thumb_url,added_cnt,album_id from (select s.song_id,song_name,thumb_url,playlist_id,added_cnt,album_id from (select song_id,song_name,thumb_url,added_cnt,album_id from song where issue_date between '{str(recent_date_month_ago)[0:10]}' and '{str(recent_date)[0:10]}' and added_cnt > 15) as s join playlist_song as ps on s.song_id = ps.song_id group by song_id) as ps join playlist as p on ps.playlist_id = p.playlist_id where like_cnt > 10 order by added_cnt desc limit 30) as s join artist_song as sa on s.song_id = sa.song_id) as sa join artist as a on sa.artist_id = a.artist_id group by song_id) as l join genre_big as r on l.artist_main_genre = r.genre_big_code order by added_cnt desc;'''
        
        # RecentSong model에 Rawquery형식으로 데이터를 받아 저장, 원하는 field는 썸네일주소,가수명,노래명,대장르이름,앨범id(melon앨범 페이지로 이동하기 위함)
        recently_hot = serializers.serialize('json', RecentSongs.objects.raw(query), fields=('thumb_url' ,'artist_name', 'song_name' ,'genre_big_name','album_id'))

        # context에 데이터를 담아
        context = {
            'recently_hot' : recently_hot
        }

        # Response
        return Response(context)

# 사용자의 태그와 유사한 태그를 추천
class TagRecommend(APIView):

    # GET요청 수신
    def get(self, request, *args, **kwargs):

        # 추천기능 객체 생성
        rec = get_recommender()

        # 로그인이 되었을떄
        if request.user.is_authenticated:

            # 사용자의 playlist_id를 가져옴
            user_playlist_id = request.user.user_playlist.playlist.playlist_id

            # playlist_id가 한개일때 쿼리
            if type(user_playlist_id) is int:
                query = f'select 1 id,tag.tag_id from (select tag_id from playlist join playlist_tag on playlist.playlist_id = playlist_tag.playlist_id where playlist.playlist_id = {user_playlist_id}) as pt join tag on pt.tag_id = tag.tag_id;'
            
            # playlist_id가 list일때 쿼리
            else:
                pid_str  = ','.join([str(x) for x in user_playlist_id])
                query = f'select 1 id,tag.tag_id from (select tag_id from playlist join playlist_tag on playlist.playlist_id = playlist_tag.playlist_id where playlist.playlist_id in ({pid_str})) as pt join tag on pt.tag_id = tag.tag_id;'

            # UserTags model에 Rawquery형식으로 데이터를 받아 저장
            tags_of_user = UserTags.objects.raw(query)

            # Rawquery에 tag들만 수집
            tag_list = []

            for tag in tags_of_user:
                tag_list.append(tag.tag_id)

            # 추천기능 객체의 멤버함수를 이용해서 새로운 추천을 수행
            recom_tag_list = rec.tag_recommend_with_genred(tag_list)

            # 추천된 태그의 id를 수집해 쿼리 수행
            result_tag_ids  = ','.join([str(x) for x in recom_tag_list])
            tag_recom_query = f'select 1 id,tag from tag where tag_id in ({result_tag_ids});'

            # UserRecomTagNames model에 Rawquery형식으로 데이터를 받아 저장 (추천 받은 태그명이 들어있음)
            query_result = UserRecomTagNames.objects.raw(tag_recom_query)
            recom_tag_list = []

            # 받은 태그명 response
            for recom_tag in query_result:
                recom_tag_list.append(recom_tag.tag)

            context = {
                'tags' : recom_tag_list,
                'login' : 'yes',
            }

            return Response(context)

        else:
            # 최근날짜 입력 하는 부분, datetime.now()로 바꾸면 계속해서 최신화된 날짜로 만들 수 있음
            recent_date = datetime.strptime('2020-04-23',"%Y-%m-%d")

            # 최신의 날짜로 부터 한달전의 날짜
            recent_date_month_ago = recent_date - relativedelta(months=1)


            # 태그가 사용된 빈도로 상위 10개 query
            hot_tag_query = f'''select 1 id,tag from (select t.tag_id, count(t.tag_id) as t_cnt from playlist as p join playlist_tag as t on p.playlist_id = t.playlist_id where like_cnt > 30 and update_date between '{recent_date_month_ago}' and '{recent_date}' group by t.tag_id order by t_cnt desc Limit 10) as p join tag as t on p.tag_id = t.tag_id;'''
            
            # UserRecomTagNames model에 Rawquery형식으로 데이터를 받아 저장 (인기 태그명이 들어있음)
            query_result = UserRecomTagNames.objects.raw(hot_tag_query)
            hot_tag_list = []

            # 받은 태그명 response
            for tag in query_result:
                hot_tag_list.append(tag.tag)

            context = {
                'tags' : hot_tag_list,
                'login' : 'no',
            }

            return Response(context)

class RecentSingerRecommend(APIView):
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(None)
        else:
            rec = get_recommender()

            user = request.user
            user_playlist_id = user.user_playlist.playlist.playlist_id

            last_song_id = rec.train.loc[user_playlist_id,'songs'][-1]
            last_song_singer = Song.objects.get(song_id = last_song_id).artists.all()    

            songs = last_song_singer.first().songs.all()
            artist_serializer = ArtistSerializer(last_song_singer, many = True) 
            if len(songs) < 15:
                song_serializer = SongSerializer(songs, many = True)

            else:    
                song_serializer = SongSerializer(random.sample(list(songs), 15), many = True)

            data = {
            'artists' : artist_serializer.data,
            'songs' : song_serializer.data,
            }

            return Response(data)


class AlsRecommend(APIView):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(None)
        else:
            rec = get_recommender()
            
            user = request.user
            user_playlist_id = user.user_playlist.playlist.playlist_id
            
            als_model = rec.als_model
            songs_scores = als_model.recommend(user_playlist_id, als_model.ply_song_table, N = 30)
            song_list = [x for x,_ in songs_scores]
            song_id_list = [als_model.id_to_song[x] for x in song_list]

            song_queryset = Song.objects.filter(song_id__in = song_id_list)

            serializer = SongSerializer(song_queryset, many = True)

            return Response(serializer.data)

class TagSearchApi(APIView):
    def get(self, request, *args, **kwargs):
        tags = request.GET.get('tags')
        rec = get_recommender()

        processed_tag_list = rec.konlpy_preprocessing(tags).split()
        processed_tag = " ".join([i for i in processed_tag_list if rec.s2v_model.embed_sentence(i).sum() != 0])

        if rec.s2v_model.embed_sentence(processed_tag).sum() == 0.0:
             return Response(None) 
            
        else:
            playlists_id = rec.get_playlist_with_tag(processed_tag, k_n=2)

            song_list = np.concatenate(rec.train.iloc[playlists_id]['songs'].tolist())
            song_list_30 = random.sample(list(song_list), 30)
            serializer =  SongSerializer( Song.objects.filter(song_id__in= song_list_30),many = True)

            return Response(serializer.data)

# 플레이리스트 추천
class UnchaeRecommender(APIView):

    # GET방식으로 통신
    def get(self, request, *args, **kwargs):

        # 로그인 하지 않았다면
        if not request.user.is_authenticated:

            # 최근날짜 입력 하는 부분, datetime.now()로 바꾸면 계속해서 최신화된 날짜로 만들 수 있음
            recent_date = datetime.strptime('2020-04-23',"%Y-%m-%d")

            # 최신의 날짜로 부터 한달전의 날짜
            recent_date_month_ago = recent_date - relativedelta(months=1)
            
            # 최근 수정된 플레이리스트 중 좋아요가 많이 눌린 상위 5개의 플레이리스트를 뽑고 각 플레이리스트 마다 인기가 많은 곡 상위 네개를 가져오는 쿼리
            query = f'''SELECT 1 id,album_id,playlist_title,thumb_url,playlist_id FROM (SELECT album_id,thumb_url,@playlist_rank := IF(@current_playlist = playlist_id, @playlist_rank + 1,1) AS p_rank, @current_playlist := playlist_id AS playlist_id, added_cnt, like_cnt,playlist_title FROM (SELECT album_id, playlist_title,s.song_id,s.thumb_url,playlist_id,added_cnt,like_cnt FROM (SELECT ps.playlist_id,ps.song_id,playlist_title,like_cnt FROM (SELECT playlist_id,playlist_title,like_cnt FROM playlist WHERE update_date BETWEEN '{str(recent_date_month_ago)[0:10]}' and '{str(recent_date)[0:10]}' ORDER BY like_cnt DESC LIMIT 5) AS pid JOIN playlist_song AS ps ON pid.playlist_id = ps.playlist_id) AS ps_id JOIN song AS s ON ps_id.song_id = s.song_id ORDER BY playlist_id,added_cnt DESC) AS c) AS d WHERE p_rank < 5 order by like_cnt desc , p_rank asc;'''

            # 쿼리에서 결과를 json으로 직렬화
            unchae_recommend = serializers.serialize('json', UnchaeRecommend.objects.raw(query), fields=('album_id','playlist_title','thumb_url','playlist_id'))

            context = {
                'unchae_recommend' : unchae_recommend,
            }

        # 로그인을 했다면
        else:

            # 추천기능 가져오기
            rec = get_recommender()
            
            # user의 playlist_id를 저장
            user_playlist_id = request.user.user_playlist.playlist.playlist_id
            
            # 플레이리스트 추천용 als모델 불러오기
            als_unchae = rec.als_unchae

            # 내 플레이리스트랑 가장 비슷한 플레이리스트 6개 불러오기 (내 플레이리스트가 첫번째)
            find_top5_ply = als_unchae.similar_items(user_playlist_id,N=6)

            # 두번째플레이리스트 부터 playlist_id를 저장
            top5 = list(map(lambda x : str(x[0]),find_top5_ply[1:]))
            
            # playlist_id를 str으로 만들어 query에 활용
            top5_query = ','.join(top5)

            # 추천된 플레이리스트중 인기가 가장 많은 곡 상위 4개의 정보를 불러옴
            query = f'SELECT 1 id,album_id,playlist_title,thumb_url,playlist_id FROM (SELECT album_id,thumb_url,@playlist_rank := IF(@current_playlist = playlist_id, @playlist_rank + 1,1) AS p_rank, @current_playlist := playlist_id AS playlist_id, added_cnt, like_cnt,playlist_title FROM (SELECT album_id, playlist_title,s.song_id,s.thumb_url,playlist_id,added_cnt,like_cnt FROM (SELECT ps.playlist_id,ps.song_id,playlist_title,like_cnt FROM (SELECT playlist_id,playlist_title,like_cnt FROM playlist WHERE playlist_id IN ({top5_query}) ORDER BY like_cnt DESC LIMIT 5) AS pid JOIN playlist_song AS ps ON pid.playlist_id = ps.playlist_id) AS ps_id JOIN song AS s ON ps_id.song_id = s.song_id ORDER BY playlist_id,added_cnt DESC) AS c) AS d WHERE p_rank < 5 order by like_cnt desc , p_rank asc;'
            
            # 쿼리 결과를 json으로 직렬화 하여 저장
            unchae_recommend = serializers.serialize('json', UnchaeRecommend.objects.raw(query), fields=('album_id','playlist_title','thumb_url','playlist_id'))
            
            context = {
                'unchae_recommend' : unchae_recommend
            }

        return Response(context)


# 플레이리스트 추천
class Mytags(APIView):

    # GET방식으로 통신
    def get(self, request, *args, **kwargs):

        # 로그인 하지 않았다면
        if not request.user.is_authenticated:    

                context = {
                    'login' : "no",
                }

        else:

            # user의 playlist_id를 저장
            user_playlist_id = request.user.user_playlist.playlist.playlist_id

            query = f'''select 1 id, tag from (select t.tag_id from playlist as p join playlist_tag as t on p.playlist_id = t.playlist_id where p.playlist_id = {user_playlist_id}) as p join tag as t on p.tag_id = t.tag_id where added_cnt > 16;'''

            cursor = connection.cursor()
        
            # 쿼리실행
            cursor.execute(query)

            # 실행결과의 list
            rows = cursor.fetchall()
            
            dict_data = defaultdict(list)

            # row들을 돌면서 dict를 생성
            for row in rows:
                dict_data['tag'].append(row[1])
    
            context = {
                'login' : "yes",
                'my_tag' : dict_data,
            }

        return Response(context)
