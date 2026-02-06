/**
 * Book Operations Module
 * Functions for viewing, borrowing, and reserving books
 */

/**
 * View book details
 * @param {HTMLElement} bookElement - The book element with data attributes
 */
function viewBookDetails(bookElement) {
  if (!bookElement || !bookElement.dataset) {
    return;
  }

  const dialog = document.getElementById("bookDetailsDialog");
  if (!dialog) {
    return;
  }

  const {
    title = "Unknown Title",
    authors = "Unknown Author",
    isbn = "",
    description = "",
    location = "",
    status = "Unknown",
  } = bookElement.dataset;

  const titleEl = document.getElementById("bookDetailsTitle");
  const authorsEl = document.getElementById("bookDetailsAuthors");
  const isbnEl = document.getElementById("bookDetailsIsbn");
  const descriptionEl = document.getElementById("bookDetailsDescription");
  const locationEl = document.getElementById("bookDetailsLocation");
  const statusEl = document.getElementById("bookDetailsStatus");

  if (titleEl) titleEl.textContent = title;
  if (authorsEl) authorsEl.textContent = authors;
  if (isbnEl) isbnEl.textContent = isbn || "—";
  if (descriptionEl) descriptionEl.textContent = description || "No description available.";
  if (locationEl) locationEl.textContent = location || "—";
  if (statusEl) statusEl.textContent = status;

  openDialog("bookDetailsDialog");
}

/**
 * Open borrow book dialog with pre-filled data
 * @param {string|number} bookId - The book ID
 * @param {string} bookTitle - The book title
 */
function borrowBook(bookId, bookTitle) {
  // Set default due date (14 days from now)
  const now = new Date();
  now.setDate(now.getDate() + 14);
  const dueDate = now.toISOString().slice(0, 16);

  // Populate form
  document.getElementById("borrow_book_id").value = bookId;
  document.getElementById("borrow_book_title").value =
    bookTitle || "Selected Book";
  document.getElementById("borrow_due_date").value = dueDate;

  // Open dialog
  openDialog("borrowBookDialog");
}

/**
 * Reserve a book
 * @param {string|number} bookId - The book ID
 */
function reserveBook(bookId) {
  Swal.fire({
    title: "Reserve Book?",
    text: "Create a reservation for this book?",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, reserve it",
    confirmButtonColor: "#f59e0b",
  }).then((result) => {
    if (result.isConfirmed) {
      Swal.fire("Success!", "Book has been reserved.", "success");
    }
  });
}
