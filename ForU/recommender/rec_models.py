import numpy as np
import pandas as pd
from itertools import chain, combinations
from scipy.sparse import csr_matrix
from collections import Counter, defaultdict
from gensim.models import Word2Vec
import json
from random import sample
import random
import scipy.sparse as spr
import pickle
import sent2vec
from nltk.corpus import stopwords
from konlpy.tag import Mecab

class Recommender:
    
    def __init__(self):
        self.song_meta = pd.read_pickle('./recommender/data/song_meta_pop.pickle')   # manage.py 가 있는 위치 기준인가봄.
        self.train = pd.read_pickle('./recommender/data/new_train.pickle')
        
        #for singer_recommend
        self.artist_w2v_model = Word2Vec.load('./recommender/data/artist_w2v.model')
        self.artist_song_dict = dict(json.loads(open('./recommender/data/artist_song_dict.json', 'r').read()))
        self.artist_list = pd.read_csv('./recommender/data/artist_list.csv')

        #load als model
        self.als_model = pickle.load(open('./recommender/data/als_model_200_0.1_10.pickle', 'rb'))
        self.als_unchae = pickle.load(open('./recommender/data/ply2ply_als_model.pickle','rb'))
        #for tag recommend
        self.p_tags = pickle.load(open('./recommender/data/tag/p_tags.pickle', 'rb'))
        self.p_title = pickle.load(open('./recommender/data/tag/p_title.pickle', 'rb'))
        self.p_new_tags = pickle.load(open('./recommender/data/tag/p_new_tags.pickle', 'rb'))

        self.stopword = pickle.load(open('./recommender/data/tag/10_28_stopword.pickle', 'rb'))
        self.s2v_model = sent2vec.Sent2vecModel()
        self.s2v_model.load_model('./recommender/data/tag/s2v_model.bin')
        self.m = Mecab('/home/ubuntu/workspace/mecab-ko-dic-2.1.1-20180720')

        with open('./recommender/data/tag/svd_knn_model.pickle', 'rb') as f:
            self.tag_knn_model = pickle.load(f)

        with open('./recommender/data/tag/svd_tag_vectors.pickle', 'rb') as f:
            self.tag_vectors = pickle.load(f)
        

    def singer_recommend(self, user, rec_songs_cnt = 30, rate_of_familiar_songs = 0.3, artist_sample = 5):
        song_cnt_from_fam = int(rec_songs_cnt * rate_of_familiar_songs)
        song_cnt_from_rec = int(rec_songs_cnt * (1-rate_of_familiar_songs))
        
        artist_songs = []
        new_artist_songs = []
        final_recommendation = []
        user_recommend_artists = []
    
        #유저 아티스트 랜덤 샘플 가져오기
        if len(list(*user['artists'].values)) > artist_sample:
            user_random_artist_list = random.sample(*user['artists'].values, artist_sample)
        else:
            user_random_artist_list = list(*user['artists'].values)
        
        #유사 가수 찾기 (전체로 찾기)
        temp = self.artist_w2v_model.wv.most_similar(user_random_artist_list, topn = 6)
        user_recommend_artists.extend([x for x , _ in temp])

        # 기존 가수 노래 가져오기
        for artist_ in user_random_artist_list:
            temp_songs = self.song_meta.iloc[self.artist_song_dict[artist_]].sort_values(by= 'popularity', ascending = False)[:10]
            artist_songs.extend(temp_songs['id'])
        # 새 가수 노래 가져오기    
        for artist_ in user_recommend_artists:
            temp_songs = self.song_meta.iloc[self.artist_song_dict[artist_]].sort_values(by= 'popularity', ascending = False)[:10]
            new_artist_songs.extend(temp_songs['id'])
        # 이미 있는 노래는 제거
        artist_songs =  set(artist_songs) - set(*user['songs'])
        
        #노래 샘플로 뽑기
        if len(artist_songs) >= song_cnt_from_fam:
            final_recommendation.extend(sample(artist_songs,  song_cnt_from_fam   ))
        else:
            final_recommendation.extend(artist_songs)

        if len(new_artist_songs) >= song_cnt_from_rec:
            final_recommendation.extend(sample(new_artist_songs,  song_cnt_from_rec    ))
        else:
            final_recommendation.extend(new_artist_songs)


        # 가수 키 가져오기
        user_recommend_artists_id = self.artist_list[self.artist_list['artist_name'].isin(user_recommend_artists)].index.tolist()
            
        return user_recommend_artists_id ,final_recommendation


    def get_playlist_with_tag(self ,text, k_n = 2):
        emb = self.s2v_model.embed_sentence(text)

        title_labels, _ = self.p_title.knn_query(emb, k = k_n, num_threads=8)
        tag_labels, _ = self.p_tags.knn_query(emb, k = k_n, num_threads=8)
        new_tag_labels, _ = self.p_new_tags.knn_query(emb, k = k_n, num_threads=8)

        playlists_id = list(chain.from_iterable(zip(title_labels.reshape(-1),tag_labels.reshape(-1),new_tag_labels.reshape(-1))))
        
        return playlists_id

    def konlpy_preprocessing(self, text, removes_stopwords = True):
        # Twitter를 활용해서 
        # stem = True > 어간 추출   \
        # norm = True > 정규화 진행
         #     morph = twitter.morphs(text, norm = True)
            
        parts_of_speech = []
        # mecab으로 원하는 품사만 뽑아오기
        for word, tag in self.m.pos(text):
            if tag in ['NNP', 'NNG', 'VA', 'VV', 'SL', 'SN', 'XR', 'VA+ETM', 'VV+EC+VX+ETM']:
                parts_of_speech.append(word.lower())
        
        #  stopwords에 있는 단어 제거
        if removes_stopwords == True:
            parts_of_speech = [token for token in parts_of_speech if not token in self.stopword]    

            stops = set(stopwords.words('english')) # 영어 불용어 불러오기

            parts_of_speech = [w for w in parts_of_speech if not w in stops] 
        
        return " ".join(parts_of_speech)

    def tag_recommend_with_genred(self,tag_list):
        vectors = np.zeros((100,1))

        for id in tag_list:
            vectors = vectors+self.tag_vectors[id]

        vectors = vectors/len(tag_list)

        labels,distances = self.tag_knn_model.knn_query(vectors, k = 10+len(tag_list))

        return list(set(labels[0])-set(tag_list))
        

    