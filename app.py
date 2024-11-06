from flask import Flask, jsonify, request
from flask_cors import CORS  # Thêm thư viện Flask-CORS
import pandas as pd
import numpy as np
from ast import literal_eval
import requests

app = Flask(__name__)
CORS(app) 

# TMDb API key
api_key = '0063b4dd59f13737d069ca8de05105f6'

# Đọc và xử lý dữ liệu phim
md = pd.read_csv("movies_metadata.csv")
md['genres'] = md['genres'].fillna('[]').apply(literal_eval).apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])
md['year'] = pd.to_datetime(md['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if pd.notnull(x) else np.nan)

# Chuyển đổi dữ liệu thể loại thành các hàng riêng biệt
s = md.apply(lambda x: pd.Series(x['genres']), axis=1).stack().reset_index(level=1, drop=True)
s.name = 'genre'
gen_md = md.drop('genres', axis=1).join(s)

# Hàm để tính điểm weighted rating
def weighted_rating(x, m, C):
    v = x['vote_count']
    R = x['vote_average']
    return (v / (v + m) * R) + (m / (m + v) * C)

# Hàm để lấy link poster từ TMDb
def get_movie_poster(api_key, title, release_year):
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}&year={release_year}"
    response = requests.get(search_url).json()

    if response.get('results'):
        poster_path = response['results'][0].get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return None

# Hàm gợi ý top phim dựa trên thể loại
def get_top_movies_by_genre(genre, percentile=0.85):
    df = gen_md[gen_md['genre'] == genre]
    vote_counts = df[df['vote_count'].notnull()]['vote_count'].astype('int')
    vote_averages = df[df['vote_average'].notnull()]['vote_average'].astype('int')
    C = vote_averages.mean()
    m = vote_counts.quantile(percentile)
    
    qualified = df[(df['vote_count'] >= m) & (df['vote_count'].notnull()) & (df['vote_average'].notnull())]
    qualified = qualified[['title', 'year', 'vote_count', 'vote_average', 'popularity']]
    qualified['vote_count'] = qualified['vote_count'].astype('int')
    qualified['vote_average'] = qualified['vote_average'].astype('int')
    qualified['wr'] = qualified.apply(lambda x: weighted_rating(x, m, C), axis=1)
    
    recommendations = []
    for _, row in qualified.sort_values('wr', ascending=False).head(15).iterrows():
        title = row['title']
        release_year = row['year']
        poster_url = get_movie_poster(api_key, title, release_year)  # Lấy URL của poster
        recommendations.append({
            "title": title,
            "year": release_year,
            "vote_count": row['vote_count'],
            "vote_average": row['vote_average'],
            "popularity": row['popularity'],
            "weighted_rating": row['wr'],
            "poster_url": poster_url  # Thêm poster URL vào kết quả trả về
        })

    return recommendations

# API endpoint để lấy gợi ý phim theo thể loại
@app.route('/recommend', methods=['GET'])
def recommend():
    genre = request.args.get('genre', default="Action", type=str)
    try:
        recommendations = get_top_movies_by_genre(genre)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)