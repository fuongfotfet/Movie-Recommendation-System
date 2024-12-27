import requests

# Hàm để lấy link poster từ TMDb
def get_movie_poster(title, release_year):
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key=0063b4dd59f13737d069ca8de05105f6&query={title}&year={release_year}"
    response = requests.get(search_url).json()

    if response.get('results'):
        poster_path = response['results'][0].get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return None

def get_backdrop_path(title, release_year):
    try:
        # Gọi API tìm kiếm phim
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key=0063b4dd59f13737d069ca8de05105f6&query={title}&year={release_year}"
        response = requests.get(search_url)
        data = response.json()

        # Nếu tìm thấy phim
        if data['results']:
            # Lấy `backdrop_path` từ kết quả đầu tiên
            backdrop_path = data['results'][0].get('backdrop_path', None)
            if backdrop_path:
                return f"https://image.tmdb.org/t/p/w1280{backdrop_path}"
        return None  # Không tìm thấy backdrop
    except Exception as e:
        print(f"Lỗi khi lấy backdrop_path cho phim {title}: {e}")
        return None