// Biến lưu danh sách phim từ API
let topRatedMovies = [];
let currentMovieIndex = 0;

async function openHistoryModal() {
    const historyModal = document.getElementById('historyModal');
    const historyList = document.getElementById('historyList');

    try {
        const response = await fetch('http://127.0.0.1:5000/rating_history');
        if (!response.ok) throw new Error('Không thể lấy dữ liệu lịch sử');

        const data = await response.json();
        historyList.innerHTML = ''; // Xóa nội dung cũ

        if (data.ratings.length === 0) {
            historyList.innerHTML = '<li>Bạn chưa đánh giá phim nào.</li>';
        } else {
            // Hiển thị danh sách lịch sử đánh giá
            data.ratings.forEach((item, index) => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    ${index + 1}. <strong>${item.title}</strong> - ${item.rating} ⭐ 
                    <br>(Đánh giá lúc: ${item.date})
                `;
                historyList.appendChild(listItem);
            });
        }

        historyModal.style.display = 'flex'; // Hiển thị modal
    } catch (error) {
        console.error("Lỗi khi lấy lịch sử đánh giá:", error);
        historyList.innerHTML = '<li>Không thể tải lịch sử đánh giá. Vui lòng thử lại sau.</li>';
    }
}

function setupRatingSystem(movie) {
    console.log("Đang thiết lập hệ thống đánh giá sao cho phim:", movie);

    const stars = document.querySelectorAll('.star');
    const ratingMessage = document.getElementById('ratingMessage');

    // Xóa sự kiện cũ trước khi thêm mới
    stars.forEach(star => {
        star.replaceWith(star.cloneNode(true));
    });

    const updatedStars = document.querySelectorAll('.star');
    updatedStars.forEach((star, index) => {
        // Log vị trí sao hiện tại
        console.log(`Đang thiết lập sự kiện cho sao thứ ${index + 1}`);

        star.addEventListener('mouseover', () => {
            console.log(`Hover vào sao thứ ${index + 1}`);
            updatedStars.forEach((s, i) => {
                if (i <= index) s.classList.add('hover');
                else s.classList.remove('hover');
            });
        });

        star.addEventListener('mouseout', () => {
            console.log("Hover ra khỏi sao");
            updatedStars.forEach(s => s.classList.remove('hover'));
        });

        star.addEventListener('click', async () => {
            const rating = index + 1;
            console.log(`Người dùng chọn đánh giá: ${rating} sao cho phim: ${movie.title}`);

            updatedStars.forEach((s, i) => {
                if (i <= index) s.classList.add('selected');
                else s.classList.remove('selected');
            });

            ratingMessage.style.display = 'none';

            try {
                console.log("Gửi request đánh giá phim đến backend...");
                const response = await fetch('http://127.0.0.1:5000/rate_movie', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        movie_id: movie.id,
                        rating: rating,
                        title: movie.title
                    }),
                    timeout: 10000 // Tăng timeout lên 10 giây
                });

                const data = await response.json();
                console.log("Dữ liệu phản hồi từ backend:", data);

                if (response.ok) {
                    ratingMessage.innerText = `Bạn đã đánh giá thành công ${rating} sao.`;
                    ratingMessage.style.color = '#4caf50';
                    ratingMessage.style.display = 'block';

                    // Log thông tin Collaborative Filtering
                    if (data.collaborative_recommendations) {
                        console.log("Kết quả Collaborative Filtering:", data.collaborative_recommendations);
                        showCollaborativeRecommendations(data.collaborative_recommendations);
                    }

                    // Log thông tin Content-Based Filtering
                    if (rating > 3 && data.recommendations) {
                        console.log("Kết quả Content-Based Filtering:", data.recommendations);
                        showRecommendedSection(data.title, data.recommendations);
                    }
                } else {
                    console.error("Lỗi từ server:", data.error);
                    ratingMessage.innerText = `Lỗi: ${data.error}`;
                    ratingMessage.style.color = '#f44336';
                    ratingMessage.style.display = 'block';
                }
            } catch (error) {
                console.error("Lỗi khi gửi request hoặc kết nối đến backend:", error);
                ratingMessage.innerText = 'Lỗi kết nối. Vui lòng thử lại!';
                ratingMessage.style.color = '#f44336';
                ratingMessage.style.display = 'block';
            }
        });
    });
}

function showCollaborativeRecommendations(recommendations) {
    const collaborativeSection = document.getElementById('collaborative-section');
    const collaborativeRow = document.getElementById('collaborative-movies');

    collaborativeRow.innerHTML = ''; // Xóa nội dung cũ

    recommendations.forEach(movie => {
        const movieCard = document.createElement('div');
        movieCard.classList.add('movie-card');

        const img = document.createElement('img');
        img.src = movie.poster_url || 'default_image.jpg';
        img.alt = movie.movie_title;

        movieCard.appendChild(img);
        collaborativeRow.appendChild(movieCard);

        movieCard.addEventListener('click', () => openModal(movie));
    });

    collaborativeSection.style.display = 'block'; // Hiển thị section
}

// Hàm để hiển thị mục "Vì bạn đã xem + tên phim"
function showRecommendedSection(likedMovieTitle, recommendations) {
    const recommendedSection = document.getElementById('recommended-section');
    const likedMovieTitleSpan = document.getElementById('liked-movie-title');
    const recommendedMoviesRow = document.getElementById('recommended-movies');

    // Hiển thị tiêu đề "Vì bạn đã xem + tên phim"
    likedMovieTitleSpan.innerText = likedMovieTitle;

    // Xóa nội dung cũ trong hàng phim
    recommendedMoviesRow.innerHTML = '';

    // Thêm phim gợi ý vào hàng
    recommendations.forEach(movie => {
        const movieCard = document.createElement('div');
        movieCard.classList.add('movie-card');

        const img = document.createElement('img');
        img.src = movie.poster_url || 'default_image.jpg';
        img.alt = movie.title;

        movieCard.appendChild(img);
        recommendedMoviesRow.appendChild(movieCard);

        // Sự kiện mở modal khi click vào phim
        movieCard.addEventListener('click', () => openModal(movie));
    });

    // Hiển thị section
    recommendedSection.style.display = 'block';
}

function openModal(movie) {
    const modal = document.getElementById('movieModal');
    modal.style.display = 'flex'; // Hiển thị modal

    // Gắn thông tin chi tiết phim
    document.getElementById('movieTitle').innerText = movie.title;
    document.getElementById('movieYear').innerText = `Năm phát hành: ${movie.year}`;
    document.getElementById('movieRating').innerText = `Điểm trung bình: ${movie.vote_average}`;
    document.getElementById('moviePoster').src = movie.poster_url || 'default_image.jpg';
    document.getElementById('movieDescription').innerText =
        movie.description || 'Không có mô tả cho phim này.';

    // Reset tất cả các sao về trạng thái mặc định
    const stars = document.querySelectorAll('.star');
    stars.forEach(star => star.classList.remove('selected'));

    // Reset thông báo đánh giá
    const ratingMessage = document.getElementById('ratingMessage');
    ratingMessage.style.display = 'none';
    ratingMessage.innerText = '';

    // Thiết lập hệ thống đánh giá mới
    setupRatingSystem(movie);
}

// Lấy danh sách phim top-rated cho hero
async function getTopRatedMoviesForHero() {
    try {
        const response = await fetch('http://127.0.0.1:5000/top_rated');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        topRatedMovies = await response.json();

        if (topRatedMovies.length > 0) {
            displayHeroMovie(topRatedMovies[currentMovieIndex]);
            startHeroRotation();
        }
    } catch (error) {
        console.error("Error fetching top-rated movies:", error);
    }
}

function displayHeroMovie(movie) {
    const heroPoster = document.getElementById('heroPoster');
    const btnPrimary = document.querySelector('.btn-primary');
    const btnSecondary = document.querySelector('.btn-secondary');

    heroPoster.classList.add('fade-out');

    setTimeout(() => {
        heroPoster.src = movie.backdrop_url || 'logo_web.png';
        heroPoster.alt = movie.title;

        heroPoster.classList.remove('fade-out');
        heroPoster.classList.add('fade-in');
        setTimeout(() => heroPoster.classList.remove('fade-in'), 500);
    }, 500);

    // Xóa bỏ sự kiện click cũ trước khi thêm mới
    btnPrimary.replaceWith(btnPrimary.cloneNode(true));
    btnSecondary.replaceWith(btnSecondary.cloneNode(true));

    document.querySelector('.btn-primary').addEventListener('click', () => openModal(movie));
    document.querySelector('.btn-secondary').addEventListener('click', () => openModal(movie));
}

// Thay đổi poster mỗi 5 giây
function startHeroRotation() {
    setInterval(() => {
        currentMovieIndex = (currentMovieIndex + 1) % topRatedMovies.length;
        displayHeroMovie(topRatedMovies[currentMovieIndex]);
    }, 5000);
}


// Hàm mở modal lịch sử đánh giá
async function openHistoryModal() {
    const historyModal = document.getElementById('historyModal');
    const historyList = document.getElementById('historyList');

    try {
        const response = await fetch('http://127.0.0.1:5000/rating_history');
        const data = await response.json();

        historyList.innerHTML = ''; // Xóa nội dung cũ

        if (data.ratings.length === 0) {
            historyList.innerHTML = '<li>Bạn chưa đánh giá phim nào.</li>';
        } else {
            // Hiển thị danh sách lịch sử đánh giá
            data.ratings.forEach((item, index) => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `${index + 1}. <strong>${item.title}</strong> - ${item.rating} ⭐ (Đánh giá lúc: ${item.date})`;
                historyList.appendChild(listItem);
            });
        }

        historyModal.style.display = 'flex';
    } catch (error) {
        console.error("Lỗi khi lấy lịch sử đánh giá:", error);
    }
}

document.querySelector('.close').addEventListener('click', () => {
    const modal = document.getElementById('movieModal');
    // Thêm class fade-out
    modal.classList.add('fade-out');

    // Sau khi hiệu ứng fade-out hoàn tất, ẩn modal
    setTimeout(() => {
        modal.style.display = 'none';
        modal.classList.remove('fade-out'); // Xóa class để dùng lại sau
    }, 400); // Thời gian khớp với thời gian animation fadeOut
});

window.onclick = function (event) {
    const movieModal = document.getElementById('movieModal');
    const historyModal = document.getElementById('historyModal');

    if (event.target === movieModal) {
        movieModal.classList.add('fade-out');
        setTimeout(() => {
            movieModal.style.display = 'none';
            movieModal.classList.remove('fade-out');
        }, 400);
    }

    if (event.target === historyModal) {
        historyModal.classList.add('fade-out');
        setTimeout(() => {
            historyModal.style.display = 'none';
            historyModal.classList.remove('fade-out');
        }, 400);
    }
};

// Hàm lấy thể loại yêu thích từ API và hiển thị phim hot tương ứng
async function loadFavoriteGenresMovies() {
    try {
        // Gọi API để lấy danh sách thể loại yêu thích đã lưu
        const response = await fetch("http://127.0.0.1:5000/favorite_genres");
        if (!response.ok) throw new Error("Lỗi khi lấy thể loại yêu thích");

        const { genres } = await response.json(); // Danh sách thể loại yêu thích
        const container = document.getElementById("favorite-genres-container");
        container.innerHTML = ""; // Xóa nội dung cũ

        // Lặp qua từng thể loại và lấy phim hot tương ứng
        for (const genre of genres) {
            // Tạo section cho mỗi thể loại
            const section = document.createElement("div");
            section.classList.add("genre-section");

            const title = document.createElement("h2");
            title.innerText = `Phim Hot: ${genre}`;
            section.appendChild(title);

            const movieRow = document.createElement("div");
            movieRow.classList.add("movie-row", "scrollable-row");

            // Gọi API để lấy phim cho thể loại hiện tại
            const moviesResponse = await fetch(`http://127.0.0.1:5000/recommend?genre=${genre}`);
            if (!moviesResponse.ok) throw new Error(`Lỗi khi lấy phim cho thể loại ${genre}`);

            const movies = await moviesResponse.json();

            // Thêm các phim vào dòng hiện tại
            movies.forEach(movie => {
                const movieCard = document.createElement("div");
                movieCard.classList.add("movie-card");

                const img = document.createElement("img");
                img.src = movie.poster_url || "default_image.jpg";
                img.alt = movie.title;

                movieCard.appendChild(img);

                // Sự kiện mở modal
                movieCard.addEventListener("click", () => openModal(movie));
                movieRow.appendChild(movieCard);
            });

            section.appendChild(movieRow);
            container.appendChild(section); // Thêm section vào container chính
        }
    } catch (error) {
        console.error("Lỗi khi tải phim hot theo thể loại yêu thích:", error);
    }
}

// Sự kiện mở modal lịch sử
document.querySelector('.fa-clock-rotate-left').addEventListener('click', openHistoryModal);

// Sự kiện đóng modal lịch sử
document.getElementById('closeHistory').addEventListener('click', () => {
    const historyModal = document.getElementById('historyModal');
    // Thêm class fade-out
    historyModal.classList.add('fade-out');

    // Sau khi hiệu ứng fade-out hoàn tất, ẩn modal
    setTimeout(() => {
        historyModal.style.display = 'none';
        historyModal.classList.remove('fade-out'); // Xóa class để dùng lại sau
    }, 400); // Thời gian khớp với thời gian animation fadeOut
});
// Khởi chạy khi tải trang
window.onload = () => {
    loadFavoriteGenresMovies();
    getTopRatedMoviesForHero();
};