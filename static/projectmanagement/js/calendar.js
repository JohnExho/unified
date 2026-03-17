/**
 * Calendar Page JavaScript
 * Handles calendar interactions and functionality
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize calendar event listeners
  initializeCalendarEvents();
  // Add project click handlers
  addProjectClickHandlers();
});

/**
 * Initialize calendar event listeners
 */
function initializeCalendarEvents() {
  const eventItems = document.querySelectorAll('.event-item');
  
  eventItems.forEach(item => {
    item.addEventListener('mouseenter', function() {
      this.style.opacity = '0.8';
    });

    item.addEventListener('mouseleave', function() {
      this.style.opacity = '1';
    });
  });

  // Initialize tooltips
  initializeTooltips();
}

/**
 * Add click handlers for project items
 */
function addProjectClickHandlers() {
  const projectEvents = document.querySelectorAll('.event-item.project-event');
  
  projectEvents.forEach(item => {
    item.style.cursor = 'pointer';
    item.addEventListener('click', function(e) {
      e.preventDefault();
      const projectName = this.getAttribute('title');
      if (projectName) {
        // Redirect to projects page with search query
        window.location.href = `/researchmanagement/projects/?search=${encodeURIComponent(projectName)}`;
      }
    });
  });
}

/**
 * Initialize tooltips for event items
 */
function initializeTooltips() {
  const eventItems = document.querySelectorAll('.event-item');
  
  eventItems.forEach(item => {
    const title = item.getAttribute('title');
    if (title) {
      item.addEventListener('mouseenter', function() {
        showTooltip(this, title);
      });

      item.addEventListener('mouseleave', function() {
        hideTooltip();
      });
    }
  });
}

/**
 * Show tooltip
 */
function showTooltip(element, text) {
  // Remove existing tooltip if any
  hideTooltip();
  
  const tooltip = document.createElement('div');
  tooltip.className = 'tooltip';
  tooltip.textContent = text;
  tooltip.style.cssText = `
    position: fixed;
    background: #1a202c;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    white-space: nowrap;
    z-index: 1000;
    pointer-events: none;
  `;
  
  document.body.appendChild(tooltip);
  
  const rect = element.getBoundingClientRect();
  tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
  tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
  
  // Adjust if tooltip goes off-screen
  const tooltipRect = tooltip.getBoundingClientRect();
  if (tooltipRect.left < 0) {
    tooltip.style.left = '8px';
  }
  if (tooltipRect.right > window.innerWidth) {
    tooltip.style.left = (window.innerWidth - tooltip.offsetWidth - 8) + 'px';
  }
}

/**
 * Hide tooltip
 */
function hideTooltip() {
  const tooltip = document.querySelector('.tooltip');
  if (tooltip) {
    tooltip.remove();
  }
}

/**
 * Navigate to specific month
 */
function navigateToMonth(year, month) {
  const currentUrl = new URL(window.location.href);
  currentUrl.searchParams.set('year', year);
  currentUrl.searchParams.set('month', month);
  window.location.href = currentUrl.toString();
}

/**
 * Navigate to today
 */
function navigateToToday() {
  const today = new Date();
  navigateToMonth(today.getFullYear(), today.getMonth() + 1);
}
