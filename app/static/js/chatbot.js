// Simple Chatbot Widget for Enhanced Student Portal

// Ensure chatbot widget is always initialized, even if script loads late
(function () {
    if (document.getElementById('chatbot-btn')) return;
    // Create floating button
    const chatBtn = document.createElement('button');
    chatBtn.id = 'chatbot-btn';
    chatBtn.className = 'btn btn-primary rounded-circle';
    chatBtn.style.position = 'fixed';
    chatBtn.style.bottom = '30px';
    chatBtn.style.right = '30px';
    chatBtn.style.zIndex = '9999';
    chatBtn.innerHTML = '<i class="fas fa-robot"></i>';
    document.body.appendChild(chatBtn);

    // Create chat modal
    const modal = document.createElement('div');
    modal.id = 'chatbot-modal';
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    modal.innerHTML = `
      <div class="modal-dialog modal-dialog-bottom-right" style="max-width: 410px;">
        <div class="modal-content shadow-lg rounded-4" style="border-radius: 18px;">
          <div class="modal-header bg-primary text-white d-flex justify-content-between align-items-center rounded-top-4" style="border-top-left-radius: 18px; border-top-right-radius: 18px;">
            <h5 class="modal-title mb-0"><i class="fas fa-robot me-1"></i> Academic Assistant</h5>
            <div>
              <button type="button" class="btn btn-sm btn-light me-1" id="chatbot-minimize" title="Minimize"><i class="fas fa-minus"></i></button>
              <button type="button" class="btn-close" data-bs-dismiss="modal" id="chatbot-close"></button>
            </div>
          </div>
          <div class="modal-body px-3 py-2" id="chatbot-messages" style="height:410px; overflow-y:auto; background: #f7f9fa;">
            <div class="text-muted small">Ask me anything about your courses, assignments, or the portal!</div>
          </div>
          <div class="modal-footer p-2 bg-white rounded-bottom-4" style="border-bottom-left-radius: 18px; border-bottom-right-radius: 18px;">
            <input type="text" id="chatbot-input" class="form-control form-control-sm" placeholder="Type your question..." style="border-radius: 8px;">
            <button id="chatbot-send" class="btn btn-primary btn-sm ms-2 px-3 rounded-pill">Send</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    // Show modal on button click (restore minimized)
    chatBtn.addEventListener('click', function () {
        var modalEl = document.getElementById('chatbot-modal');
        var bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();
        chatBtn.style.display = 'none';
    });

    // Minimize button logic
    document.addEventListener('click', function (e) {
        if (e.target && (e.target.id === 'chatbot-minimize' || e.target.closest('#chatbot-minimize'))) {
            var modalEl = document.getElementById('chatbot-modal');
            var bsModal = bootstrap.Modal.getInstance(modalEl);
            if (bsModal) bsModal.hide();
            chatBtn.style.display = 'block';
        }
    });

    // When modal is hidden (by minimize or close), show button unless closed
    modal.addEventListener('hidden.bs.modal', function (e) {
        if (!modal.dataset.closed) {
            chatBtn.style.display = 'block';
        }
    });

    // Close button logic (clear history)
    document.addEventListener('click', function (e) {
        if (e.target && (e.target.id === 'chatbot-close' || e.target.closest('#chatbot-close'))) {
            var messages = document.getElementById('chatbot-messages');
            if (messages) messages.innerHTML = '<div class="text-muted small">Ask me anything about your courses, assignments, or the portal!</div>';
            modal.dataset.closed = 'true';
            setTimeout(function(){
                chatBtn.style.display = 'block';
                modal.dataset.closed = '';
            }, 400);
        }
    });

    // Handle send button
    document.addEventListener('click', function (e) {
        if (e.target && e.target.id === 'chatbot-send') {
            sendChatbotMessage();
        }
    });
    // Handle Enter key
    document.addEventListener('keydown', function (e) {
        if (e.target && e.target.id === 'chatbot-input' && e.key === 'Enter') {
            sendChatbotMessage();
        }
    });

    // --- Chat history persistence ---
    function saveChatHistory() {
        const messages = document.getElementById('chatbot-messages');
        if (!messages) return;
        localStorage.setItem('chatbot_history', messages.innerHTML);
    }
    function loadChatHistory() {
        const messages = document.getElementById('chatbot-messages');
        if (!messages) return;
        const history = localStorage.getItem('chatbot_history');
        if (history) {
            messages.innerHTML = history;
        }
    }
    function clearChatHistory() {
        localStorage.removeItem('chatbot_history');
    }

    // Restore chat history on load
    setTimeout(loadChatHistory, 200); // Wait for modal to be created

    // --- Patch appendMessage to save after each message ---
    function appendMessage(sender, text, cls) {
        const messages = document.getElementById('chatbot-messages');
        const msgDiv = document.createElement('div');
        let bubbleStyle = '';
        let senderLabel = '';
        if (sender === 'You') {
            bubbleStyle = 'background: #e3f0ff; color: #1a237e; border-radius: 14px 14px 4px 14px; padding: 8px 12px; display: inline-block; max-width: 90%;';
            senderLabel = `<div class='small text-end text-secondary mb-1'>You</div>`;
            msgDiv.className = `mb-2 text-end`;
        } else {
            bubbleStyle = 'background: #fff; color: #222; border-radius: 14px 14px 14px 4px; padding: 8px 12px; display: inline-block; max-width: 90%; box-shadow: 0 1px 2px #e3e3e3;';
            senderLabel = `<div class='small text-start text-primary mb-1'><i class="fas fa-robot"></i> Assistant</div>`;
            msgDiv.className = `mb-2 text-start`;
        }
        msgDiv.innerHTML = `${senderLabel}<div style='${bubbleStyle}'>${text}</div>`;
        messages.appendChild(msgDiv);
        messages.scrollTop = messages.scrollHeight;
        saveChatHistory();
    }

    // Patch close button logic to clear chat history and cache
    document.addEventListener('click', function (e) {
        if (e.target && (e.target.id === 'chatbot-close' || e.target.closest('#chatbot-close'))) {
            var messages = document.getElementById('chatbot-messages');
            if (messages) messages.innerHTML = '<div class="text-muted small">Ask me anything about your courses, assignments, or the portal!</div>';
            modal.dataset.closed = 'true';
            clearChatHistory();
            localStorage.removeItem('chatbot_history'); // double ensure
            setTimeout(function(){
                chatBtn.style.display = 'block';
                modal.dataset.closed = '';
            }, 400);
        }
    });

    // Fallback: also clear cache on modal hidden (in case closed via other means)
    modal.addEventListener('hidden.bs.modal', function (e) {
        if (modal.dataset.closed) {
            clearChatHistory();
            localStorage.removeItem('chatbot_history');
        }
    });

    function sendChatbotMessage() {
        const input = document.getElementById('chatbot-input');
        const msg = input.value.trim();
        if (!msg) return;
        appendMessage('You', msg, 'text-end');
        input.value = '';
        fetch('/api/chatbot/ask', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question: msg})
        })
        .then(res => res.json())
        .then(data => {
            if (data.answer) {
                appendMessage('Assistant', data.answer, 'text-start bg-light');
            } else {
                appendMessage('Assistant', data.error || 'Sorry, I could not answer that.', 'text-start bg-light');
            }
        })
        .catch(() => {
            appendMessage('Assistant', 'Sorry, something went wrong.', 'text-start bg-light');
        });
    }})();
