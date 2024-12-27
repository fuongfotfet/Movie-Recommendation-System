import pandas as pd
import numpy as np
from ast import literal_eval
from backend.get_poster import get_movie_poster
from backend.get_poster import get_backdrop_path

# Đọc và xử lý dữ liệu phim
md = pd.read_csv("main/backend/data/metadata.csv")
md['genres'] = md['genres'].fillna('[]').apply(literal_eval).apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])
md['year'] = pd.to_datetime(md['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if pd.notnull(x) else np.nan)

# Hàm tính weighted rating
def weighted_rating(x, m, C):
    v = x['vote_count']
    R = x['vote_average']
    return (v / (v + m) * R) + (m / (m + v) * C)

# Hàm trả về top 10 phim hay nhất
def get_top_rated(percentile=0.90):
    # Lọc các phim có số phiếu bầu và điểm đánh giá hợp lệ
    valid_movies = md[(md['vote_count'].notnull()) & (md['vote_average'].notnull())]
    valid_movies['vote_count'] = valid_movies['vote_count'].astype('int')
    valid_movies['vote_average'] = valid_movies['vote_average'].astype('float')

    # Tính C (điểm đánh giá trung bình toàn bộ) và m (ngưỡng số lượng đánh giá)
    C = valid_movies['vote_average'].mean()
    m = valid_movies['vote_count'].quantile(percentile)

    # Lọc các phim đủ điều kiện
    qualified = valid_movies[(valid_movies['vote_count'] >= m)]
    qualified = qualified[['id', 'title', 'year', 'vote_count', 'vote_average', 'popularity', 'overview']]
    qualified['wr'] = qualified.apply(lambda x: weighted_rating(x, m, C), axis=1)

    # Sắp xếp theo WR giảm dần và lấy top 10 phim
    top_movies = qualified.sort_values('wr', ascending=False).head(10)

    # Chuẩn hóa kết quả trả về
    recommendations = []
    for _, row in top_movies.iterrows():
        title = row['title']
        release_year = row['year']
        poster_url = get_movie_poster(title, release_year)  # Gọi hàm lấy poster
        backdrop_url = get_backdrop_path(title, release_year)  # Gọi hàm lấy backdrop

        recommendations.append({
            "id": row['id'],  # ID của phim
            "title": title,
            "year": release_year,
            "vote_count": row['vote_count'],
            "vote_average": row['vote_average'],
            "popularity": row['popularity'],
            "description": row['overview'],  # Thêm mô tả phim
            "weighted_rating": row['wr'],
            "poster_url": poster_url,  # Thêm poster URL
            "backdrop_url": backdrop_url  # Thêm backdrop URL
        })

    return recommendations