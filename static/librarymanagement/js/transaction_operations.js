/**
 * Transaction Operations Module
 * Functions for managing book transactions (returns, renewals)
 */

/**
 * Return a book
 * @param {string|number} transactionId - The transaction ID
 */
function returnBook(transactionId) {
  Swal.fire({
    title: "Return Book?",
    text: "Mark this book as returned?",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, return it",
    confirmButtonColor: "#10b981",
    input: "checkbox",
    inputPlaceholder: "Apply fine for overdue",
  }).then((result) => {
    if (result.isConfirmed) {
      fetchWithCsrf(
        `/librarymanagement/transactions/${transactionId}/return/`,
        {
          apply_fine: result.value ? "true" : "false",
        },
      ).then((response) =>
        handleApiResponse(response, "Book has been returned.", true),
      );
    }
  });
}

/**
 * Renew a book transaction
 * @param {string|number} transactionId - The transaction ID
 */
function renewBook(transactionId) {
  Swal.fire({
    title: "Renew Book?",
    text: "Extend the due date for this book?",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, renew it",
    confirmButtonColor: "#3b82f6",
    input: "number",
    inputLabel: "Extend by how many days?",
    inputValue: 14,
    inputAttributes: {
      min: 1,
      max: 30,
      step: 1,
    },
  }).then((result) => {
    if (result.isConfirmed) {
      fetchWithCsrf(`/librarymanagement/transactions/${transactionId}/renew/`, {
        extend_days: result.value || 14,
      }).then((response) =>
        handleApiResponse(response, "Book has been renewed.", true),
      );
    }
  });
}

/**
 * View transaction details
 * @param {string|number} transactionId - The transaction ID
 */
function viewTransactionDetails(transactionId) {
  window.location.href = `/librarymanagement/transactions/${transactionId}/`;
}

// Ensure functions are available in the global scope for inline handlers
window.returnBook = returnBook;
window.renewBook = renewBook;
window.viewTransactionDetails = viewTransactionDetails;
