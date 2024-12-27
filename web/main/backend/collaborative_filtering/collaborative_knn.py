import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
import requests

# Tải và chuẩn bị dữ liệu
user_columns = ['user_id', 'age', 'sex', 'occupation', 'zip_code']
movie_columns = ['movie_id', 'title', 'release_date', 'video_release_date', 'imdb_url']
movies_df = pd.read_csv(
    r'main/backend/data/u_item.csv', 
    sep='|', 
    names=movie_columns + [f'genre_{i}' for i in range(19)],
    encoding='latin-1'
)[["movie_id", "title"]]

ratings_columns = ['user_id', 'movie_id', 'rating', 'unix_timestamp']
ratings_df = pd.read_csv(r'main/backend/data/u_data.csv', sep='\t', names=ratings_columns)
ratings_df.drop("unix_timestamp", inplace=True, axis=1)

# Kết hợp dữ liệu ratings và movie
rating_movies_df = ratings_df.merge(movies_df, on="movie_id", how="inner")

# Lọc ra các phim có đủ rating
movie_rating_count = rating_movies_df.groupby("title")["rating"].count().reset_index().rename(columns={"rating": "total_rating_count"})
rating_movies_df = rating_movies_df.merge(movie_rating_count, on="title")
rating_popular_movies_df = rating_movies_df[rating_movies_df.total_rating_count >= 10]

# Tạo ma trận user-movie
user_features_df = rating_popular_movies_df.pivot_table(index="user_id", columns="title", values="rating").fillna(0.0)
user_features_matrix = csr_matrix(user_features_df)

# Khởi tạo mô hình KNN
model_knn = NearestNeighbors(metric="cosine", algorithm="brute", n_neighbors=10, n_jobs=-1)
model_knn.fit(user_features_matrix)

# Hàm để lấy link poster từ TMDb
def get_movie_poster(title, release_year):
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key=0063b4dd59f13737d069ca8de05105f6&query={title}&year={release_year}"
    response = requests.get(search_url).json()

    if response.get('results'):
        poster_path = response['results'][0].get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return None

# Tải metadata.csv
metadata = pd.read_csv("main/backend/data/metadata.csv")
metadata['year'] = pd.to_datetime(metadata['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if pd.notnull(x) else np.nan)

def recommend_with_similarity_weight(user_id=10, n_users=10, rec_top_n=20, min_rating=3.5):
    """
    Recommend movies based on collaborative filtering and return detailed information from metadata.
    This function ensures updated data and re-trains the model every call.
    """
    # Bước 1: Đọc lại dữ liệu mới từ file u_data.csv
    ratings_df = pd.read_csv("main/backend/data/u_data.csv", sep="\t", header=None,
                             names=["user_id", "movie_id", "rating", "unix_timestamp"])
    ratings_df.drop("unix_timestamp", axis=1, inplace=True)  # Bỏ cột thời gian

    # Kết hợp dữ liệu với movies_df
    rating_movies_df = ratings_df.merge(movies_df, on="movie_id", how="inner")

    # Lọc các phim có đủ ratings
    movie_rating_count = rating_movies_df.groupby("title")["rating"].count().reset_index()
    movie_rating_count = movie_rating_count.rename(columns={"rating": "total_rating_count"})
    rating_movies_df = rating_movies_df.merge(movie_rating_count, on="title")
    rating_popular_movies_df = rating_movies_df[rating_movies_df.total_rating_count >= 10]

    # Bước 2: Tạo ma trận user-movie
    user_features_df = rating_popular_movies_df.pivot_table(
        index="user_id", columns="title", values="rating"
    ).fillna(0.0)
    user_features_matrix = csr_matrix(user_features_df)

    # Bước 3: Huấn luyện lại mô hình KNN
    model_knn = NearestNeighbors(metric="cosine", algorithm="brute", n_neighbors=10, n_jobs=-1)
    model_knn.fit(user_features_matrix)

    # Bước 4: Tìm n người dùng tương đồng nhất
    if user_id not in user_features_df.index:
        return []  # Trả về rỗng nếu user_id không tồn tại

    distances, indices = model_knn.kneighbors(
        user_features_df.loc[[user_id]].values.reshape(1, -1),
        n_neighbors=n_users + 1
    )

    # Lấy danh sách user_ids tương tự
    user_ids = [user_features_df.index[indices.flatten()[i]] for i in range(1, n_users + 1)]
    similarities = 1 - distances.flatten()[1:]

    # Lấy các đánh giá từ người dùng tương tự
    sel_ratings = rating_popular_movies_df.loc[
        rating_popular_movies_df.user_id.isin(user_ids) & 
        (rating_popular_movies_df.rating > min_rating)
    ]

    # Loại bỏ các phim đã được người dùng hiện tại đánh giá
    movies_rated_by_user = rating_popular_movies_df.loc[
        rating_popular_movies_df.user_id == user_id, "movie_id"
    ].values
    sel_ratings = sel_ratings.loc[~sel_ratings.movie_id.isin(movies_rated_by_user)]

    # Tính điểm trung bình có trọng số theo độ tương đồng
    movie_scores = {}
    for movie_id in sel_ratings["movie_id"].unique():
        ratings_for_movie = sel_ratings[sel_ratings.movie_id == movie_id]
        numerator, denominator = 0, 0
        for _, row in ratings_for_movie.iterrows():
            user_index = user_ids.index(row["user_id"])
            sim = similarities[user_index]
            numerator += sim * row["rating"]
            denominator += sim
        movie_scores[int(movie_id)] = numerator / denominator if denominator != 0 else 0

    # Tính điểm ưu tiên dựa trên số người xem
    movie_priority = sel_ratings.groupby("movie_id").agg(
        viewers=("user_id", "nunique")
    ).reset_index()
    movie_priority["viewer_score"] = movie_priority["viewers"] / max(movie_priority["viewers"]) * 5
    movie_priority["avg_score"] = movie_priority["movie_id"].map(movie_scores)
    movie_priority["final_score"] = movie_priority["viewer_score"] * 0.51 + movie_priority["avg_score"] * 0.49

    # Lấy top n phim gợi ý
    top_movies = movie_priority.sort_values(by="final_score", ascending=False).head(rec_top_n)

    # Kết nối với metadata để lấy thông tin chi tiết
    recommendations = []
    for _, row in top_movies.iterrows():
        movie_id = row["movie_id"]
        metadata_row = metadata[metadata["id"] == movie_id]

        if not metadata_row.empty:
            metadata_row = metadata_row.iloc[0]
            poster_url = get_movie_poster(metadata_row["title"], metadata_row["year"])

            recommendations.append({
                "id": int(metadata_row["id"]),
                "title": metadata_row["title"],
                "year": str(metadata_row["year"]) if pd.notnull(metadata_row["year"]) else None,
                "vote_count": int(metadata_row["vote_count"]) if pd.notnull(metadata_row["vote_count"]) else 0,
                "vote_average": float(metadata_row["vote_average"]) if pd.notnull(metadata_row["vote_average"]) else 0.0,
                "popularity": float(metadata_row["popularity"]) if pd.notnull(metadata_row["popularity"]) else 0.0,
                "description": metadata_row["overview"],
                "poster_url": poster_url
            })

    return recommendations