import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

# Tải và chuẩn bị dữ liệu
user_columns = ['user_id', 'age', 'sex', 'occupation', 'zip_code']
users_df = pd.read_csv(r'../data/u_user.csv', sep='|', names=user_columns)

movie_columns = ['movie_id', 'title', 'release_date', 'video_release_date', 'imdb_url']
movies_df = pd.read_csv(
    r'../data/u_item.csv',
    sep='|', 
    names=movie_columns + [f'genre_{i}' for i in range(19)],
    encoding='latin-1'
)[["movie_id", "title"]]

ratings_columns = ['user_id', 'movie_id', 'rating', 'unix_timestamp']
ratings_df = pd.read_csv(r'../data/u_data.csv', sep='\t', names=ratings_columns)
ratings_df.drop("unix_timestamp", inplace=True, axis=1)

# Kết hợp dữ liệu ratings và movie
rating_movies_df = ratings_df.merge(movies_df, on="movie_id", how="inner")

# Lọc ra các phim có đủ rating
movie_rating_count = rating_movies_df.groupby("title")["rating"].count().reset_index().rename(columns={"rating": "total_rating_count"})
rating_movies_df = rating_movies_df.merge(movie_rating_count, on="title")
rating_popular_movies_df = rating_movies_df[rating_movies_df.total_rating_count >= 100]

# Tạo ma trận user-movie
user_features_df = rating_popular_movies_df.pivot_table(index="user_id", columns="title", values="rating").fillna(0.0)
user_features_matrix = csr_matrix(user_features_df)

# Khởi tạo mô hình KNN
model_knn = NearestNeighbors(metric="cosine", algorithm="brute", n_neighbors=10, n_jobs=-1)
model_knn.fit(user_features_matrix)

def recommend_with_similarity_weight(user_id=10, n_users=10, rec_top_n=20, min_rating=3.5):
    """
    Gợi ý phim dựa trên trọng số độ tương đồng giữa người dùng và trả về kết quả định dạng bảng.
    """
    # Tìm n người dùng tương đồng nhất với user_id
    distances, indices = model_knn.kneighbors(
        user_features_df.loc[user_features_df.index == user_id].values.reshape(1, -1),
        n_neighbors=n_users + 1
    )

    # Lấy danh sách user_id và độ tương đồng tương ứng (bỏ người dùng hiện tại)
    user_ids = [user_features_df.index[indices.flatten()[i]] for i in range(1, n_users + 1)]
    similarities = 1 - distances.flatten()[1:]

    # Lấy các đánh giá của người dùng tương đồng
    sel_ratings = rating_popular_movies_df.loc[
        rating_popular_movies_df.user_id.isin(user_ids) & (rating_popular_movies_df.rating > min_rating)
    ]

    # Loại bỏ các phim đã xem bởi user hiện tại
    movies_rated_by_targeted_user = rating_popular_movies_df.loc[
        rating_popular_movies_df.user_id == user_id, "movie_id"
    ].values
    sel_ratings = sel_ratings.loc[~sel_ratings.movie_id.isin(movies_rated_by_targeted_user)]

    # Tính avg score có trọng số
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

    # Chuẩn hóa viewer score và tính final score
    movie_priority = sel_ratings.groupby("movie_id").agg(
        viewers=("user_id", "nunique")
    ).reset_index()
    movie_priority["viewer_score"] = movie_priority["viewers"] / max(movie_priority["viewers"]) * 5
    movie_priority["avg_score"] = movie_priority["movie_id"].map(movie_scores)
    movie_priority["final_score"] = movie_priority["viewer_score"] * 0.51 + movie_priority["avg_score"] * 0.49

    # Lấy top n phim gợi ý
    top_movies = movie_priority.sort_values(by="final_score", ascending=False).head(rec_top_n)

    # Kết hợp với thông tin movie_title và release_year
    top_movies = top_movies.merge(movies_df, left_on="movie_id", right_on="movie_id")
    top_movies[["movie_title", "release_year"]] = top_movies["title"].str.extract(r'(.+)\s\((\d+)\)')

    # Định dạng kết quả cuối cùng
    result_df = top_movies[["movie_id", "movie_title", "release_year", "final_score"]]
    return result_df

# Gọi hàm và in kết quả
recommended_movies = recommend_with_similarity_weight(user_id=10, n_users=6, rec_top_n=10)
print(recommended_movies)
