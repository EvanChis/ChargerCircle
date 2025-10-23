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
