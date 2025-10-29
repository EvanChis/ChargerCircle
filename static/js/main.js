// static/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    
    let onlineUsers = new Set();

    // --- Indicator Management ---
    // This function is now smarter and only changes the class if needed.
    function updateIndicatorState(userPk) {
        const presenceContainers = document.querySelectorAll(`.user-presence-container[data-user-pk="${userPk}"]`);
        presenceContainers.forEach(container => {
            const indicator = container.querySelector('.online-indicator');
            if (indicator) {
                const isCurrentlyOnline = indicator.classList.contains('is-online');
                const shouldBeOnline = onlineUsers.has(userPk);
                
                if (isCurrentlyOnline !== shouldBeOnline) {
                    if (shouldBeOnline) {
                        indicator.classList.add('is-online');
                    } else {
                        indicator.classList.remove('is-online');
                    }
                }
            }
        });
    }

    function refreshAllIndicators() {
        const allUserPks = new Set();
        const presenceContainers = document.querySelectorAll('.user-presence-container');
        presenceContainers.forEach(container => {
            const userPk = parseInt(container.dataset.userPk, 10);
            if (!isNaN(userPk)) {
                allUserPks.add(userPk);
            }
        });
        allUserPks.forEach(pk => updateIndicatorState(pk));
    }
    
    // --- Initial Load ---
    const onlineUsersData = document.getElementById('online-users-data');
    if (onlineUsersData) {
        const initialOnlineIds = JSON.parse(onlineUsersData.textContent);
        onlineUsers = new Set(initialOnlineIds);
        refreshAllIndicators();
    }
    
    // --- Global WebSocket for Notifications and Presence ---
    const mainNav = document.querySelector('.main-nav');
    if (mainNav) {
        const notificationSocket = new WebSocket('ws://' + window.location.host + '/ws/notifications/');

        notificationSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.type === 'notification') {
                showToast(data.message.text);
                if (data.message.invite_count !== undefined) {
                    updateNotificationBadge(data.message.invite_count);
                }
            } else if (data.type === 'presence_update') {
                const userPk = parseInt(data.user_pk, 10);
                if (data.status === 'online') {
                    onlineUsers.add(userPk);
                } else {
                    onlineUsers.delete(userPk);
                }
                updateIndicatorState(userPk);
            }
        };

        notificationSocket.onclose = function(e) {
            console.error('Notification socket closed unexpectedly');
        };
    }

    // --- HTMX CSRF Token Setup ---
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');
    document.body.addEventListener('htmx:configRequest', function(evt) {
        evt.detail.headers['X-CSRFToken'] = csrftoken;
    });

    // Custom confirmation for HTMX forms
    document.body.addEventListener('click', function(evt) {
        const button = evt.target;
        const form = button.closest('form');
        
        if (form && form.hasAttribute('data-confirm')) {
            evt.preventDefault();
            const confirmMessage = form.getAttribute('data-confirm');
            showConfirm(confirmMessage, () => {
                // Trigger the form submission
                form.requestSubmit();
            });
        }
    });

    // --- Global Helper Functions ---
    window.showToast = function(message) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => { toast.classList.add('show'); }, 100);
        setTimeout(() => {
            toast.classList.remove('show');
            toast.addEventListener('transitionend', () => toast.remove());
        }, 3000);
    }

    // Custom Confirmation Dialog
    window.showConfirm = function(message, onConfirm, onCancel = null) {
        // Create modal backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'confirm-backdrop';
        backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.2s ease;
        `;

        // Create dialog box
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.style.cssText = `
            background: var(--card-bg, #fff);
            border-radius: 8px;
            padding: 24px;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            transform: scale(0.9);
            transition: transform 0.2s ease;
        `;

        dialog.innerHTML = `
            <div style="margin-bottom: 20px; font-size: 16px; line-height: 1.5; color: var(--text-primary, #333);">
                ${message}
            </div>
            <div style="display: flex; gap: 12px; justify-content: flex-end;">
                <button class="btn btn-secondary btn-sm" id="confirm-cancel" style="padding: 8px 16px;">
                    Cancel
                </button>
                <button class="btn btn-primary btn-sm" id="confirm-ok" style="padding: 8px 16px;">
                    OK
                </button>
            </div>
        `;

        backdrop.appendChild(dialog);
        document.body.appendChild(backdrop);

        // Animate in
        requestAnimationFrame(() => {
            backdrop.style.opacity = '1';
            dialog.style.transform = 'scale(1)';
        });

        // Handle button clicks
        const cancelBtn = dialog.querySelector('#confirm-cancel');
        const okBtn = dialog.querySelector('#confirm-ok');

        const closeDialog = () => {
            backdrop.style.opacity = '0';
            dialog.style.transform = 'scale(0.9)';
            setTimeout(() => {
                document.body.removeChild(backdrop);
            }, 200);
        };

        cancelBtn.addEventListener('click', () => {
            closeDialog();
            if (onCancel) onCancel();
        });

        okBtn.addEventListener('click', () => {
            closeDialog();
            if (onConfirm) onConfirm();
        });

        // Handle backdrop click
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                closeDialog();
                if (onCancel) onCancel();
            }
        });

        // Handle escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                closeDialog();
                if (onCancel) onCancel();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    }

    function updateNotificationBadge(count) {
        const badgeContainer = document.getElementById('notification-badge-container');
        const badgeCount = document.getElementById('notification-badge-count');
        if (!badgeContainer || !badgeCount) return;
        
        if (count > 0) {
            badgeCount.textContent = count;
            badgeContainer.style.display = 'inline-block';
        } else {
            badgeContainer.style.display = 'none';
        }
    }

    // --- Theme Toggler ---
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-mode');
            // Save the new preference to localStorage
            localStorage.setItem('theme', document.body.classList.contains('light-mode') ? 'light' : 'dark');
        });
    }
    
    // --- Chat Functionality ---
    const chatWindow = document.querySelector('.chat-window');
    if (chatWindow) {
        const threadId = chatWindow.dataset.threadId;
        // Only initialize the WebSocket if a threadId is present
        if (threadId) {
            const currentUserId = chatWindow.dataset.userId;
            const currentUserName = chatWindow.dataset.userFirstName;
            const messageList = document.getElementById('message-list');
            const chatForm = document.getElementById('chat-form');
            const messageInput = document.querySelector('.message-input');
            const typingIndicator = document.getElementById('typing-indicator');

            const chatSocket = new WebSocket('ws://' + window.location.host + '/ws/chat/' + threadId + '/');

            chatSocket.onmessage = function(e) {
                const data = JSON.parse(e.data);

                if (data.type === 'typing') {
                    if (data.sender_id != currentUserId) {
                        typingIndicator.style.display = 'block';
                        setTimeout(() => {
                            typingIndicator.style.display = 'none';
                        }, 2000);
                    }
                } else if (data.type === 'chat_message') {
                    const isSent = data.sender_id == currentUserId;
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message ' + (isSent ? 'sent' : 'received');
                    
                    let senderName = '';
                    if (!isSent && chatWindow.dataset.participantCount > 2) {
                        senderName = `<small class="message-sender-name">${data.sender_first_name}</small>`;
                    }

                    messageDiv.innerHTML = `${senderName}<p>${data.message}</p>`;
                    messageList.appendChild(messageDiv);
                    messageList.scrollTop = messageList.scrollHeight;
                    typingIndicator.style.display = 'none';
                }
            };

            chatSocket.onclose = function(e) {
                console.error('Chat socket closed unexpectedly');
            };

            if (chatForm) {
                chatForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    const message = messageInput.value;
                    if (message.trim() !== '') {
                        chatSocket.send(JSON.stringify({
                            'type': 'chat_message',
                            'message': message,
                            'sender_id': currentUserId,
                            'sender_first_name': currentUserName
                        }));
                        messageInput.value = '';
                    }
                });

                messageInput.addEventListener('keyup', function(e) {
                    if (e.key !== 'Enter') {
                        chatSocket.send(JSON.stringify({
                            'type': 'typing',
                            'sender_id': currentUserId
                        }));
                    }
                });
            }
            
            if (messageList) {
                messageList.scrollTop = messageList.scrollHeight;
            }
        }
    }

    // --- Course Room Functionality ---
    const courseDetailPage = document.getElementById('course-detail-page');
    if (courseDetailPage) {
        const roomSlug = courseDetailPage.dataset.roomSlug;
        const roomSocket = new WebSocket('ws://' + window.location.host + '/ws/course_room/' + roomSlug + '/');

        roomSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.message_type === 'new_thread') {
                const threadList = document.getElementById('thread-list');
                threadList.insertAdjacentHTML('afterbegin', data.html);
            } else if (data.message_type === 'new_post') {
                const postList = document.getElementById('post-list');
                if(postList){
                    postList.insertAdjacentHTML('beforeend', data.html);
                }
            }
        };

        roomSocket.onclose = function(e) {
            console.error('Course room socket closed unexpectedly');
        };
    }

    // --- Event Delegation for Dynamic Content ---
    document.body.addEventListener('click', function(event) {
        
        const discoverButton = event.target.closest('[data-discover-action]');
        if (discoverButton) {
            event.preventDefault();
            const direction = discoverButton.dataset.discoverAction;
            animateAndSubmit(direction);
        }

        const galleryDirectionButton = event.target.closest('[data-gallery-direction]');
        if (galleryDirectionButton) {
            const userPk = galleryDirectionButton.dataset.galleryUser;
            const direction = parseInt(galleryDirectionButton.dataset.galleryDirection, 10);
            changeImage(userPk, direction);
        }

        const galleryDot = event.target.closest('[data-gallery-index]');
        if (galleryDot) {
            const userPk = galleryDot.dataset.galleryUser;
            const index = parseInt(galleryDot.dataset.galleryIndex, 10);
            changeImage(userPk, index);
        }
    });
    
    document.body.addEventListener('change', function(event) {
        if (event.target.id === 'id_image') {
             const form = document.getElementById('image-upload-form');
             if (form) htmx.trigger(form, 'submit');
        }
    });

    // Listen for HTMX swaps to refresh indicators and discover cards
    document.body.addEventListener('htmx:afterSwap', function(event) {
        refreshAllIndicators();

        const newCard = event.detail.elt.querySelector('.match-card');
        if (newCard) {
            const userPk = newCard.querySelector('.profile-image-gallery').dataset.userPk;
            currentImageIndex[userPk] = 0;
        }
    });
});

// 'like' and 'pass' animation
function animateAndSubmit(direction) {
    const card = document.querySelector('.match-card');
    if (!card) return;
    card.classList.add('swiping-' + direction);
    setTimeout(() => {
        const eventName = (direction === 'left') ? 'submitSkip' : 'submitLike';
        document.body.dispatchEvent(new Event(eventName, { bubbles: true }));
    }, 300);
}

let currentImageIndex = {};
function changeImage(userPk, directionOrIndex) {
    const gallery = document.getElementById(`profile-gallery-${userPk}`);
    if (!gallery) return;

    const images = gallery.querySelectorAll('.profile-gallery-image');
    const dots = gallery.querySelectorAll('.pagination-dot');
    
    if (images.length <= 1) return;

    let currentIndex = currentImageIndex[userPk] || 0;
    images[currentIndex].classList.remove('active');
    if (dots.length > 0) dots[currentIndex].classList.remove('active');

    let newIndex;
    if (directionOrIndex === 1 || directionOrIndex === -1) {
        newIndex = currentIndex + directionOrIndex;
    } else {
        newIndex = directionOrIndex;
    }
    
    if (newIndex >= images.length) newIndex = 0;
    if (newIndex < 0) newIndex = images.length - 1;
    
    images[newIndex].classList.add('active');
    if (dots.length > 0) dots[newIndex].classList.add('active');
    currentImageIndex[userPk] = newIndex;
}
