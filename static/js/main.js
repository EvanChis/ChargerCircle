// static/js/main.js

/*
This function runs when the webpage has finished loading. It sets up
all the interactive and real-time features of the site.
RT: This function initializes all WebSocket connections and event listeners
for real-time updates (presence, notifications, chat, course rooms).
*/
document.addEventListener('DOMContentLoaded', function () {
    
    /*
    Author: Evan
    This variable keeps track of which users are currently online.
    It's a 'Set' for efficient adding and checking of user IDs.
    RT: This is the core client-side data store for real-time presence.
    */
    let onlineUsers = new Set();

    // --- Indicator Management ---
    /*
    Author: Oju
    This function finds all the green "online" dots associated with
    a specific user (identified by their unique ID, 'userPk') and
    updates them to show whether that user is currently online or offline.
    It only makes changes if the dot's current state doesn't match the
    user's actual online status.
    RT: This function visually updates the real-time presence indicators.
    */
    // This function is now smarter and only changes the class if needed.
    function updateIndicatorState(userPk) {
        // Find all elements on the page showing presence for this user
        const presenceContainers = document.querySelectorAll(`.user-presence-container[data-user-pk="${userPk}"]`);
        presenceContainers.forEach(container => {
            const indicator = container.querySelector('.online-indicator');
            if (indicator) {
                const isCurrentlyOnline = indicator.classList.contains('is-online');
                // Check if the user ID is in our 'onlineUsers' set
                const shouldBeOnline = onlineUsers.has(userPk);
                
                // Only change the class if the visual state is wrong
                if (isCurrentlyOnline !== shouldBeOnline) {
                    if (shouldBeOnline) {
                        indicator.classList.add('is-online'); // Show dot
                    } else {
                        indicator.classList.remove('is-online'); // Hide dot
                    }
                }
            }
        });
    }

    /*
    Author: Evan
    This function goes through *all* the online indicators currently
    visible on the page and makes sure they reflect the latest online
    status stored in the 'onlineUsers' set. This is useful after
    HTMX swaps in new content or when the page first loads.
    RT: This ensures all real-time presence indicators are accurate.
    */
    function refreshAllIndicators() {
        const allUserPks = new Set();
        // Find all elements that have an online indicator
        const presenceContainers = document.querySelectorAll('.user-presence-container');
        presenceContainers.forEach(container => {
            // Get the user ID associated with this element
            const userPk = parseInt(container.dataset.userPk, 10);
            if (!isNaN(userPk)) {
                allUserPks.add(userPk);
            }
        });
        // Update the indicator for each unique user ID found
        allUserPks.forEach(pk => updateIndicatorState(pk));
    }
    
    /*
    Author: Oju
    When the page first loads, this code looks for a special script tag
    containing the initial list of users who are already online. It reads
    this list, stores it in the 'onlineUsers' set, and then immediately
    updates all the green dots on the page to reflect this initial state.
    RT: Initializes the client-side presence data when the page loads.
    */
    // --- Initial Load ---
    const onlineUsersData = document.getElementById('online-users-data');
    if (onlineUsersData) {
        // Parse the JSON data from the script tag
        const initialOnlineIds = JSON.parse(onlineUsersData.textContent);
        onlineUsers = new Set(initialOnlineIds); // Store the initial IDs
        refreshAllIndicators(); // Update dots based on initial data
    }
    
    /*
    This section sets up the main WebSocket connection used for general
    site notifications (like "You Matched!") and for receiving live
    updates about who comes online or goes offline.
    RT: Establishes the primary WebSocket for real-time notifications and presence.
    */
    // --- Global WebSocket for Notifications and Presence ---
    const mainNav = document.querySelector('.main-nav'); // Check if the main nav exists (user is logged in)
    if (mainNav) {
        // RT: Connect to the '/ws/notifications/' WebSocket endpoint.
        const notificationSocket = new WebSocket('ws://' + window.location.host + '/ws/notifications/');

        /*
        Author: Oju
        This function runs every time a message is received through the
        main notification WebSocket. It checks the message type:
        - If it's a 'notification', it displays a pop-up toast and updates
          the notification badge count if provided.
        - If it's a 'presence_update', it adds or removes the user from
          the 'onlineUsers' set and updates their green dot.
        RT: Handles incoming real-time notifications and presence updates.
        */
        notificationSocket.onmessage = function(e) {
            const data = JSON.parse(e.data); // Parse the incoming message
            if (data.type === 'notification') {
                showToast(data.message.text); // Display pop-up
                if (data.message.invite_count !== undefined) {
                    // RT: Update the notification badge in the header.
                    updateNotificationBadge(data.message.invite_count);
                }
            } else if (data.type === 'presence_update') {
                const userPk = parseInt(data.user_pk, 10);
                if (data.status === 'online') {
                    onlineUsers.add(userPk); // RT: Add user to the online set.
                } else {
                    onlineUsers.delete(userPk); // RT: Remove user from the online set.
                }
                updateIndicatorState(userPk); // RT: Update the user's green dot.
            }
        };

        // Log an error if the WebSocket connection closes unexpectedly.
        notificationSocket.onclose = function(e) {
            console.error('Notification socket closed unexpectedly');
        };
    }

    /*
    Author: Evan
    This section ensures that HTMX requests include a necessary security
    token (CSRF token) required by Django to prevent certain types of
    attacks. It reads the token from a cookie and adds it as a header
    to every HTMX request.
    RT: Essential setup for making HTMX requests work securely.
    */
    // --- HTMX CSRF Token Setup ---
    // Helper function to get a cookie value by name.
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken'); // Get the security token
    // Add an event listener that runs just before any HTMX request is sent.
    document.body.addEventListener('htmx:configRequest', function(evt) {
        // Add the token to the request headers.
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
    /*
    Author: Evan
    This function displays a small pop-up message (a "toast") at the
    bottom-right of the screen. It's used for showing notifications
    like "You matched!". The toast automatically appears and then fades
    away after a few seconds.
    RT: Used to display real-time notifications received via WebSocket.
    */
    window.showToast = function(message) {
        const container = document.getElementById('toast-container');
        if (!container) return; // Make sure the container exists
        const toast = document.createElement('div'); // Create the toast element
        toast.className = 'toast';
        toast.textContent = message;
        container.appendChild(toast);
        // Animate the toast appearing
        setTimeout(() => { toast.classList.add('show'); }, 100);
        // Set a timer to automatically remove the toast
        setTimeout(() => {
            toast.classList.remove('show');
            // Remove the element from the page after the fade-out animation finishes
            toast.addEventListener('transitionend', () => toast.remove());
        }, 3000); // Toast disappears after 3 seconds
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

    /*
    Author: Cole (Original Logic) / Oju (RT Refactor)
    This function updates the red notification badge that appears
    next to the "Messages" link in the main navigation. It shows
    or hides the badge based on the count provided (e.g., the number
    of unread session invites).
    RT: Visually updates the notification count based on real-time data.
    */
    function updateNotificationBadge(count) {
        const badgeContainer = document.getElementById('notification-badge-container');
        const badgeCount = document.getElementById('notification-badge-count');
        if (!badgeContainer || !badgeCount) return; // Make sure elements exist
        
        if (count > 0) {
            badgeCount.textContent = count; // Set the number
            badgeContainer.style.display = 'inline-block'; // Show the badge
        } else {
            badgeContainer.style.display = 'none'; // Hide the badge
        }
    }

    /*
    Author:  Oju
    This section handles the light/dark theme toggle button. When the
    button is clicked, it adds or removes the 'light-mode' class from
    the page's body and saves the user's preference (light or dark)
    in their browser's local storage so it's remembered next time.
    */
    // --- Theme Toggler ---
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-mode');
            // Save the new preference to localStorage
            localStorage.setItem('theme', document.body.classList.contains('light-mode') ? 'light' : 'dark');
        });
    }
    
    /*
    This section manages the real-time chat functionality on the
    messaging page. It establishes a WebSocket connection specific
    to the currently open chat thread.
    RT: Handles the entire real-time private chat experience.
    */
    // --- Chat Functionality ---
    const chatWindow = document.querySelector('.chat-window');
    if (chatWindow) { // Only run if we're on a page with a chat window
        const threadId = chatWindow.dataset.threadId; // Get the ID of the current chat
        // Only initialize the WebSocket if a threadId is present
        if (threadId) {
            // Get user info and page elements needed for chat
            const currentUserId = chatWindow.dataset.userId;
            const currentUserName = chatWindow.dataset.userFirstName;
            const messageList = document.getElementById('message-list');
            const chatForm = document.getElementById('chat-form');
            const messageInput = document.querySelector('.message-input');
            const typingIndicator = document.getElementById('typing-indicator');

            // RT: Connect to the specific chat thread's WebSocket endpoint.
            const chatSocket = new WebSocket('ws://' + window.location.host + '/ws/chat/' + threadId + '/');

            /*
            Author: Cole (Original Logic) / Oju (RT Refactor)
            This function runs when a message is received from the chat WebSocket.
            - If it's a 'typing' indicator from someone else, it briefly shows
              the "... is typing" message.
            - If it's a 'chat_message', it creates a new message bubble (styled
              differently if it's sent or received), adds the sender's name
              if it's a group chat, puts the message text inside, appends it
              to the message list, and scrolls down.
            RT: Handles incoming real-time chat messages and typing indicators.
            */
            chatSocket.onmessage = function(e) {
                const data = JSON.parse(e.data);

                if (data.type === 'typing') {
                    // Only show typing indicator if it's from someone else
                    if (data.sender_id != currentUserId) {
                        typingIndicator.style.display = 'block'; // Show "... is typing"
                        // Hide it again after 2 seconds
                        setTimeout(() => {
                            typingIndicator.style.display = 'none';
                        }, 2000);
                    }
                } 
                // Refactored by Angie for image handling
                else if (data.type === 'chat_message') {
                    const isSent = data.sender_id == currentUserId; // Was this message sent by me?
                    const messageDiv = document.createElement('div');
                    // Apply 'sent' or 'received' class for styling
                    messageDiv.className = 'message ' + (isSent ? 'sent' : 'received');
                    
                    let senderName = '';
                    // Add sender's name above the message in group chats (if received)
                    if (!isSent && chatWindow.dataset.participantCount > 2) {
                        senderName = `<small class="message-sender-name">${data.sender_first_name}</small>`;
                    }

                    // Build the message content. It might be text, an image, or both.
                    let messageContentHTML = '';
                    
                    // Check for an image URL
                    if (data.image_url) {
                        // Add an image tag. You'll want to style .chat-image
                        messageContentHTML += `<img src="${data.image_url}" class="chat-image" alt="User image" style="max-width: 100%; border-radius: 12px; margin-top: 5px;">`;
                    }
                    
                    // Check for text content
                    if (data.message) {
                        messageContentHTML += `<p>${data.message}</p>`;
                    }
                    
                    // Add the sender name (if any) and the message content
                    messageDiv.innerHTML = `${senderName}${messageContentHTML}`;

                    messageList.appendChild(messageDiv); // Add the new bubble to the list
                    messageList.scrollTop = messageList.scrollHeight; // Scroll to the bottom
                    typingIndicator.style.display = 'none'; // Hide typing indicator
                    
                    // Clear the file input after successful send
                    const imageInput = document.getElementById('chat-image-input');
                    if (imageInput) imageInput.value = null;
                }
                // --- END MODIFICATION ---
            };

            // Log error if chat connection closes unexpectedly.
            chatSocket.onclose = function(e) {
                console.error('Chat socket closed unexpectedly');
            };

            /*
            Author: Cole (Original Logic) / Oju (RT Refactor)
            This sets up the "Send" button and the message input field.
            - When the form is submitted (Send button or Enter key), it takes
              the text from the input, sends it over the WebSocket, and clears
              the input field.
            - When the user types anything (except Enter), it sends a "typing"
              notification over the WebSocket.
            RT: Sends outgoing chat messages and typing indicators in real-time.
            */
            if (chatForm) {
                // Handle sending a message
                chatForm.addEventListener('submit', function(e) {
                    e.preventDefault(); // Prevent normal form submission
                    const message = messageInput.value;
                    if (message.trim() !== '') { // Only send if message isn't empty
                        // RT: Send message data over WebSocket.
                        chatSocket.send(JSON.stringify({
                            'type': 'chat_message',
                            'message': message,
                            'sender_id': currentUserId,
                            'sender_first_name': currentUserName
                        }));
                        messageInput.value = ''; // Clear the input field
                    }
                });

                // Handle typing indicator
                messageInput.addEventListener('keyup', function(e) {
                    if (e.key !== 'Enter') { // Don't send typing indicator on Enter key
                        // RT: Send typing status over WebSocket.
                        chatSocket.send(JSON.stringify({
                            'type': 'typing',
                            'sender_id': currentUserId
                        }));
                    }
                });
            }
            
            // Scroll to the bottom of the message list when the page loads
            if (messageList) {
                messageList.scrollTop = messageList.scrollHeight;
            }
        }
    }

    /*
    This section handles the real-time updates within a specific
    course room page (where discussion threads are listed). It
    connects to a WebSocket specific to that course room.
    RT: Manages live updates for new threads and posts in course rooms.
    */
    // --- Course Room Functionality ---
    const courseDetailPage = document.getElementById('course-detail-page');
    if (courseDetailPage) { // Only run if on a course detail page
        const roomSlug = courseDetailPage.dataset.roomSlug; // Get the unique ID for the room
        // RT: Connect to the course room's WebSocket endpoint.
        const roomSocket = new WebSocket('ws://' + window.location.host + '/ws/course_room/' + roomSlug + '/');

        /*
        Author: Oju
        This runs when a message is received from the course room WebSocket.
        - If it's a 'new_thread', it takes the provided HTML for the new
          thread item and adds it to the top of the thread list.
        - If it's a 'new_post' (for the thread detail page), it takes the
          HTML for the new post and adds it to the bottom of the post list.
        RT: Handles incoming real-time updates for new threads and posts.
        */
        roomSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.message_type === 'new_thread') {
                const threadList = document.getElementById('thread-list');
                // RT: Insert new thread HTML at the beginning of the list.
                threadList.insertAdjacentHTML('afterbegin', data.html);
            } else if (data.message_type === 'new_post') {
                const postList = document.getElementById('post-list'); // This is on the thread detail page
                if(postList){
                    // RT: Insert new post HTML at the end of the list.
                    postList.insertAdjacentHTML('beforeend', data.html);
                }
            }
        };

        // Log error if the connection closes unexpectedly.
        roomSocket.onclose = function(e) {
            console.error('Course room socket closed unexpectedly');
        };
    }

    /*
    Author: Evan
    This uses a technique called "event delegation" to handle clicks
    and changes on elements that might be added to the page later by
    HTMX or other JavaScript. Instead of attaching listeners to each
    button directly, it listens on the whole page ('document.body')
    and checks *what* was clicked.
    RT: Handles interactions with dynamically loaded HTMX content,
    including Discover card actions and profile image uploads/navigation.
    */
    // --- Event Delegation for Dynamic Content ---
    document.body.addEventListener('click', function(event) {
        
        // Handle clicks on the Like/Skip buttons on Discover cards
        const discoverButton = event.target.closest('[data-discover-action]');
        if (discoverButton) {
            event.preventDefault();
            const direction = discoverButton.dataset.discoverAction; // 'left' or 'right'
            animateAndSubmit(direction); // Trigger animation and HTMX submit
        }

        // Handle clicks on profile image gallery next/prev arrows
        const galleryDirectionButton = event.target.closest('[data-gallery-direction]');
        if (galleryDirectionButton) {
            const userPk = galleryDirectionButton.dataset.galleryUser;
            const direction = parseInt(galleryDirectionButton.dataset.galleryDirection, 10); // -1 or 1
            changeImage(userPk, direction); // Change the displayed image
        }

        // Handle clicks on profile image gallery pagination dots
        const galleryDot = event.target.closest('[data-gallery-index]');
        if (galleryDot) {
            const userPk = galleryDot.dataset.galleryUser;
            const index = parseInt(galleryDot.dataset.galleryIndex, 10); // 0, 1, 2...
            changeImage(userPk, index); // Go directly to the clicked image index
        }
    });
    
    // Handle the file input changing (user selected an image to upload)
    document.body.addEventListener('change', function(event) {
        if (event.target.id === 'id_image') { // Check if it was the profile image input
             const form = document.getElementById('image-upload-form');
             // RT: If so, immediately trigger the HTMX form submission.
             if (form) htmx.trigger(form, 'submit');
        }
    });

    /*
    Author: Evan
    This listens for the 'htmx:afterSwap' event, which fires every
    time HTMX finishes replacing content on the page. It then calls
    'refreshAllIndicators' to make sure any new online dots are
    correctly displayed. It also resets the image gallery index if a
    new Discover card was loaded.
    RT: Ensures real-time presence indicators are updated after HTMX swaps.
    */
    // Listen for HTMX swaps to refresh indicators and discover cards
    document.body.addEventListener('htmx:afterSwap', function(event) {
        refreshAllIndicators(); // RT: Update all green dots.

        // Check if the swapped content includes a new Discover card
        const newCard = event.detail.elt.querySelector('.match-card');
        if (newCard) {
            // If yes, reset the image gallery index for that new card's user
            const userPk = newCard.querySelector('.profile-image-gallery').dataset.userPk;
            currentImageIndex[userPk] = 0;
        }
    });


    // --- START: Profile Gallery Modal (NEW VERSION) ---
    /*
    Author: Evan
    This section handles the pop-up gallery modal on the
    user profile page.
    */
    const profileImageTrigger = document.getElementById('profile-image-trigger');
    const galleryThumbnails = document.querySelectorAll('.profile-thumbnail-trigger');
    const galleryModal = document.getElementById('profile-gallery-modal');
    const galleryCloseBtn = document.getElementById('profile-gallery-close');

    if (galleryModal && galleryCloseBtn) {
        const gallery = galleryModal.querySelector('.profile-image-gallery');
        const userPk = gallery.dataset.userPk;

        // Function to open the modal
        const openModal = () => {
            galleryModal.style.display = 'flex'; // Show the modal
        }

        // Function to close the modal
        const closeModal = () => {
            galleryModal.style.display = 'none'; // Hide the modal
        }

        // --- Event Listeners ---

        // Listener for the MAIN profile image
        if (profileImageTrigger) {
            profileImageTrigger.addEventListener('click', () => {
                // Find the main image in the modal, get its index
                const mainImage = gallery.querySelector('.profile-gallery-image.active');
                let mainIndex = 0;
                if (mainImage) {
                    mainIndex = parseInt(mainImage.dataset.imageIndex, 10);
                }
                changeImage(userPk, mainIndex); // Set gallery to that index
                openModal(); // Open
            });
        }

        // Listeners for ALL the thumbnails in the "Pictures" card
        galleryThumbnails.forEach(thumb => {
            thumb.addEventListener('click', (e) => {
                // Get the index from the thumbnail that was clicked
                const clickedIndex = parseInt(e.currentTarget.dataset.galleryIndex, 10);
                changeImage(userPk, clickedIndex); // Set gallery to that index
                openModal(); // Open
            });
        });

        // Listeners for closing the modal
        galleryCloseBtn.addEventListener('click', closeModal);
        galleryModal.addEventListener('click', (e) => {
            // Close modal if user clicks on the backdrop
            if (e.target === galleryModal) {
                closeModal();
            }
        });
    }
    // --- END: Profile Gallery Modal ---


});

/*
Author: Evan
This function triggers the swipe animation (left or right) for the
Discover card and then, after a short delay, triggers the
corresponding HTMX form submission ('submitSkip' or 'submitLike').
RT: Part of the HTMX interaction on the Discover page.
*/
// 'like' and 'pass' animation
function animateAndSubmit(direction) {
    const card = document.querySelector('.match-card');
    if (!card) return; // Make sure the card exists
    // Add the appropriate animation class ('swiping-left' or 'swiping-right')
    card.classList.add('swiping-' + direction);
    // Wait for the animation to mostly complete (300ms)
    setTimeout(() => {
        // Create and dispatch a custom event ('submitSkip' or 'submitLike')
        // The HTMX forms are listening for these events.
        const eventName = (direction === 'left') ? 'submitSkip' : 'submitLike';
        document.body.dispatchEvent(new Event(eventName, { bubbles: true }));
    }, 300);
}

/*
This object stores the current image index being viewed for each
user's profile gallery (used on Discover and Profile pages).
Example: { 123: 0, 456: 2 } means user 123 is viewing image 0, user 456 is viewing image 2.
*/
let currentImageIndex = {};
/*
Author: Evan
This function handles changing the displayed image in a profile gallery.
It takes the user's ID ('userPk') and either a direction (-1 for previous,
1 for next) or a specific index to jump to. It updates the 'active'
classes on the images and pagination dots to show the correct image.
*/
function changeImage(userPk, directionOrIndex) {
    const gallery = document.getElementById(`profile-gallery-${userPk}`);
    if (!gallery) return; // Make sure the gallery exists

    const images = gallery.querySelectorAll('.profile-gallery-image');
    const dots = gallery.querySelectorAll('.pagination-dot');
    
    // Don't do anything if there's only one image or fewer
    if (images.length <= 1) return;

    // Get the current index for this user, default to 0 if not set
    let currentIndex = currentImageIndex[userPk] || 0;
    // Hide the current image and deactivate the current dot
    images[currentIndex].classList.remove('active');
    if (dots.length > 0) dots[currentIndex].classList.remove('active');

    let newIndex;
    if (directionOrIndex === 1 || directionOrIndex === -1) { // If direction was given
        newIndex = currentIndex + directionOrIndex; // Calculate next/prev index
    } else { // If a specific index was given
        newIndex = directionOrIndex; // Go directly to that index
    }
    
    // Wrap around if index goes out of bounds
    if (newIndex >= images.length) newIndex = 0; // Go to first image
    if (newIndex < 0) newIndex = images.length - 1; // Go to last image
    
    // Show the new image and activate the new dot
    images[newIndex].classList.add('active');
    if (dots.length > 0) dots[newIndex].classList.add('active');
    // Store the new index for this user
    currentImageIndex[userPk] = newIndex;
}
