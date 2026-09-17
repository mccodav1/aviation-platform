document.addEventListener("DOMContentLoaded", () => {

    // ==========================
    // Navbar Scroll State
    // ==========================

    // The navbar is transparent over the hero image at the top of the
    // page (see .page-home .navbar in navbar.css) but needs a solid
    // background once the hero scrolls out from under it, or page
    // content underneath would show through/behind the nav links.
    // --nav-fade tracks scroll position directly (0 at the top, 1 once
    // scrolled NAV_FADE_DISTANCE px down) rather than a CSS transition
    // on a timer, so the fade tracks the scroll itself instead of
    // jumping in over a fixed duration the instant scrolling starts.
    const NAV_FADE_DISTANCE = 400;

    const syncNavFade = () => {
        const fade = Math.min(window.scrollY / NAV_FADE_DISTANCE, 1);
        document.body.style.setProperty("--nav-fade", fade);
    };

    syncNavFade();
    window.addEventListener("scroll", syncNavFade, { passive: true });

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
                        <div class="weather-panel-header">
                            <i class="bi bi-cloud-sun weather-panel-icon"></i>
                            <h3>Weather</h3>
                        </div>

                        <p>Weather currently unavailable.</p>
                    </div>
                `;
            });
    }

    // ==========================
    // Events Calendar
    // ==========================

    // A single delegated listener rather than binding to each prev/next
    // link directly - the links themselves get replaced along with the
    // rest of the calendar on every month switch, so a direct binding
    // would only ever work for the first month shown.
    const calendarWidget = document.getElementById("calendar-widget");

    if (calendarWidget) {
        calendarWidget.addEventListener("click", (event) => {
            const link = event.target.closest(".calendar-nav");
            if (!link) {
                return;
            }

            event.preventDefault();

            fetch(link.href)
                .then(response => {
                    if (!response.ok) {
                        throw new Error("Calendar request failed");
                    }

                    return response.text();
                })
                .then(html => {
                    calendarWidget.innerHTML = html;
                })
                .catch(error => {
                    console.error("Failed to load calendar:", error);
                });
        });
    }

});