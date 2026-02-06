/**
 * Filter and Navigation Operations Module
 * Functions for filtering data by various parameters
 */

/**
 * Filter by period (daily, weekly, monthly, yearly)
 * @param {string} period - The period type
 */
function filterByPeriod(period) {
  filterByParam("period", period);
}

/**
 * Filter by status
 * @param {string} status - The status value
 */
function filterByStatus(status) {
  filterByParam("status", status);
}

/**
 * Filter by category
 * @param {string} category - The category value
 */
function filterByCategory(category) {
  filterByParam("category", category);
}

/**
 * Clear all filters and return to base URL
 */
function clearFilters() {
  window.location.href = window.location.pathname;
}
