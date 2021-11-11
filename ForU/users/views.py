from typing import DefaultDict
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection
import random
from collections import Counter
# Create your views here.

class UserDetailView(DetailView):
    template_name = "user_info.html"

    def get_object(self):
        return get_object_or_404(User, username=self.kwargs['username'])

    def get_context_data(self,*args, **kwargs):

        user = self.get_object()        
        context = super().get_context_data(*args, **kwargs)
        playlist_id = user.user_playlist.playlist.playlist_id     
        
        cursor = connection.cursor()
        cursor.execute(f'''
                        select distinct a.artist_name, a.thumb_url
                        from (select song_id,artist_id 
                                from artist_song 
                                where song_id in (select v.song_id
                                                    from (select * 
                                                            from playlist_song 
                                                            where playlist_id = { playlist_id } ) as v)) as s 
                        join artist as a on s.artist_id = a.artist_id;
                        ''')
                    
        result = cursor.fetchall()

        print(type(result))
        context['artists'] = result

        return context

class UserPreferInfo(APIView):
    def get(self, request, *args, **kwargs):
        user = get_object_or_404(User, username=self.kwargs['username'])
        playlist_id = user.user_playlist.playlist.playlist_id 

        #가수 카운트
        cursor = connection.cursor()
        cursor.execute(f'''
                        select Q.artist_name, count(Q.artist_name) as count
                        from   (select A.artist_name
                                from (select song_id
                                        from playlist_song
                                        where playlist_id = {playlist_id}) as s
                                inner join artist_song as a on a.song_id = s.song_id
                                inner join artist as A on A.artist_id = a.artist_id)  as Q
                        group by Q.artist_name;
                        ''')

        artist_count_list = list(cursor.fetchall())
        artist_count_list.sort(key=lambda x: x[1], reverse=True)
        artist = []
        artist_count = []
        len_artist = sum([x[1] for x in artist_count_list])
        for a, c in artist_count_list:
            artist.append(a)
            artist_count.append(round( (c/len_artist * 100),2 ) )
        
        #장르 카운트
        cursor.execute(f'''
                    select Q.genre_big_name, count(Q.genre_big_name) as count
                    from   (select G.genre_big_name
                            from (select song_id
                                    from playlist_song
                                    where playlist_id = {playlist_id}) as s
                            inner join genre_big_song as g on s.song_id = g.song_id
                            inner join genre_big as G on G.genre_big_id = g.genre_big_id)  as Q
                    group by Q.genre_big_name;
        '''
        )
        genre_count_list = list(cursor.fetchall())
        genre_count_list.sort(key=lambda x: x[1], reverse=True)
        genre = []
        genre_count = []
        len_genre = sum([x[1] for x in genre_count_list])

        for g, c in genre_count_list:
            genre.append(g)
            genre_count.append(round( (c/len_genre * 100), 1 ) )

        colors = ["#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])
             for i in range(len(genre))]

        # 시대별 분포
        cursor.execute(f'''
        select S.issue_date
        from (select song_id
                from playlist_song
                where playlist_id = {playlist_id}) as s
        inner join song as S on s.song_id = S.song_id;
        ''')
        issue_date = cursor.fetchall()
        len_date = len(issue_date)
        issue_date_list = []
        for row in issue_date:
            issue_date_list.append(row[0].year)
        issue_date_year_count = list(Counter(list(map(lambda x: x - (x % 10), issue_date_list))).items())
        issue_date_year_count = list(Counter(issue_date_list).items())

        # issue_date_year_count.sort(key=lambda x: x[0])

        year = [x for x in range(1980, 2021, 1)]
        dummy_year_dict = dict(zip(year,[0]*len(year)))
        for y ,c in issue_date_year_count:
            if y in dummy_year_dict:
                dummy_year_dict[y] = c

        year_count_list = list(dummy_year_dict.values())
        total_count = sum(year_count_list)

        data = {
            'artist_label':artist,
            'artist_count':artist_count,
            'genre_label':genre,
            'genre_count':genre_count,
            'colors': colors,
            'year_label' : list(dummy_year_dict.keys()),
            'year_count' : list(map(lambda x:round((x / total_count * 100),2) ,year_count_list))
        }

        return Response(data)