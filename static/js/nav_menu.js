// Collapses the navbar into a drop-down menu whenever the full bar
// doesn't fit across the screen - on phones and tablets, and on laptops
// too narrow for every link (officers see more items than visitors, and
// the links themselves are editable in the admin, so a fixed screen
// width can't say when that is). The full bar is laid out, measured,
// and swapped for the menu button only if it overflows.
(function () {
    const navbar = document.querySelector(".navbar");
    const inner = navbar && navbar.querySelector(".nav-inner");
    const toggle = navbar && navbar.querySelector(".nav-toggle");
    if (!inner || !toggle) {
        return;
    }
    const icon = toggle.querySelector("i");

    function setOpen(open) {
        navbar.classList.toggle("nav-open", open);
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Close menu" : "Menu");
        icon.className = open ? "bi bi-x-lg" : "bi bi-list";
    }

    function fit() {
        navbar.classList.remove("nav-collapsed");
        const overflows = inner.scrollWidth > inner.clientWidth + 1;
        navbar.classList.toggle("nav-collapsed", overflows);
        if (!overflows) {
            setOpen(false);
        }
    }

    let pending = false;
    function refit() {
        if (!pending) {
            pending = true;
            requestAnimationFrame(() => {
                pending = false;
                fit();
            });
        }
    }

    fit();
    window.addEventListener("resize", refit);
    // Web fonts arriving late change how wide the links are.
    if (document.fonts) {
        document.fonts.ready.then(refit);
    }
    window.addEventListener("load", refit);

    toggle.addEventListener("click", () => {
        setOpen(!navbar.classList.contains("nav-open"));
    });

    document.addEventListener("click", (event) => {
        if (navbar.classList.contains("nav-open") && !navbar.contains(event.target)) {
            setOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && navbar.classList.contains("nav-open")) {
            setOpen(false);
            toggle.focus();
        }
    });
})();
