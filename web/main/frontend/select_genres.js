const maxSelections = 3; // Số thể loại tối đa
let selectedGenres = []; // Lưu thể loại đã chọn
const genreButtons = document.querySelectorAll(".genre-button");
const progressDisplay = document.getElementById("selection-progress");
const continueButton = document.getElementById("continue-button");

// Xử lý chọn và bỏ chọn thể loại
genreButtons.forEach(button => {
    button.addEventListener("click", () => {
        const genre = button.getAttribute("data-genre");

        if (selectedGenres.includes(genre)) {
            selectedGenres = selectedGenres.filter(g => g !== genre);
            button.classList.remove("selected");
        } else if (selectedGenres.length < maxSelections) {
            selectedGenres.push(genre);
            button.classList.add("selected");
        }

        // Cập nhật tiến trình
        progressDisplay.innerText = `${selectedGenres.length}/3 Thể Loại Được Chọn`;

        // Kích hoạt hoặc vô hiệu hóa nút Tiếp Tục
        if (selectedGenres.length === maxSelections) {
            continueButton.classList.add("active");
        } else {
            continueButton.classList.remove("active");
        }
    });
});

// Xử lý khi bấm "Tiếp Tục"
continueButton.addEventListener("click", async () => {
    if (selectedGenres.length === maxSelections) {
        try {
            const response = await fetch("http://127.0.0.1:5000/save_favorite_genres", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ genres: selectedGenres })
            });

            const result = await response.json();
            if (response.ok) {
                console.log("Thể loại yêu thích đã lưu:", result);
                window.location.href = "mainpage.html"; // Chuyển hướng sang trang index.html
            } else {
                alert("Lỗi: " + result.error);
            }
        } catch (error) {
            console.error("Lỗi kết nối:", error);
        }
    }
});