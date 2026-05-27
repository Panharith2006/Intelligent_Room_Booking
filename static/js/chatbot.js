class ChatbotWidget {
    constructor() {
        this.isOpen = false;
        this.sessionId = this.loadSessionId();
        this.userEmail = this.getUserEmail();
        this.init();
    }

    init() {
        console.log('ChatbotWidget init started');
        this.attachEventListeners();
        setTimeout(() => this.addBotMessage('Hi! How can I help you with room bookings?'), 800);
    }

    getUserEmail() {
        const emailElement = document.querySelector('[data-user-email]');
        return emailElement ? emailElement.dataset.userEmail : 'guest';
    }

    loadSessionId() {
        let sid = localStorage.getItem('chatbot_session_id');
        if (!sid) {
            sid = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('chatbot_session_id', sid);
        }
        return sid;
    }

    attachEventListeners() {
        const toggleBtn = document.getElementById('chatbot-toggle');
        const sendBtn = document.getElementById('chatbot-send');
        const closeBtn = document.getElementById('chatbot-close');
        const input = document.getElementById('chatbot-input');

        console.log('=== CHATBOT DEBUG ===');
        console.log('toggleBtn element:', toggleBtn);
        console.log('toggleBtn computed style:', toggleBtn ? window.getComputedStyle(toggleBtn) : 'N/A');
        console.log('sendBtn:', sendBtn);
        console.log('closeBtn:', closeBtn);
        console.log('input:', input);

        if (!toggleBtn || !sendBtn || !closeBtn || !input) {
            console.error('❌ Missing required elements:', { toggleBtn, sendBtn, closeBtn, input });
            return;
        }

        console.log(' All elements found');

        // Test that listener works
        toggleBtn.addEventListener('click', () => {
            console.log(' TOGGLE BUTTON CLICKED - isOpen was:', this.isOpen);
            this.toggleChat();
        });
        closeBtn.addEventListener('click', () => {
            console.log(' CLOSE BUTTON CLICKED');
            this.toggleChat();
        });
        sendBtn.addEventListener('click', () => {
            console.log('✅ SEND BUTTON CLICKED');
            this.sendMessage();
        });
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
        });

        console.log('✅ All listeners attached');
    }

    toggleChat() {
        console.log('toggleChat() called, isOpen:', this.isOpen);
        this.isOpen = !this.isOpen;
        console.log('isOpen is now:', this.isOpen);
        
        const chatWindow = document.getElementById('chatbot-window');
        console.log('chatWindow element:', chatWindow);
        
        if (chatWindow) {
            console.log('Window classes before:', chatWindow.className);
            chatWindow.classList.toggle('open', this.isOpen);
            console.log('Window classes after:', chatWindow.className);
            
            if (this.isOpen) {
                const input = document.getElementById('chatbot-input');
                if (input) input.focus();
            }
        } else {
            console.error('❌ chatbot-window NOT FOUND!');
        }
    }

    addUserMessage(text) {
        const messagesDiv = document.getElementById('chatbot-messages');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user-message';
        msgDiv.textContent = text;
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    addBotMessage(text) {
        const messagesDiv = document.getElementById('chatbot-messages');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot-message';
        msgDiv.innerHTML = text.replace(/\n/g, '<br>');
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    showTyping() {
        const messagesDiv = document.getElementById('chatbot-messages');
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'message bot-message typing';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        messagesDiv.appendChild(typingDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    hideTyping() {
        const typing = document.getElementById('typing-indicator');
        if (typing) typing.remove();
    }

    async sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();

        if (!message) return;

        this.addUserMessage(message);
        input.value = '';
        input.disabled = true;

        this.showTyping();

        try {
            const response = await fetch('/chatbot/chat/', {
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
            this.hideTyping();

            if (response.ok) {
                const reply = data.reply_text || data.reply || 'No response';
                
                // Display main message
                this.addBotMessage(reply);
                
                // Display room details if available
                if (data.rooms && data.rooms.length > 0) {
                    this.displayRoomDetails(data.rooms);
                }
                
                // Display action buttons if available
                if (data.actions && data.actions.length > 0) {
                    this.displayActions(data.actions, data);
                }
            } else {
                this.addBotMessage('Error: ' + (data.error || 'Unknown error'));
            }
        } catch (err) {
            console.error('Chat error:', err);
            this.hideTyping();
            this.addBotMessage('Sorry, I could not connect to the server.');
        } finally {
            input.disabled = false;
            input.focus();
        }
    }

    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            document.cookie.split(';').forEach(cookie => {
                const trimmed = cookie.trim();
                if (trimmed.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(trimmed.substring(name.length + 1));
                }
            });
        }
        return cookieValue;
    }

    displayRoomDetails(rooms) {
        const messagesDiv = document.getElementById('chatbot-messages');
        
        rooms.forEach(room => {
            const roomCard = document.createElement('div');
            roomCard.className = 'message bot-message room-card';
            roomCard.style.cssText = 'background: #f0f4ff; border-left: 4px solid #667eea; margin-top: 10px; padding: 12px;';
            
            let equipmentHTML = '';
            if (room.equipment && room.equipment.length > 0) {
                equipmentHTML = `<p style="margin: 6px 0;"><strong>Equipment:</strong> ${Array.isArray(room.equipment) ? room.equipment.join(', ') : room.equipment}</p>`;
            }
            
            roomCard.innerHTML = `
                <div style="color: #2d3748; font-size: 0.95em;">
                    <p style="margin: 0 0 6px 0; font-weight: 600; color: #667eea;">📍 ${room.name}</p>
                    <p style="margin: 4px 0;"><strong>Room #:</strong> ${room.room_number || 'N/A'}</p>
                    <p style="margin: 4px 0;"><strong>Capacity:</strong> ${room.capacity || 'N/A'} people</p>
                    ${equipmentHTML}
                </div>
            `;
            
            messagesDiv.appendChild(roomCard);
        });
        
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    displayActions(actions, data) {
        const messagesDiv = document.getElementById('chatbot-messages');
        const actionContainer = document.createElement('div');
        actionContainer.className = 'message bot-message action-container';
        actionContainer.style.cssText = 'background: transparent; border: none; padding: 12px 0; display: flex; gap: 8px; flex-wrap: wrap;';
        
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = 'chatbot-action-button';
            button.style.cssText = `
                background: ${action.style === 'primary' ? '#667eea' : '#f0f4ff'};
                color: ${action.style === 'primary' ? '#fff' : '#667eea'};
                border: 1px solid #667eea;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 0.9em;
            `;
            button.textContent = action.label;
            
            button.addEventListener('mouseover', () => {
                button.style.opacity = '0.9';
                button.style.transform = 'scale(1.02)';
            });
            
            button.addEventListener('mouseout', () => {
                button.style.opacity = '1';
                button.style.transform = 'scale(1)';
            });
            
            button.addEventListener('click', async () => {
                console.log('Action clicked:', action.type);
                
                if (action.type === 'confirm_booking') {
                    await this.confirmBooking(data);
                }
            });
            
            actionContainer.appendChild(button);
        });
        
        messagesDiv.appendChild(actionContainer);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    async confirmBooking(data) {
        const input = document.getElementById('chatbot-input');
        input.disabled = true;
        
        this.showTyping();
        
        try {
            const response = await fetch('/chatbot/confirm_booking/', {
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
            
            const result = await response.json();
            this.hideTyping();
            
            if (response.ok) {
                const confirmMsg = result.reply_text || 'Booking confirmed!';
                this.addBotMessage(confirmMsg);
                
                // Show booking result details if available
                if (result.result && result.result.success) {
                    const successCard = document.createElement('div');
                    successCard.className = 'message bot-message booking-success';
                    successCard.style.cssText = 'background: #d4edda; border-left: 4px solid #28a745; padding: 12px;';
                    successCard.innerHTML = `
                        <div style="color: #155724; font-size: 0.95em;">
                            <p style="margin: 0; font-weight: 600;">✅ Booking Confirmed!</p>
                            <p style="margin: 4px 0;"><strong>Booking ID:</strong> ${result.result.booking_id || 'N/A'}</p>
                        </div>
                    `;
                    document.getElementById('chatbot-messages').appendChild(successCard);
                    document.getElementById('chatbot-messages').scrollTop = document.getElementById('chatbot-messages').scrollHeight;
                }
            } else {
                this.addBotMessage('Error confirming booking: ' + (result.error || 'Unknown error'));
            }
        } catch (err) {
            console.error('Booking confirmation error:', err);
            this.hideTyping();
            this.addBotMessage('Sorry, I could not confirm the booking. Please try again.');
        } finally {
            input.disabled = false;
            input.focus();
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    try {
        if (!window.chatbotWidget) {
            window.chatbotWidget = new ChatbotWidget();
            console.log('ChatbotWidget initialized');
        }
    } catch (err) {
        console.error('Failed to initialize ChatbotWidget:', err);
    }
});
