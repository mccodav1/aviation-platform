document.addEventListener("DOMContentLoaded", () => {

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