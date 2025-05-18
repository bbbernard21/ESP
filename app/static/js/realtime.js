// realtime.js - Handles real-time updates for messages and notifications

document.addEventListener('DOMContentLoaded', function() {
    if (!window.currentUserId) {
        // Try to get user id from a meta tag or global variable if set by backend
        const meta = document.querySelector('meta[name="current-user-id"]');
        if (meta) window.currentUserId = meta.content;
    }
    if (!window.currentUserId) return; // Only connect if we have a user id

    const socket = io({ transports: ['websocket'] });
    window.socket = socket;

    // Join personal room for this user
    socket.on('connect', function() {
        socket.emit('join', { user_id: window.currentUserId });
    });

    // Handle new direct message
    socket.on('new_message', function(data) {
        // Optionally play a sound, show a toast, or update chat UI
        if (window.updateChatUI) {
            window.updateChatUI(data);
        } else {
            showToast('New message from ' + data.sender_name, data.body);
        }
        incrementMessageBadge();
    });

    // Handle new group message
    socket.on('new_group_message', function(data) {
        if (window.updateGroupChatUI) {
            window.updateGroupChatUI(data);
        } else {
            showToast('New group message from ' + data.sender_name, data.body);
        }
        incrementMessageBadge();
    });

    // Handle new notification
    socket.on('new_notification', function(data) {
        showToast(data.title, data.body);
        incrementNotificationBadge();
    });

    // Listen for notification read events to sync badge across tabs
    socket.on('notification_read', function(data) {
        decrementNotificationBadge();
    });

    // Listen for message read events to sync badge across tabs
    socket.on('message_read', function(data) {
        decrementMessageBadge(data.chat_id);
    });

    // Helper: Show a toast notification
    function showToast(title, message) {
        // Remove any existing toast
        let existing = document.getElementById('realtime-toast');
        if (existing) existing.remove();
        // Create toast container if not present
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.position = 'fixed';
            toastContainer.style.top = '20px';
            toastContainer.style.right = '20px';
            toastContainer.style.zIndex = 1055;
            document.body.appendChild(toastContainer);
        }
        // Create toast element
        const toast = document.createElement('div');
        toast.id = 'realtime-toast';
        toast.className = 'toast align-items-center text-bg-primary border-0 show';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        // Use Bootstrap's toast
        if (window.bootstrap && window.bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
            bsToast.show();
            toast.addEventListener('hidden.bs.toast', () => toast.remove());
        } else {
            setTimeout(() => toast.remove(), 5000);
        }
    }

    // Helper: Increment message badge
    function incrementMessageBadge() {
        updateMessageCount();
    }
    // Helper: Decrement message badge (optionally for a chat)
    function decrementMessageBadge(chatId) {
        updateMessageCount();
    }
    // Helper: Increment notification badge
    function incrementNotificationBadge() {
        updateNotificationCount();
    }

    // Helper: Decrement notification badge
    function decrementNotificationBadge() {
        updateNotificationCount();
    }

    // Fetch and update notification badge
    function updateNotificationCount() {
        fetch('/api/notifications/unread_count')
            .then(res => res.json())
            .then(data => {
                const badge = document.querySelector('.nav-link .badge.bg-warning');
                if (badge) {
                    badge.textContent = data.unread_count > 0 ? data.unread_count : '';
                    badge.style.display = data.unread_count > 0 ? '' : 'none';
                }
            });
    }
    // Fetch and update message badge
    function updateMessageCount() {
        fetch('/api/messages/unread_count')
            .then(res => res.json())
            .then(data => {
                const badge = document.querySelector('.nav-link .badge.bg-danger');
                if (badge) {
                    badge.textContent = data.unread_count > 0 ? data.unread_count : '';
                    badge.style.display = data.unread_count > 0 ? '' : 'none';
                }
            });
    }
});
