/**
 * Switch between grid and list views
 * @param {string} viewType - 'grid' or 'list'
 */
function switchView(viewType) {
  const gridView = document.getElementById("grid-view");
  const listView = document.getElementById("list-view");
  const buttons = document.querySelectorAll(".view-toggle button");

  if (viewType === "grid") {
    gridView.classList.remove("hidden-view");
    listView.classList.add("hidden-view");

    // Update button states
    buttons[0].classList.add("active");
    buttons[1].classList.remove("active");

    // Save preference
    localStorage.setItem("preferredView", "grid");
  } else if (viewType === "list") {
    gridView.classList.add("hidden-view");
    listView.classList.remove("hidden-view");

    // Update button states
    buttons[0].classList.remove("active");
    buttons[1].classList.add("active");

    // Save preference
    localStorage.setItem("preferredView", "list");
  }
}

// Restore user's preferred view on page load
document.addEventListener("DOMContentLoaded", () => {
  const preferredView = localStorage.getItem("preferredView");
  if (preferredView) {
    switchView(preferredView);
  }
});
