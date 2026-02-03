/**
 * Library Management Utility Functions
 * Reusable helper functions used across the application
 */

/**
 * Get CSRF token from the page for POST requests
 * @returns {string} CSRF token value
 */
function getCsrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]").value;
}

/**
 * Make a fetch POST request with CSRF token
 * @param {string} url - The URL to send the request to
 * @param {Object} data - The data to send in the request body
 * @returns {Promise} Fetch promise
 */
function fetchWithCsrf(url, data = {}) {
  const formBody = Object.keys(data)
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(data[key])}`)
    .join("&");

  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-CSRFToken": getCsrfToken(),
    },
    body: formBody,
  });
}

/**
 * Handle API response with SweetAlert notifications
 * @param {Response} response - Fetch response object
 * @param {string} successMessage - Message to show on success
 * @param {boolean} reload - Whether to reload the page on success
 */
function handleApiResponse(
  response,
  successMessage = "Operation successful!",
  reload = true,
) {
  return response
    .json()
    .then((data) => {
      if (data.success) {
        Swal.fire("Success!", successMessage, "success").then(() => {
          if (reload) window.location.reload();
        });
      } else {
        Swal.fire("Error!", data.message || "Operation failed.", "error");
      }
    })
    .catch((error) => {
      Swal.fire("Error!", "An error occurred. Please try again.", "error");
      console.error("Error:", error);
    });
}

/**
 * Navigate to a specific URL
 * @param {string} url - The URL to navigate to
 */
function navigateTo(url) {
  window.location.href = url;
}

/**
 * Filter page by URL parameter
 * @param {string} paramName - Parameter name (e.g., 'period', 'status')
 * @param {string} paramValue - Parameter value
 */
function filterByParam(paramName, paramValue) {
  const url = new URL(window.location.href);
  url.searchParams.set(paramName, paramValue);
  window.location.href = url.toString();
}
