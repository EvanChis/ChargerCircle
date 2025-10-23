// static/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    
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
                updatePresenceIndicator(data.user_pk, data.status);
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

    function updatePresenceIndicator(userPk, status) {
        const presenceElements = document.querySelectorAll(`.user-presence-container[data-user-pk="${userPk}"]`);
        presenceElements.forEach(container => {
            let indicator = container.querySelector('.online-indicator');
            if (status === 'online') {
                if (!indicator) {
                    indicator = document.createElement('span');
                    indicator.className = 'online-indicator';
                    const userName = container.querySelector('.user-name');
                    if(userName) userName.appendChild(indicator);
                }
            } else { // 'offline'
                if (indicator) {
                    indicator.remove();
                }
            }
        });
    }

    // --- Theme Toggler ---
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const body = document.body;
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            body.classList.add('light-mode');
        }
        themeToggle.addEventListener('click', () => {
            body.classList.toggle('light-mode');
            localStorage.setItem('theme', body.classList.contains('light-mode') ? 'light' : 'dark');
        });
    }
    
    // --- Chat Functionality ---
    const chatWindow = document.querySelector('.chat-window');
    if (chatWindow) {
        const threadId = chatWindow.dataset.threadId;
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

document.body.addEventListener('htmx:afterSwap', function(event) {
    const newCard = event.detail.elt.querySelector('.match-card');
    if (newCard) {
        const userPk = newCard.querySelector('.profile-image-gallery').dataset.userPk;
        currentImageIndex[userPk] = 0;
    }
});
