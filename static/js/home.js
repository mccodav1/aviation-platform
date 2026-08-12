document.addEventListener("DOMContentLoaded", () => {

    // ==========================
    // Weather Panel
    // ==========================

    const weatherPanel = document.getElementById("weather-panel");

    if (weatherPanel) {
        fetch(weatherPanel.dataset.url)
            .then(response => {
                if (!response.ok) {
                    throw new Error("Weather request failed");
                }

                return response.text();
            })
            .then(html => {
                weatherPanel.innerHTML = html;
            })
            .catch(error => {
                console.error("Failed to load weather:", error);

                weatherPanel.innerHTML = `
                    <div class="info-panel weather-panel">
                        <i class="bi bi-cloud-sun info-panel-icon"></i>

                        <h3>Weather</h3>

                        <p>Weather currently unavailable.</p>
                    </div>
                `;
            });
    }


    // ==========================
    // Hero Slideshow
    // ==========================

    const slides = document.querySelectorAll(".hero-image");

    if (!slides.length) {
        return;
    }

    let current = 0;

    function activate(index) {

        slides[current].classList.remove("active");

        current = index;

        slides[current].classList.add("active");
    }

    setInterval(() => {

        const next = (current + 1) % slides.length;

        activate(next);

    }, 8000);


    // ==========================
    // Hero Parallax
    // ==========================

    function updateParallax() {

        const hero = document.querySelector(".hero");
        const activeSlide = slides[current];

        if (!hero || !activeSlide) {
            return;
        }

        const rect = hero.getBoundingClientRect();

        // Stop animating once the hero has scrolled away
        if (rect.bottom <= 0 || rect.top >= window.innerHeight) {
            return;
        }

        const offset = window.scrollY * 0.20;

        activeSlide.style.translate = `0 ${offset}px`;
    }

    window.addEventListener("scroll", updateParallax, { passive: true });

    updateParallax();

});