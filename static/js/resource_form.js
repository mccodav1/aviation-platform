// Captured at top level, synchronously, while this script is actually
// executing - document.currentScript is null once we're inside an
// event callback like DOMContentLoaded below, since it's only valid
// during a script's own initial, synchronous run.
const resourceFormScript = document.currentScript;

document.addEventListener("DOMContentLoaded", () => {

    // ==========================
    // Add Category (inline)
    // ==========================
    // Mirrors what Django admin's "+" next to a foreign-key dropdown
    // does: create the related object without leaving the page, then
    // select it in the dropdown - so "category" stays the one real
    // answer to "which category", never a second field competing with it.

    const script = resourceFormScript;
    const toggle = document.getElementById("resource-category-add-toggle");
    const addRow = document.getElementById("resource-category-add");
    const input = document.getElementById("resource-category-add-input");
    const submit = document.getElementById("resource-category-add-submit");
    const errorBox = document.getElementById("resource-category-add-error");
    const select = document.getElementById("id_category");

    if (!script || !toggle || !addRow || !input || !submit || !errorBox || !select) {
        return;
    }

    const addCategoryUrl = script.dataset.addCategoryUrl;
    const TOGGLE_LABEL_CLOSED = "+ New Category";
    const TOGGLE_LABEL_OPEN = "Cancel";

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
    }

    function clearError() {
        errorBox.hidden = true;
        errorBox.textContent = "";
    }

    function closeAddRow() {
        addRow.hidden = true;
        toggle.textContent = TOGGLE_LABEL_CLOSED;
        input.value = "";
        clearError();
    }

    toggle.addEventListener("click", () => {
        if (addRow.hidden) {
            addRow.hidden = false;
            toggle.textContent = TOGGLE_LABEL_OPEN;
            input.focus();
        } else {
            closeAddRow();
        }
    });

    function addCategory() {
        const title = input.value.trim();

        if (!title) {
            showError("Category name can't be blank.");
            return;
        }

        clearError();

        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

        fetch(addCategoryUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: `title=${encodeURIComponent(title)}`,
        })
            // The server returns a rendered <option> fragment (matching
            // the weather panel's fetch-for-HTML convention, see
            // home.js), not JSON - same shape as any other content this
            // page injects.
            .then(response => response.text().then(text => ({ ok: response.ok, text })))
            .then(({ ok, text }) => {
                if (!ok) {
                    showError(text || "Couldn't add that category.");
                    return;
                }

                // Parse into a real <option> node (a <select> is the
                // only reliable parent context for parsing <option>
                // markup) rather than trusting raw string insertion.
                const parser = document.createElement("select");
                parser.innerHTML = text;
                const newOption = parser.firstElementChild;

                // get_or_create on the server means "add" a name that
                // already exists just returns that category - reuse the
                // existing <option> instead of inserting a duplicate.
                const existing = select.querySelector(`option[value="${newOption.value}"]`);
                if (existing) {
                    existing.selected = true;
                } else {
                    select.appendChild(newOption);
                }

                closeAddRow();
            })
            .catch(() => {
                showError("Couldn't reach the server - try again.");
            });
    }

    submit.addEventListener("click", addCategory);

    input.addEventListener("keydown", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            addCategory();
        }
    });

});
