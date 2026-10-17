// The navbar's account menu is a <details> element, which opens and
// closes on its own; this just closes it on a click outside it or Esc,
// like any other dropdown.
(function () {
    const menu = document.querySelector(".nav-account");
    if (!menu) {
        return;
    }

    document.addEventListener("click", (event) => {
        if (menu.open && !menu.contains(event.target)) {
            menu.open = false;
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menu.open) {
            menu.open = false;
            menu.querySelector("summary").focus();
        }
    });
})();
