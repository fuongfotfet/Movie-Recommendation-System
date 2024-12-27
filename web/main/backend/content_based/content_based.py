import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from ast import literal_eval
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity
from sklearn.model_selection import train_test_split
from nltk.stem.snowball import SnowballStemmer
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import wordnet
from surprise import Reader, Dataset, SVD
from surprise.model_selection import cross_validate
import warnings; warnings.simplefilter('ignore')
from gensim.models import Word2Vec
import ast
import re
from datetime import datetime, timedelta
import random

# Đọc dữ liệu
md = pd.read_csv("main/backend/data/metadata.csv")
credits = pd.read_csv('main/backend/data/credits.csv')
keywords = pd.read_csv('main/backend/data/keywords.csv')

# Chuyển genres từ định dạng json về list
md['genres'] = md['genres'].fillna('[]').apply(literal_eval).apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])

non_integer_ids = md[~md['id'].apply(lambda x: str(x).isdigit())]
print(non_integer_ids['id'])
md = md[md['id'].apply(lambda x: str(x).isdigit())]
md['id'] = md['id'].astype('int')

# Trích xuất năm ra 1 cột riêng
md['year'] = pd.to_datetime(md['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if x != np.nan else np.nan)

keywords['id'] = keywords['id'].astype('int')
credits['id'] = credits['id'].astype('int')
md['id'] = md['id'].astype('int')

# Merge các bảng dữ liệu tương ứng với id
md = md.merge(credits, on='id')
md = md.merge(keywords, on='id')

# Chuyển đổi dữ liệu từ dạng JSON về dạng list, sau đó đếm số lượng caster, và số lượng crew
md['cast'] = md['cast'].apply(literal_eval)
md['crew'] = md['crew'].apply(literal_eval)
md['keywords'] = md['keywords'].apply(literal_eval)
md['cast_size'] = md['cast'].apply(lambda x: len(x))
md['crew_size'] = md['crew'].apply(lambda x: len(x))

# Lấy tên đạo diễn
def get_director(x):
    for i in x:
        if i['job'] == 'Director':
            return i['name']
    return np.nan

md['director'] = md['crew'].apply(get_director)

# Lấy 3 diễn viên cast nhân vật chính
md['cast'] = md['cast'].apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])
md['cast'] = md['cast'].apply(lambda x: x[:3] if len(x) >=3 else x)

md['keywords'] = md['keywords'].apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])

# Lower case và bỏ dấu cách trong cast
md['cast'] = md['cast'].apply(lambda x: [str.lower(i.replace(" ", "")) for i in x])

# Lower case, bỏ dấu cách và tạo 3 lần tên tác giả
md['director'] = md['director'].astype('str').apply(lambda x: str.lower(x.replace(" ", "")))
md['director'] = md['director'].apply(lambda x: [x, x, x])

# Tạo một series để tách từng keyword trong phần keywords thành những hàng riêng biệt
s = md.apply(lambda x: pd.Series(x['keywords']),axis=1).stack().reset_index(level=1, drop=True)
s.name = 'keyword'

# Đếm tần suất xuất hiện keyword
s = s.value_counts()
s[:5]

# Lọc những từ xuất hiện dưới 2 lần
s = s[s > 1]

# Sử dụng Snowball Stemmer để biến số nhiều thành số ít
stemmer = SnowballStemmer('english')
stemmer.stem('dogs')

# Lấy các từ trong keywords
def filter_keywords(x):
    words = []
    for i in x:
        if i in s:
            words.append(i)
    return words

# Loại bỏ số nhiều, bỏ dấu cách, lower case
md['keywords'] = md['keywords'].apply(filter_keywords)
md['keywords'] = md['keywords'].apply(lambda x: [stemmer.stem(i) for i in x])
md['keywords'] = md['keywords'].apply(lambda x: [str.lower(i.replace(" ", "")) for i in x])

# Đặt tên cột gộp là soup, thêm dấu cách cho mỗi phần tử
md['soup'] = md['keywords'] + md['cast'] + md['director'] + md['genres']
md['soup'] = md['soup'].apply(lambda x: ' '.join(x))


# Khởi tạo ma trận CountVectorizer
count = CountVectorizer(analyzer='word',ngram_range=(1, 2),min_df=1, stop_words='english')
count_matrix = count.fit_transform(md['soup'])

# Thay thế ma trận cosine mới
cosine_sim = cosine_similarity(count_matrix, count_matrix)

import h5py

# Lưu ma trận cosine similarity vào file HDF5
cosine_sim_file = "backend/data/cosine_similarity_matrix.h5"
with h5py.File(cosine_sim_file, 'w') as hf:
    hf.create_dataset("cosine_sim", data=cosine_sim, compression="gzip", compression_opts=9)

print(f"Cosine similarity matrix đã được lưu vào file '{cosine_sim_file}'.")
