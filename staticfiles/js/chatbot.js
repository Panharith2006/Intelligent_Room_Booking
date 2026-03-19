// Emoji categories for the picker
console.log('[chatbot] chatbot.js loaded');
const emojiCategories = {
    'Smileys': ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '😚', '😙', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪', '🤤', '😴'],
    'Gestures': ['👋', '🤚', '🖐️', '✋', '🖖', '👌', '🤏', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝', '🙏', '💪', '🦵', '🦶', '👂', '👃', '🧠', '🦷', '🦴', '👀', '👁️', '👅', '👄'],
    'Hearts': ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '☮️', '✝️', '☪️', '🕉️', '☸️', '✡️', '🔯', '🕎', '☯️', '☦️', '🛐', '⛎', '♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'],
    'Animals': ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐽', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🐤', '🐣', '🐥', '🦆', '🦅', '🦉', '🦇', '🐺', '🐗', '🐴', '🦄', '🐝', '🐛', '🦋', '🐌', '🐞', '🐜', '🦟', '🦗'],
    'Food': ['🍏', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🍈', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🍆', '🥑', '🥦', '🥬', '🥒', '🌶️', '🌽', '🥕', '🧄', '🧅', '🥔', '🍠', '🥐', '🥯', '🍞', '🥖', '🥨', '🧀', '🥚', '🍳', '🧈', '🥞', '🧇', '🥓', '🥩'],
    'Activities': ['⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🎱', '🪀', '🏓', '🏸', '🏒', '🏑', '🥍', '🏏', '🥅', '⛳', '🪁', '🏹', '🎣', '🤿', '🥊', '🥋', '🎽', '🛹', '🛼', '🛷', '⛸️', '🥌', '🎿', '⛷️', '🏂', '🪂', '🏋️', '🤼', '🤸', '🤺', '⛹️', '🤾', '🏌️'],
    'Travel': ['🚗', '🚕', '🚙', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐', '🚚', '🚛', '🚜', '🦯', '🦽', '🦼', '🛴', '🚲', '🛵', '🏍️', '🛺', '🚨', '🚔', '🚍', '🚘', '🚖', '🚡', '🚠', '🚟', '🚃', '🚋', '🚞', '🚝', '🚄', '🚅', '🚈', '🚂', '🚆', '🚇', '🚊', '🚉', '✈️'],
    'Objects': ['⌚', '📱', '📲', '💻', '⌨️', '🖥️', '🖨️', '🖱️', '🖲️', '🕹️', '🗜️', '💾', '💿', '📀', '📼', '📷', '📸', '📹', '🎥', '📽️', '🎞️', '📞', '☎️', '📟', '📠', '📺', '📻', '🎙️', '🎚️', '🎛️', '🧭', '⏱️', '⏲️', '⏰', '🕰️', '⌛', '⏳', '📡', '🔋', '🔌', '💡', '🔦']
};

class ChatbotWidget {
    constructor() {
        this.isOpen = false;
        this.messages = [];
        this.chatbotApiUrl = '/chatbot';
        this.userEmail = this.getUserEmail();
        this.sessionId = this.loadSessionId();
        
        try { 
            window.chatbotInitialized = window.chatbotInitialized || false; 
        } catch (e) {
            console.error('Failed to set chatbotInitialized flag:', e);
        }
        
        this.init();
    }
    
    init() {
        this.createWidget();
        this.attachEventListeners();
        
        try { 
            this.showQuickActions(); 
        } catch (e) {
            console.error('Failed to show quick actions:', e);
        }
        
        this.greetUser();
        
        try {
            setTimeout(() => {
                if (!this.isOpen) {
                    this.showMiniQuickActions();
                    setTimeout(() => this.hideMiniQuickActions(), 2500);
                }
            }, 1200);
        } catch (e) {
            console.error('Failed to show mini quick actions:', e);
        }
    }
    
    getUserEmail() {
        const emailElement = document.querySelector('[data-user-email]');
        return emailElement ? emailElement.dataset.userEmail : '';
    }

    loadSessionId() {
        try {
            let sid = localStorage.getItem('chatbot_session_id');
            if (!sid) {
                sid = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
                localStorage.setItem('chatbot_session_id', sid);
            }
            return sid;
        } catch (e) {
            return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
        }
    }

    saveSessionId(sessionId) {
        try {
            this.sessionId = sessionId;
            localStorage.setItem('chatbot_session_id', sessionId);
        } catch (e) {
            console.warn('Could not save session ID:', e);
        }
    }
    
    createWidget() {
        console.log('[chatbot] createWidget called');
        const widgetHTML = `
            <div class="chatbot-container">
                <button class="chatbot-button" id="chatbot-toggle">
                    <i class="fas fa-comments"></i>
                </button>
                <div id="chatbot-mini-actions"></div>
                
                <div class="chatbot-window" id="chatbot-window">
                    <div class="chatbot-header">
                        <div style="display:flex;flex-direction:column;">
                            <h3>AI Booking Assistant</h3>
                            <div class="subtitle">Try: "Find available rooms"</div>
                        </div>
                        <button class="chatbot-close" id="chatbot-close" aria-label="Close chat">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="chatbot-messages" id="chatbot-messages">
                        <!-- Messages will be added here -->
                    </div>
                    
                    <div class="chatbot-input-area">
                        <button class="chatbot-emoji" id="chatbot-emoji" title="Emoji Picker" type="button">
                            <span id="chatbot-emoji-icon">😊</span>
                        </button>
                        <input 
                            type="text" 
                            class="chatbot-input" 
                            id="chatbot-input" 
                            placeholder="Type your message..."
                            autocomplete="off"
                        />
                        <button class="chatbot-send" id="chatbot-send">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                        <div id="chatbot-emoji-picker"></div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        console.log('[chatbot] Widget HTML inserted into DOM');
    }
    
    attachEventListeners() {
        console.log('[chatbot] attachEventListeners called');
        const toggleBtn = document.getElementById('chatbot-toggle');
        const closeBtn = document.getElementById('chatbot-close');
        const sendBtn = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input');
        const emojiBtn = document.getElementById('chatbot-emoji');
        const emojiPicker = document.getElementById('chatbot-emoji-picker');
        
        console.log('[chatbot] Elements found:', {
            toggleBtn: !!toggleBtn,
            closeBtn: !!closeBtn,
            sendBtn: !!sendBtn,
            input: !!input,
            emojiBtn: !!emojiBtn,
            emojiPicker: !!emojiPicker
        });
        
        if (!toggleBtn || !closeBtn || !sendBtn || !input || !emojiBtn || !emojiPicker) {
            console.error('[chatbot] Failed to find required chatbot elements');
            return;
        }

        toggleBtn.addEventListener('click', () => {
            console.log('[chatbot] Toggle button clicked!');
            this.toggleChat();
        });
        console.log('[chatbot] Toggle button listener attached');
        
        let hoverTimer = null;
        toggleBtn.addEventListener('mouseenter', () => {
            if (!this.isOpen) {
                hoverTimer = setTimeout(() => this.showMiniQuickActions(), 300);
            }
        });
        toggleBtn.addEventListener('mouseleave', () => {
            if (hoverTimer) clearTimeout(hoverTimer);
            setTimeout(() => this.hideMiniQuickActions(), 200);
        });
        
        closeBtn.addEventListener('click', () => this.closeChat());
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Event delegation for quick-action buttons
        const chatWindow = document.getElementById('chatbot-window');
        if (chatWindow) {
            chatWindow.addEventListener('click', (e) => {
                const btn = e.target.closest('.inline-quick-action, .quick-action-btn');
                if (btn && btn.dataset.action) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleQuickAction(btn.dataset.action, btn.dataset);
                }
            });
        }

        // Global document-level handler for dynamically inserted buttons
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn || !btn.dataset.action) return;
            
            console.log('Button clicked with action:', btn.dataset.action);
            
            const chatContainer = document.querySelector('.chatbot-container');
            if (!chatContainer || !chatContainer.contains(btn)) {
                console.log('Button not in chat container');
                return;
            }

            // Check if button is disabled
            if (btn.disabled) {
                console.log('Button is disabled');
                return;
            }

            console.log('Proceeding with action:', btn.dataset.action);
            e.preventDefault();
            e.stopPropagation();
            
            const action = btn.dataset.action;
            
            // Handle confirm_booking
            if (action === 'confirm_booking') {
                this.handleConfirmBooking(btn);
                return;
            }

            // Handle navigate
            if (action === 'navigate') {
                const href = btn.dataset.href || btn.getAttribute('href');
                if (href) {
                    setTimeout(() => { window.location.href = href; }, 250);
                }
                return;
            }
        }.bind(this)); // Bind 'this' context

        // Emoji picker logic
        emojiBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (emojiPicker.style.display === 'block') {
                emojiPicker.style.display = 'none';
            } else {
                this.showEmojiPicker(emojiPicker, input);
            }
        });
        
        document.addEventListener('click', (e) => {
            try {
                if (emojiPicker && !emojiPicker.contains(e.target) && e.target !== emojiBtn && !emojiBtn.contains(e.target)) {
                    emojiPicker.style.display = 'none';
                }
            } catch (err) {
                console.error('Error hiding emoji picker:', err);
            }

            try {
                const mini = document.getElementById('chatbot-mini-actions');
                const toggle = document.getElementById('chatbot-toggle');
                if (mini && toggle && !mini.contains(e.target) && !toggle.contains(e.target)) {
                    mini.style.display = 'none';
                }
            } catch (err) {
                console.error('Error hiding mini actions:', err);
            }
        });
    }
    
    showEmojiPicker(emojiPicker, input) {
        let html = `
            <div style="padding:8px;">
                <input type="text" id="emoji-search" placeholder="🔍 Search emojis..." 
                    style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;margin-bottom:8px;font-size:14px;outline:none;">
                <div style="display:flex;gap:4px;margin-bottom:8px;border-bottom:1px solid #eee;padding-bottom:6px;overflow-x:auto;">
        `;
        
        Object.keys(emojiCategories).forEach((cat, idx) => {
            html += `<button type="button" class="emoji-category-tab" data-category="${cat}" 
                style="padding:6px 10px;border:none;background:${idx === 0 ? '#667eea' : '#f0f0f0'};
                color:${idx === 0 ? 'white' : '#333'};border-radius:6px;cursor:pointer;font-size:12px;white-space:nowrap;flex-shrink:0;">
                ${cat}</button>`;
        });
        
        html += `</div><div id="emoji-grid" style="display:flex;flex-wrap:wrap;gap:4px;max-height:200px;overflow-y:auto;"></div></div>`;
        
        emojiPicker.innerHTML = html;
        emojiPicker.style.display = 'block';

        const emojiGrid = emojiPicker.querySelector('#emoji-grid');
        const searchInput = emojiPicker.querySelector('#emoji-search');
        const tabs = emojiPicker.querySelectorAll('.emoji-category-tab');
        
        let currentCategory = 'Smileys';
        let allEmojis = [];
        
        Object.values(emojiCategories).forEach(arr => allEmojis.push(...arr));
        
        const renderEmojis = (emojis) => {
            emojiGrid.innerHTML = '';
            emojis.forEach(emoji => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.textContent = emoji;
                btn.style.cssText = 'font-size:24px;padding:6px;background:none;border:none;cursor:pointer;border-radius:4px;transition:background 0.2s;';
                btn.onmouseover = () => btn.style.background = '#f0f0f0';
                btn.onmouseout = () => btn.style.background = 'none';
                btn.onclick = () => {
                    input.value += emoji;
                    input.focus();
                    const icon = document.getElementById('chatbot-emoji-icon');
                    if (icon) {
                        icon.textContent = emoji;
                        setTimeout(() => icon.textContent = '😊', 2000);
                    }
                };
                emojiGrid.appendChild(btn);
            });
        };
        
        renderEmojis(emojiCategories[currentCategory]);
        
        tabs.forEach(tab => {
            tab.onclick = () => {
                const category = tab.dataset.category;
                currentCategory = category;
                searchInput.value = '';
                
                tabs.forEach(t => {
                    t.style.background = t === tab ? '#667eea' : '#f0f0f0';
                    t.style.color = t === tab ? 'white' : '#333';
                });
                
                renderEmojis(emojiCategories[category]);
            };
        });
        
        searchInput.oninput = (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query) {
                renderEmojis(emojiCategories[currentCategory]);
                return;
            }
            
            const filtered = allEmojis.filter(emoji => emoji.includes(query));
            renderEmojis(filtered.length > 0 ? filtered : allEmojis.slice(0, 50));
        };
        
        searchInput.focus();
    }
    
    toggleChat() {
        console.log('[chatbot] toggleChat called, current isOpen:', this.isOpen);
        this.isOpen = !this.isOpen;
        const window = document.getElementById('chatbot-window');
        console.log('[chatbot] Chat window element:', window);
        console.log('[chatbot] Setting isOpen to:', this.isOpen);
        
        if (window) {
            window.classList.toggle('open', this.isOpen);
            console.log('[chatbot] Window classes after toggle:', window.className);
            
            if (this.isOpen) {
                const input = document.getElementById('chatbot-input');
                if (input) {
                    input.focus();
                    console.log('[chatbot] Input focused');
                }
            }
        } else {
            console.error('[chatbot] Chat window element not found!');
        }
    }
    
    closeChat() {
        this.isOpen = false;
        const window = document.getElementById('chatbot-window');
        if (window) {
            window.classList.remove('open');
        }
    }
    
    greetUser() {
        setTimeout(() => {
            const greeting = this.userEmail 
                ? "Hi! I'm here to help you book rooms. Just tell me what you need!"
                : "Hi! I can help you find and book rooms. What do you need today?";

            this.addMessage(greeting, 'bot');
            
            setTimeout(() => {
                this.showQuickActions();
            }, 500);
        }, 1000);
    }
    
    showQuickActions() {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer) return;

        const actionsHTML = `
            <div class="chat-message bot" id="quick-actions">
                <div class="quick-actions-container">
                    <div class="quick-actions-label">Quick Actions</div>
                    <div class="quick-actions-grid">
                        <button class="quick-action-btn" data-action="browse">
                            <span class="text">Find Available Rooms</span>
                        </button>
                        <button class="quick-action-btn" data-action="book">
                            <span class="text">Book a Room</span>
                        </button>
                        <button class="quick-action-btn" data-action="mybookings">
                            <span class="text">My Bookings</span>
                        </button>
                        <button class="quick-action-btn" data-action="help">
                            <span class="text">Help & Guide</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.insertAdjacentHTML('beforeend', actionsHTML);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    showMiniQuickActions() {
        const mini = document.getElementById('chatbot-mini-actions');
        if (!mini) return;
        
        mini.innerHTML = `
            <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
                <button class="quick-action-btn" data-action="browse" style="min-width:140px;">
                    <span class="text">Find Rooms</span>
                </button>
                <button class="quick-action-btn" data-action="book" style="min-width:140px;">
                    <span class="text">Book a Room</span>
                </button>
            </div>
        `;
        mini.style.display = 'block';
    }

    hideMiniQuickActions() {
        const mini = document.getElementById('chatbot-mini-actions');
        if (mini) mini.style.display = 'none';
    }
    
    async handleQuickAction(action, dataset = {}) {
        const actionsEl = document.getElementById('quick-actions');
        if (actionsEl) {
            actionsEl.remove();
        }
        
        if (!this.isOpen) this.toggleChat();
        
        switch(action) {
            case 'browse':
                this.addMessage('Find available rooms', 'user');
                this.sendQuickQuery('Show available rooms').catch(() => {});
                break;
                
            case 'book':
                this.addMessage('Book a room', 'user');
                this.sendQuickQuery('I want to book a room').catch(() => {});
                break;
                
            case 'mybookings':
                this.addMessage('My bookings', 'user');
                this.sendQuickQuery('Show my bookings').catch(() => {});
                break;
                
            case 'help':
                this.addMessage('Help & guide', 'user');
                this.sendQuickQuery('How do I book a room?').catch(() => {});
                break;
                
            case 'navigate':
                const href = (dataset && (dataset.href || dataset['href'])) || null;
                if (href) {
                    setTimeout(() => { window.location.href = href; }, 250);
                }
                break;
        }
    }
    
    async handleConfirmBooking(btn) {
        console.log('handleConfirmBooking called');
        btn.disabled = true;
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<span style="display:flex;align-items:center;gap:8px;"><span class="spinner" style="border:2px solid rgba(255,255,255,0.3);border-top-color:white;border-radius:50%;width:14px;height:14px;animation:spin 0.6s linear infinite;"></span>Confirming...</span>';
        
        this.addMessage('Confirm booking', 'user');
        this.showTypingIndicator();
        
        try {
            const response = await fetch(`${this.chatbotApiUrl}/confirm_booking/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ 
                    session_id: this.sessionId, 
                    email: this.userEmail 
                })
            });

            const data = await response.json();
            this.hideTypingIndicator();

            if (data.session_id && data.session_id !== this.sessionId) {
                this.saveSessionId(data.session_id);
            }

            if (response.ok) {
                const reply = data.reply || data.message || JSON.stringify(data);
                this.addMessage(reply, 'bot');
            } else {
                const err = data.error || JSON.stringify(data);
                this.addMessage(`Sorry, I couldn't confirm the booking: ${err}`, 'bot');
            }
        } catch (err) {
            console.error('Confirm booking error:', err);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I could not confirm the booking right now. Please try again.', 'bot');
        } finally {
            try { 
                btn.disabled = false; 
                btn.innerHTML = originalHTML; 
            } catch (e) {
                console.error('Error resetting button:', e);
            }
        }
    }
    
    addMessage(text, sender = 'user', isHtml = false) {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer) return;

        console.log('Adding message:', { sender, isHtml, textLength: text.length });

        const time = new Date().toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit' 
        });
        
        // If isHtml is true, render the text as HTML directly
        const content = isHtml ? text : this.formatMessage(text);
        
        if (isHtml) {
            console.log('Rendering HTML content');
        }
        
        const messageHTML = `
            <div class="chat-message ${sender}">
                <div class="message-bubble">
                    ${content}
                    <span class="message-time">${time}</span>
                </div>
            </div>
        `;
        
        messagesContainer.insertAdjacentHTML('beforeend', messageHTML);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        this.messages.push({ text, sender, time });
    }
    
    renderActions(actions) {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer || !Array.isArray(actions) || actions.length === 0) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'chat-message bot';
        const inner = document.createElement('div');
        inner.className = 'message-bubble';

        const actionsContainer = document.createElement('div');
        actionsContainer.style.marginTop = '8px';
        actionsContainer.style.display = 'flex';
        actionsContainer.style.gap = '8px';
        actionsContainer.style.flexWrap = 'wrap';
        
        actions.forEach(a => {
            const btn = document.createElement('button');
            btn.className = 'inline-quick-action';
            btn.type = 'button';
            btn.textContent = a.label || (a.type || 'Action');
            btn.dataset.action = a.type || '';
            if (a.href) btn.dataset.href = a.href;
            
            // Special styling for confirm_booking button
            if (a.type === 'confirm_booking') {
                btn.style.cssText = 'padding:10px 20px;border-radius:8px;border:none;background:linear-gradient(135deg, #10b981 0%, #059669 100%);color:white;cursor:pointer;font-size:14px;font-weight:600;transition:all 0.2s;pointer-events:auto;z-index:100;';
                btn.onmouseover = () => btn.style.background = 'linear-gradient(135deg, #059669 0%, #047857 100%)';
                btn.onmouseout = () => btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            } else {
                btn.style.cssText = 'padding:10px 16px;border-radius:6px;border:1px solid #667eea;background:#667eea;color:white;cursor:pointer;font-size:14px;font-weight:500;transition:all 0.2s;';
                btn.onmouseover = () => btn.style.background = '#5568d3';
                btn.onmouseout = () => btn.style.background = '#667eea';
            }
            
            actionsContainer.appendChild(btn);
        });

        inner.appendChild(actionsContainer);
        wrapper.appendChild(inner);
        messagesContainer.appendChild(wrapper);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    renderSlotSummary(slots, confidences) {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer || !slots) return;

        const hasSlots = Object.values(slots).some(v => v);
        if (!hasSlots) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'chat-message bot slot-summary';
        const inner = document.createElement('div');
        inner.className = 'message-bubble';
        inner.style.background = '#f8f9fa';
        inner.style.border = '1px solid #e9ecef';

        const title = document.createElement('div');
        title.style.fontSize = '13px';
        title.style.fontWeight = '600';
        title.style.marginBottom = '8px';
        title.style.color = '#495057';
        title.textContent = 'Detected details:';
        inner.appendChild(title);

        const list = document.createElement('div');
        list.style.display = 'flex';
        list.style.gap = '8px';
        list.style.flexWrap = 'wrap';

        Object.keys(slots).forEach(k => {
            const v = slots[k];
            if (!v) return;
            
            const pill = document.createElement('div');
            pill.style.padding = '8px 12px';
            pill.style.border = '1px solid #dee2e6';
            pill.style.borderRadius = '16px';
            pill.style.background = '#ffffff';
            pill.style.fontSize = '13px';
            pill.style.display = 'flex';
            pill.style.alignItems = 'center';
            pill.style.gap = '8px';
            
            const label = document.createElement('span');
            label.textContent = `${k.replace(/_/g,' ')}: ${v}`;
            label.style.fontWeight = '500';
            pill.appendChild(label);

            const edit = document.createElement('button');
            edit.textContent = 'Edit';
            edit.style.fontSize = '11px';
            edit.style.padding = '4px 8px';
            edit.style.border = '1px solid #667eea';
            edit.style.borderRadius = '4px';
            edit.style.background = 'white';
            edit.style.color = '#667eea';
            edit.style.cursor = 'pointer';
            edit.style.fontWeight = '600';
            edit.style.transition = 'all 0.2s';
            
            edit.onmouseover = () => {
                edit.style.background = '#667eea';
                edit.style.color = 'white';
            };
            edit.onmouseout = () => {
                edit.style.background = 'white';
                edit.style.color = '#667eea';
            };
            
            edit.onclick = async () => {
                const newVal = prompt(`Edit ${k.replace(/_/g, ' ')}:`, v);
                if (newVal === null || newVal === v) return;
                
                try {
                    this.showTypingIndicator();
                    const resp = await fetch(`${this.chatbotApiUrl}/chat/`, {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json', 
                            'X-CSRFToken': this.getCsrfToken() 
                        },
                        body: JSON.stringify({ 
                            update_slots: { [k]: newVal }, 
                            session_id: this.sessionId, 
                            email: this.userEmail,
                            message: ''
                        })
                    });
                    
                    const data = await resp.json();
                    this.hideTypingIndicator();
                    
                    if (resp.ok) {
                        if (data.reply_text) this.addMessage(data.reply_text, 'bot');
                        if (data.slots) this.renderSlotSummary(data.slots, data.slot_confidences);
                        if (Array.isArray(data.actions) && data.actions.length) this.renderActions(data.actions);
                    } else {
                        this.addMessage('Failed to update details.', 'bot');
                    }
                } catch (err) {
                    this.hideTypingIndicator();
                    console.error('Update slot failed', err);
                    this.addMessage('Failed to update details.', 'bot');
                }
            };

            pill.appendChild(edit);
            list.appendChild(pill);
        });

        inner.appendChild(list);
        wrapper.appendChild(inner);
        messagesContainer.appendChild(wrapper);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    formatMessage(text) {
        let formatted = text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');

        if (window.twemoji) {
            try {
                formatted = window.twemoji.parse(formatted, {
                    folder: 'svg', 
                    ext: '.svg'
                });
            } catch (err) {
                console.error('Twemoji parsing error:', err);
            }
        }
        return formatted;
    }
    
    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer) return;

        const typingHTML = `
            <div class="chat-message bot" id="typing-indicator">
                <div class="message-bubble">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.insertAdjacentHTML('beforeend', typingHTML);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    async sendMessage() {
        const input = document.getElementById('chatbot-input');
        const sendBtn = document.getElementById('chatbot-send');
        if (!input || !sendBtn) return;

        const message = input.value.trim();
        
        if (!message) return;
        
        this.addMessage(message, 'user');
        input.value = '';
        
        input.disabled = true;
        sendBtn.disabled = true;
        
        this.showTypingIndicator();
        
        try {
            const response = await fetch(`${this.chatbotApiUrl}/chat/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    message: message,
                    email: this.userEmail,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();
            this.hideTypingIndicator();

            if (data.session_id && data.session_id !== this.sessionId) {
                this.saveSessionId(data.session_id);
            }

            if (response.ok) {
                const replyText = data.reply_text || data.reply || '';
                const replyHtml = data.reply_html || null;
                
                // If we have HTML content, render it as HTML
                if (replyHtml) {
                    this.addMessage(replyHtml, 'bot', true);
                } else if (replyText) {
                    this.addMessage(replyText, 'bot');
                }
                
                if (data.slots) this.renderSlotSummary(data.slots, data.slot_confidences);
                
                if (Array.isArray(data.actions) && data.actions.length) {
                    this.renderActions(data.actions);
                }
            } else {
                const err = data.error || JSON.stringify(data);
                this.addMessage(`Sorry, I encountered an error: ${err}`, 'bot');
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            this.addMessage(
                `Sorry, I'm having trouble connecting to the server. Please try again later.`,
                'bot'
            );
        } finally {
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }
    }

    async sendQuickQuery(message) {
        this.showTypingIndicator();

        try {
            const response = await fetch(`${this.chatbotApiUrl}/chat/`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ 
                    message: message, 
                    email: this.userEmail,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();
            this.hideTypingIndicator();

            if (data.session_id && data.session_id !== this.sessionId) {
                this.saveSessionId(data.session_id);
            }

            if (response.ok) {
                const replyText = data.reply_text || data.reply || '';
                const replyHtml = data.reply_html || null;
                
                // If we have HTML content, render it as HTML
                if (replyHtml) {
                    this.addMessage(replyHtml, 'bot', true);
                } else if (replyText) {
                    this.addMessage(replyText, 'bot');
                }
                
                if (data.slots) this.renderSlotSummary(data.slots, data.slot_confidences);
                if (Array.isArray(data.actions) && data.actions.length) this.renderActions(data.actions);

                return replyText || replyHtml;
            } else {
                const err = data.error || JSON.stringify(data);
                this.addMessage(`Sorry, I encountered an error: ${err}`, 'bot');
                throw new Error(err);
            }
        } catch (error) {
            console.error('Quick query error:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I could not reach the chatbot service right now.', 'bot');
            throw error;
        }
    }

    getCsrfToken() {
        const name = 'csrftoken';
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
}

// Auto-initialization removed - now initialized by inline script in chatbot_widget.html
// This prevents conflicts and ensures proper initialization timing
console.log('[chatbot.js] Script loaded, ChatbotWidget class defined');
