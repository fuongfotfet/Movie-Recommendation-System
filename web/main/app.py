from flask import Flask, jsonify, request
from flask_cors import CORS  # Thêm thư viện Flask-CORS
from backend.others.top_ratings_genres import get_top_movies_by_genre
from backend.others.get_top_10_trending import get_top_rated
from backend.content_based.get_similar import get_recommendations_tfidf  
from datetime import datetime  # Import để lấy thời gian đánh giá
import random
import os
import pandas as pd
from backend.collaborative_filtering.collaborative_knn import recommend_with_similarity_weight
import time


# Thêm biến toàn cục lưu trữ user_id
user_id = random.randint(1000, 9999)  # Generate a random user_id on server startup
print(f"User ID mới đã được khởi tạo: {user_id}")
DATA_FILE = "main/backend/data/u_data.csv"

app = Flask(__name__)
CORS(app) 

all_ratings = []
ratings = []


# API endpoint để lấy gợi ý phim theo thể loại
@app.route('/recommend', methods=['GET'])
def recommend():
    genre = request.args.get('genre', default="Action", type=str)
    try:
        recommendations = get_top_movies_by_genre(genre)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/top_rated', methods=['GET'])
def top_rated():
    try:
        top_movies = get_top_rated()  # Gọi hàm
        return jsonify(top_movies)
    except Exception as e:
        print(f"Lỗi xảy ra: {e}")  # Log lỗi chi tiết
        return jsonify({"error": str(e)}), 400

@app.route('/rate_movie', methods=['POST'])
def rate_movie():
    global ratings, user_id
    try:
        data = request.json
        print("Dữ liệu nhận từ request:", data)

        movie_id = data.get('movie_id')
        rating = data.get('rating')
        title = data.get('title')  # Lấy tên phim từ request

        if movie_id is None or rating is None or not (0 <= rating <= 5) or not title:
            return jsonify({"error": "Invalid movie_id, title, or rating"}), 400

        # Thêm thông tin đánh giá vào danh sách
        ratings.append({
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": rating,
            "unix_timestamp": int(datetime.now().timestamp())
        })

        all_ratings.append({
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": rating,
            "title" : title,
            "date": datetime.now()
        })

        # Kiểm tra nếu đủ 5 đánh giá
        if len(ratings) >= 5:
            # Đọc dữ liệu hiện tại từ file u_data.csv
            if os.path.exists(DATA_FILE):
                existing_data = pd.read_csv(DATA_FILE, sep="\t", header=None, names=["user_id", "movie_id", "rating", "unix_timestamp"])
            else:
                # Nếu file chưa tồn tại, tạo một DataFrame rỗng
                existing_data = pd.DataFrame(columns=["user_id", "movie_id", "rating", "unix_timestamp"])
            
            # Chuyển đánh giá mới thành DataFrame
            new_data = pd.DataFrame(ratings)
            # Kết hợp dữ liệu mới và dữ liệu cũ
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)

            # Ghi dữ liệu vào file u_data.csv
            updated_data.to_csv(DATA_FILE, sep="\t", index=False, header=False)

            # Xóa danh sách đánh giá tạm thời
            ratings = []
            
            try:
                print("Bắt đầu Collaborative Filtering...")
                start_time = time.time()
                recommendations_list = recommend_with_similarity_weight(user_id=user_id, n_users=10, rec_top_n=100)
                end_time = time.time()
                print(f"Collaborative Filtering chạy thành công. Thời gian xử lý: {end_time - start_time:.2f} giây")
                return jsonify({
                    "message": "5 ratings saved to file. Collaborative Filtering recommendations generated.",
                    "collaborative_recommendations": recommendations_list
                })
            except Exception as e:
                print("Lỗi khi chạy Collaborative Filtering:", e)
                return jsonify({"error": "Failed to run Collaborative Filtering", "details": str(e)}), 500

        # Nếu rating > 3 sao, trả về gợi ý phim Content-Based Filtering
        if rating > 3:
            recommendations = get_recommendations_tfidf(movie_id, top_k=10)
            return jsonify({"message": "Rating saved", "recommendations": recommendations, "title": title})

        return jsonify({"message": "Rating saved", "current_ratings": ratings})
    except Exception as e:
        print("Lỗi từ server:", e)
        return jsonify({"error": str(e)}), 400
    
@app.route('/rating_history', methods=['GET'])
def rating_history():
    try:
        return jsonify({"ratings": all_ratings})
    except Exception as e:
        print("Lỗi từ server:", e)
        return jsonify({"error": str(e)}), 400
    
    
# Biến lưu thể loại yêu thích
favorite_genres = []
# API 1: Lưu thể loại yêu thích
@app.route('/save_favorite_genres', methods=['POST'])
def save_favorite_genres():
    global favorite_genres
    data = request.json
    favorite_genres = data.get('genres', [])
    if len(favorite_genres) != 3:
        return jsonify({"error": "Vui lòng chọn chính xác 3 thể loại."}), 400
    print(favorite_genres)
    return jsonify({"message": "Thể loại đã được lưu", "genres": favorite_genres})

# API 2: Lấy danh sách phim hot dựa trên các thể loại yêu thích
@app.route('/hot_movies_by_favorites', methods=['GET'])
def hot_movies_by_favorites():
    try:
        if not favorite_genres:
            return jsonify({"error": "Chưa lưu thể loại yêu thích nào."}), 400
        
        # Duyệt qua từng thể loại và lấy danh sách phim hot
        movies_by_genre = {}
        for genre in favorite_genres:
            movies = get_top_movies_by_genre(genre)[:10]  # Lấy top 10 phim hot cho mỗi thể loại
            movies_by_genre[genre] = movies
        
        return jsonify(movies_by_genre)
    except Exception as e:
        print(f"Lỗi: {e}")
        return jsonify({"error": str(e)}), 500
    
# API để trả về các thể loại yêu thích
@app.route('/favorite_genres', methods=['GET'])
def get_favorite_genres():
    try:
        global favorite_genres  # Lấy danh sách thể loại đã lưu
        return jsonify({"genres": favorite_genres})
    except Exception as e:
        print("Lỗi từ server:", e)
        return jsonify({"error": str(e)}), 400
    
@app.route('/recommend_content', methods=['GET'])
def recommend_content():
    """
    API endpoint trả về danh sách gợi ý phim dựa trên content-based filtering.
    Tham số truyền vào: movie_id (id của phim).
    """
    try:
        movie_id = request.args.get('movie_id')
        if not movie_id:
            return jsonify({"error": "Missing movie_id parameter"}), 400
        
        # Gọi hàm gợi ý
        recommendations = get_recommendations_tfidf(movie_id, top_k=10)
        
        # Trả về kết quả
        return jsonify({"recommendations": recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)