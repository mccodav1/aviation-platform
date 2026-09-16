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
                        <div class="weather-panel-header">
                            <i class="bi bi-cloud-sun weather-panel-icon"></i>
                            <h3>Weather</h3>
                        </div>

                        <p>Weather currently unavailable.</p>
                    </div>
                `;
            });
    }

});