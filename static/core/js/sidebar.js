  document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname.replace(/\/$/, "");

    document.querySelectorAll(".sidebar-nav a").forEach(link => {
      const url = new URL(link.href, window.location.origin);
      const linkPath = url.pathname.replace(/\/$/, "");

      if (
        currentPath === linkPath ||
        currentPath.startsWith(linkPath + "/")
      ) {
        link.classList.add("active");
        link.closest("li")?.classList.add("active");
      }
    });
  });