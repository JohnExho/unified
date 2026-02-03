/**
 * Modal Operations Module
 * Generic modal open/close functions for non-dialog modals
 */

/**
 * Open a modal by ID
 * @param {string} modalId - The modal element ID
 */
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

/**
 * Close a modal by ID
 * @param {string} modalId - The modal element ID
 * @param {string} formId - Optional form ID to reset
 */
function closeModal(modalId, formId = null) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "auto";

    if (formId) {
      const form = document.getElementById(formId);
      if (form) form.reset();
    }
  }
}

/**
 * Setup modal close on outside click
 * @param {string} modalId - The modal element ID
 */
function setupModalOutsideClick(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === this) {
        closeModal(modalId);
      }
    });
  }
}

/**
 * Setup modal close on Escape key for multiple modals
 * @param {Array<string>} modalIds - Array of modal IDs
 */
function setupModalEscapeKey(modalIds) {
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      modalIds.forEach((modalId) => closeModal(modalId));
    }
  });
}

// Author/Publisher Modal Functions (specific implementations)
function openAddAuthorModal() {
  openModal("addAuthorModal");
}

function closeAddAuthorModal() {
  closeModal("addAuthorModal", "addAuthorForm");
}

function openAddPublisherModal() {
  openModal("addPublisherModal");
}

function closeAddPublisherModal() {
  closeModal("addPublisherModal", "addPublisherForm");
}
