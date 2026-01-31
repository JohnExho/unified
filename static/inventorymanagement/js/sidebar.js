// Sidebar functionality
document.addEventListener('DOMContentLoaded', function() {
    // Handle active navigation state
    const navLinks = document.querySelectorAll('.sidebar-nav a');
    const currentPath = window.location.pathname;
    
    navLinks.forEach(link => {
        const linkPath = new URL(link.href).pathname;
        
        // Check if current path matches the link
        if (linkPath === currentPath) {
            link.classList.add('active');
        }
    });
});
