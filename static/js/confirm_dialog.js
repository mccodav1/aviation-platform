// Themed replacement for window.confirm() on forms - see
// templates/app/components/confirm_dialog.html. Opt a form in with:
//   data-confirm="Question shown in the dialog"
//   data-confirm-title="Dialog heading"      (optional, default "Are you sure?")
//   data-confirm-button="Confirm button text" (optional, default "Confirm")
//   data-confirm-tone="positive"             (optional - green confirm
//                                             button instead of red)
// Without JS the form just submits unconfirmed.
(function () {
    const dialog = document.getElementById("confirm-dialog");
    if (!dialog) {
        return;
    }

    const title = dialog.querySelector(".confirm-dialog-title");
    const message = dialog.querySelector(".confirm-dialog-message");
    const confirmButton = dialog.querySelector(".confirm-dialog-confirm");
    const cancelButton = dialog.querySelector(".confirm-dialog-cancel");
    let pendingForm = null;

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            pendingForm = form;
            // textContent, not innerHTML - the text can include
            // visitor-supplied values (e.g. a contact message's name).
            title.textContent = form.dataset.confirmTitle || "Are you sure?";
            message.textContent = form.dataset.confirm;
            confirmButton.textContent = form.dataset.confirmButton || "Confirm";
            dialog.classList.toggle("confirm-dialog-positive", form.dataset.confirmTone === "positive");
            dialog.showModal();
        });
    });

    confirmButton.addEventListener("click", () => {
        dialog.close();
        // form.submit() skips the submit event, so this doesn't reopen
        // the dialog.
        if (pendingForm) {
            pendingForm.submit();
        }
    });

    cancelButton.addEventListener("click", () => dialog.close());

    // Clicking the backdrop (outside the dialog box) cancels, like Escape.
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) {
            dialog.close();
        }
    });

    dialog.addEventListener("close", () => {
        pendingForm = null;
    });
})();
