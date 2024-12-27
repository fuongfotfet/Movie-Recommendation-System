import h5py
import pandas as pd
import numpy as np
from backend.get_poster import get_movie_poster
md = pd.read_csv("main/backend/data/metadata.csv")
md['year'] = pd.to_datetime(md['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if pd.notnull(x) else np.nan)

cosine_sim_file = "main/backend/data/cosine_similarity_matrix.h5"
# Tải lại ma trận cosine similarity từ file HDF5
with h5py.File(cosine_sim_file, 'r') as hf:
    cosine_sim = hf["cosine_sim"][:]

print("Cosine similarity matrix đã được tải lại thành công.")

def get_recommendations_tfidf(movie_id, top_k=10):
    """
    Get top K movie recommendations with detailed fields: id, title, year, vote_count, 
    vote_average, popularity, description, and poster_url.

    Parameters:
        movie_id (int/str): The ID of the movie to find recommendations for.
        top_k (int): Number of top recommendations to return.

    Returns:
        List[dict]: List of dictionaries with detailed movie information.
    """
    movie_id = str(movie_id)

    # Check if movie_id exists
    if movie_id not in md['id'].astype(str).values:
        print(f"Warning: Movie ID {movie_id} not found in metadata.")
        return []

    # Get index of the movie
    idx = md[md['id'].astype(str) == movie_id].index[0]

    # Calculate similarity scores
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Extract top K indices excluding itself
    movie_indices = [i[0] for i in sim_scores[1:top_k + 1]]
    top_movies = md.iloc[movie_indices]

    # Prepare the list of recommendations
    recommendations = []
    for _, row in top_movies.iterrows():
        poster_url = get_movie_poster(row['title'], row['year'])  # Lấy URL của poster
        
        recommendations.append({
            "id": row['id'],
            "title": row['title'],
            "year": row['year'],
            "vote_count": row['vote_count'],
            "vote_average": row['vote_average'],
            "popularity": row['popularity'],
            "description": row['overview'],  # Thêm description
            "poster_url": poster_url  # Thêm poster URL
        })

    return recommendations
