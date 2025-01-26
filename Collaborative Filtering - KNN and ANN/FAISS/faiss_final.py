import numpy as np
import pandas as pd
import re
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity
from sklearn.neighbors import NearestNeighbors
from tqdm import tqdm
import faiss

user_columns = ['user_id', 'age', 'sex', 'occupation', 'zip_code']
users_df = pd.read_csv(r'../data/u_user.csv', sep='|', names=user_columns)

# genre_df = pd.read_csv("u_genre.csv", sep='|', encoding='latin-1')
# genre_columns = ["unknown"] + list(genre_df[genre_df.columns[0]].values)

movie_columns = ['movie_id', 'title', 'release_date', 'video_release_date', 'imdb_url']
movies_df = pd.read_csv(
    r'../data/u_item.csv',
    sep='|', 
    names=movie_columns + [f'genre_{i}' for i in range(19)],
    encoding='latin-1'
)[["movie_id", "title"]]

ratings_columns = ['user_id', 'movie_id', 'rating', 'unix_timestamp']
ratings_df = pd.read_csv(r'../data/u_data.csv', sep='\t', names=ratings_columns)

rating_movies_df = ratings_df.merge(movies_df, how="outer")

movie_rating = rating_movies_df.dropna(axis = 0, subset = ["title"])
movie_rating_count = movie_rating.groupby(["title"])["rating"].count().reset_index().rename(columns = {'rating': 'total_rating_count'})

rating_movies_df = rating_movies_df.merge(movie_rating_count, on="title", how="right")

ratings_threshold = 100
rating_popular_movies_df = rating_movies_df.loc[rating_movies_df.total_rating_count >= ratings_threshold]

user_features_df = rating_popular_movies_df.pivot_table(index="user_id", columns="title", values="rating").fillna(0.0)
user_features_matrix = csr_matrix(user_features_df)

# Bước 1: Lọc các phim phổ biến dựa vào ngưỡng đánh giá
ratings_threshold = 100
rating_popular_movies_df = rating_movies_df.loc[rating_movies_df.total_rating_count >= ratings_threshold]

# Bước 2: Tạo bảng User-Item Matrix với movie_id làm cột
user_features_df = rating_popular_movies_df.pivot_table(
    index="user_id",
    columns="movie_id",
    values="rating"
).fillna(0.0)  # Điền giá trị 0 cho các ô trống

# Bước 3: Chuyển ma trận thành CSR Matrix (nếu cần)
user_features_matrix = csr_matrix(user_features_df.values)

# Chuyển đổi user_features_df thành numpy array
prediction_matrix = user_features_df.copy()  # Giữ lại ma trận gốc
prediction_array = prediction_matrix.values.astype('float32')  # Chuyển thành numpy array dạng float32

def recommend_with_faiss(user_id, prediction_array, prediction_matrix, ratings_df, movies_df, k=10, rec_top_n=10, min_rating=3.5):
    # Tạo FAISS Index và tìm k người dùng tương tự
    user_vector = prediction_array[prediction_matrix.index.get_loc(user_id)].reshape(1, -1)
    dimension = prediction_array.shape[1]
    faiss_index = faiss.IndexFlatL2(dimension)
    faiss_index.add(prediction_array)
    distances, indices = faiss_index.search(user_vector, k + 1)
    
    # Loại user hiện tại và lấy danh sách user_id tương tự
    similar_user_ids = [prediction_matrix.index[i] for i in indices.flatten()[1:]]
    similarities = 1 / (1 + distances.flatten()[1:])

    # Lấy đánh giá từ những người dùng tương tự
    sel_ratings = ratings_df.loc[
        ratings_df.user_id.isin(similar_user_ids) & (ratings_df.rating >= min_rating)
    ]

    # Loại bỏ phim đã xem bởi user hiện tại
    seen_movies = ratings_df.loc[ratings_df.user_id == user_id, "movie_id"].unique()
    sel_ratings = sel_ratings.loc[~sel_ratings.movie_id.isin(seen_movies)]

    # Tính điểm trung bình có trọng số
    movie_scores = {}
    for movie_id in sel_ratings["movie_id"].unique():
        group = sel_ratings[sel_ratings.movie_id == movie_id]
        numerator = sum(similarities[similar_user_ids.index(row.user_id)] * row.rating for _, row in group.iterrows())
        denominator = sum(similarities[similar_user_ids.index(row.user_id)] for _, row in group.iterrows())
        movie_scores[movie_id] = numerator / denominator if denominator != 0 else 0

    # Chuyển kết quả thành DataFrame và kết hợp với movies_df
    top_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)[:rec_top_n]
    result_df = pd.DataFrame(top_movies, columns=["movie_id", "final_score"])
    result_df = result_df.merge(movies_df, on="movie_id", how="left")

    # Tách movie_title và release_year
    result_df["movie_title"] = result_df["title"].str.extract(r'(.+)\s\(\d{4}\)')
    result_df["release_year"] = result_df["title"].str.extract(r'\((\d{4})\)')
    result_df = result_df[["movie_id", "movie_title", "release_year", "final_score"]]

    return result_df

# Gọi hàm ví dụ
user_id_to_test = 1
recommended_movies = recommend_with_faiss(
    user_id=user_id_to_test,
    prediction_array=prediction_array,
    prediction_matrix=prediction_matrix,
    ratings_df=rating_popular_movies_df,
    movies_df=movies_df,
    k=5,
    rec_top_n=10,
    min_rating=3.5
)

print(f"Phim gợi ý cho User ID {user_id_to_test}:")
print(recommended_movies)

