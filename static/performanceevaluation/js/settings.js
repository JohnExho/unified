(() => {
    const firstNameInput = document.getElementById("firstName");
    const lastNameInput = document.getElementById("lastName");
    const avatarCircle = document.getElementById("avatarCircle");
    const modal = document.getElementById("addressModal");
    const openBtn = document.getElementById("openAddressModal");
    const closeBtn = document.getElementById("closeModal");
    const country2Input = document.getElementById("country2");
    const address2Fields = document.getElementById("address2Fields");

    window.handleCancel = () => {
        if (confirm("Discard changes?")) location.reload();
    };

    const updateAvatar = () => {
        if (!firstNameInput || !lastNameInput || !avatarCircle) return;
        const initials = (firstNameInput.value.charAt(0) + lastNameInput.value.charAt(0)).toUpperCase();
        if (!avatarCircle.style.backgroundImage) {
            avatarCircle.textContent = initials || "JD";
        }
    };
    firstNameInput?.addEventListener("input", updateAvatar);
    lastNameInput?.addEventListener("input", updateAvatar);

    openBtn?.addEventListener("click", () => modal.classList.remove("hidden"));
    closeBtn?.addEventListener("click", () => modal.classList.add("hidden"));
    modal?.addEventListener("click", e => {
        if (e.target === modal) modal.classList.add("hidden");
    });

    country2Input?.addEventListener("input", () => {
        if (country2Input.value.trim() !== "") {
            address2Fields.classList.remove("hidden");
        } else {
            address2Fields.classList.add("hidden");
            address2Fields.querySelectorAll("input").forEach(i => i.value = "");
        }
    });

    const phoneInput = document.getElementById("phone");
    if (phoneInput) {
        phoneInput.addEventListener("input", () => {
            phoneInput.value = phoneInput.value.replace(/\D/g, "");
            if (phoneInput.value.length > 20) {
                phoneInput.value = phoneInput.value.slice(0, 20);
            }
        });
    }
})();
