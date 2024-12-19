// Enable Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Handle notification read status
function markNotificationAsRead(notificationId) {
    fetch(`/mark_notification_read/${notificationId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const notification = document.querySelector(`#notification-${notificationId}`);
                notification.classList.remove('unread');
                updateNotificationCount();
            }
        });
}

// Update notification count in navbar
function updateNotificationCount() {
    const badge = document.querySelector('#notification-badge');
    if (badge) {
        const currentCount = parseInt(badge.textContent);
        if (currentCount > 1) {
            badge.textContent = currentCount - 1;
        } else {
            badge.style.display = 'none';
        }
    }
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Password confirmation check
function validatePassword() {
    const password = document.getElementById('password');
    const password2 = document.getElementById('password2');
    
    if (password && password2) {
        if (password.value !== password2.value) {
            password2.setCustomValidity("Passwords don't match");
        } else {
            password2.setCustomValidity('');
        }
    }
}

// Dynamic grade calculation
function calculateGPA() {
    const gradeInputs = document.querySelectorAll('.grade-input');
    const creditInputs = document.querySelectorAll('.credit-input');
    let totalPoints = 0;
    let totalCredits = 0;

    for (let i = 0; i < gradeInputs.length; i++) {
        const grade = parseFloat(gradeInputs[i].value);
        const credits = parseFloat(creditInputs[i].value);
        
        if (!isNaN(grade) && !isNaN(credits)) {
            totalPoints += grade * credits;
            totalCredits += credits;
        }
    }

    const gpa = totalCredits > 0 ? (totalPoints / totalCredits).toFixed(2) : '0.00';
    document.getElementById('gpa-display').textContent = gpa;
}

// Message character counter
function updateMessageCounter(textarea) {
    const counter = document.getElementById('message-counter');
    if (counter) {
        const remaining = 1000 - textarea.value.length;
        counter.textContent = `${remaining} characters remaining`;
        counter.classList.toggle('text-danger', remaining < 50);
    }
}

// Handle file uploads
function handleFileUpload(input) {
    const fileList = input.files;
    const filePreview = document.getElementById('file-preview');
    
    if (filePreview) {
        filePreview.innerHTML = '';
        for (let file of fileList) {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <i class="fas fa-file me-2"></i>
                <span>${file.name}</span>
                <small class="text-muted">(${(file.size / 1024).toFixed(1)} KB)</small>
            `;
            filePreview.appendChild(item);
        }
    }
} 