// Register Page Scripts

// Open Terms Modal - automatically on page load
function openTermsModal() {
  const modal = document.getElementById('termsModal');
  if (modal) {
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
}

// Close Terms Modal
function closeTermsModal() {
  const modal = document.getElementById('termsModal');
  const agreeCheckbox = document.getElementById('agreeCheckbox');
  
  if (modal) {
    modal.classList.remove('show');
    document.body.style.overflow = 'auto';
    
    // Reset checkbox when closing
    if (agreeCheckbox) {
      agreeCheckbox.checked = false;
      toggleAcceptButton();
    }
  }
}

// Toggle Accept Button based on checkbox
function toggleAcceptButton() {
  const agreeCheckbox = document.getElementById('agreeCheckbox');
  const acceptBtn = document.getElementById('acceptBtn');
  
  if (agreeCheckbox && acceptBtn) {
    acceptBtn.disabled = !agreeCheckbox.checked;
  }
}

// Accept Terms and enable register button
function acceptTerms() {
  const registerBtn = document.querySelector('button[type="submit"]');
  const termsHiddenInput = document.getElementById('termsAcceptedHidden');
  
  if (registerBtn) {
    registerBtn.disabled = false;
    registerBtn.textContent = 'Register';
  }
  
  if (termsHiddenInput) {
    termsHiddenInput.value = 'true';
  }
  
  closeTermsModal();
  
  // Show success notification
  showNotification('Terms accepted! You can now register.', 'success');
}

// Show notification
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    background: ${type === 'success' ? '#d4edda' : '#f8d7da'};
    color: ${type === 'success' ? '#155724' : '#721c24'};
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 10000;
    animation: slideInRight 0.3s ease-out;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOutRight 0.3s ease-out';
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

// Close modal when clicking outside - allow closing now
window.addEventListener('click', function(event) {
  const modal = document.getElementById('termsModal');
  if (event.target === modal) {
    closeTermsModal();
  }
});

// Allow closing modal with Escape key
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    const modal = document.getElementById('termsModal');
    if (modal && modal.classList.contains('show')) {
      closeTermsModal();
    }
  }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  // Check if terms have been accepted (page reload scenario)
  const termsHiddenInput = document.getElementById('termsAcceptedHidden');
  const registerBtn = document.querySelector('button[type="submit"]');
  
  if (registerBtn && termsHiddenInput && termsHiddenInput.value === 'true') {
    // If terms already accepted, enable register button
    registerBtn.disabled = false;
    registerBtn.textContent = 'Register';
  }

  // Password confirmation validation
  const password = document.getElementById('password');
  const confirmPassword = document.getElementById('confirm_password');
  const indicator = document.getElementById('passwordMatchIndicator');

  function checkPasswordMatch() {
    if (!password || !confirmPassword || !indicator) return;

    const pwd = password.value;
    const confirmPwd = confirmPassword.value;

    if (confirmPwd === '') {
      indicator.textContent = '';
      indicator.className = 'password-match-indicator empty';
      confirmPassword.style.borderColor = '#d1d9e6';
    } else if (pwd === confirmPwd) {
      indicator.textContent = '✓ Passwords match';
      indicator.className = 'password-match-indicator match';
      confirmPassword.style.borderColor = '#28a745';
    } else {
      indicator.textContent = '✗ Passwords do not match';
      indicator.className = 'password-match-indicator no-match';
      confirmPassword.style.borderColor = '#dc3545';
    }
  }

  if (password && confirmPassword) {
    password.addEventListener('input', checkPasswordMatch);
    confirmPassword.addEventListener('input', checkPasswordMatch);
  }
  
  // Form validation
  const form = document.querySelector('form');
  
  if (form) {
    form.addEventListener('submit', function(event) {
      if (termsHiddenInput && termsHiddenInput.value !== 'true') {
        event.preventDefault();
        showNotification('Please accept the Terms and Conditions to register.', 'error');
        openTermsModal();
        return false;
      }
      
      // Additional validation
      const username = form.querySelector('input[name="username"]');
      const password = form.querySelector('input[name="password"]');
      const confirmPassword = form.querySelector('input[name="confirm_password"]');
      
      if (username && username.value.trim().length < 3) {
        event.preventDefault();
        showNotification('Username must be at least 3 characters long.', 'error');
        username.focus();
        return false;
      }
      
      if (password && password.value.length < 8) {
        event.preventDefault();
        showNotification('Password must be at least 8 characters long.', 'error');
        password.focus();
        return false;
      }

      // Check password confirmation
      if (password && confirmPassword && password.value !== confirmPassword.value) {
        event.preventDefault();
        showNotification('Passwords do not match. Please check and try again.', 'error');
        confirmPassword.focus();
        return false;
      }
    });
  }
});

// Add notification animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInRight {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOutRight {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);