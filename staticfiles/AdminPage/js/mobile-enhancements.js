// Mobile-First JavaScript Enhancements for RUPP Room Booking System

document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle Enhancement
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            const isExpanded = navbarCollapse.classList.contains('show');
            
            // Add smooth animation
            if (!isExpanded) {
                navbarCollapse.style.maxHeight = navbarCollapse.scrollHeight + 'px';
            } else {
                navbarCollapse.style.maxHeight = '0px';
            }
        });
    }

    // Touch-friendly Button Enhancements
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        // Add touch feedback
        button.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.95)';
        });
        
        button.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
    });

    // Improved Form Input Experience on Mobile
    const formInputs = document.querySelectorAll('input, select, textarea');
    formInputs.forEach(input => {
        // Prevent zoom on iOS for form inputs
        input.addEventListener('focus', function() {
            if (window.innerWidth < 768) {
                document.querySelector('meta[name=viewport]').setAttribute(
                    'content', 
                    'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
                );
            }
        });
        
        input.addEventListener('blur', function() {
            if (window.innerWidth < 768) {
                document.querySelector('meta[name=viewport]').setAttribute(
                    'content', 
                    'width=device-width, initial-scale=1.0, user-scalable=yes, minimum-scale=1.0, maximum-scale=5.0'
                );
            }
        });
    });

    // Swipe Gestures for Cards (Mobile)
    if (window.innerWidth < 768) {
        const cards = document.querySelectorAll('.card, .room-card, .service-card');
        cards.forEach(card => {
            let startX, startY, distX, distY;
            const threshold = 100; // Minimum distance for swipe
            
            card.addEventListener('touchstart', function(e) {
                const touch = e.changedTouches[0];
                startX = touch.pageX;
                startY = touch.pageY;
            });
            
            card.addEventListener('touchend', function(e) {
                const touch = e.changedTouches[0];
                distX = touch.pageX - startX;
                distY = touch.pageY - startY;
                
                // Check if it's a horizontal swipe
                if (Math.abs(distX) > Math.abs(distY) && Math.abs(distX) > threshold) {
                    if (distX > 0) {
                        // Swipe right - could trigger an action
                        card.style.transform = 'translateX(10px)';
                        setTimeout(() => {
                            card.style.transform = 'translateX(0)';
                        }, 200);
                    } else {
                        // Swipe left - could trigger an action
                        card.style.transform = 'translateX(-10px)';
                        setTimeout(() => {
                            card.style.transform = 'translateX(0)';
                        }, 200);
                    }
                }
            });
        });
    }

    // Responsive Table Enhancements
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        if (window.innerWidth < 768) {
            // Add horizontal scroll indicator
            const wrapper = table.closest('.table-responsive');
            if (wrapper) {
                wrapper.addEventListener('scroll', function() {
                    const scrollLeft = this.scrollLeft;
                    const scrollWidth = this.scrollWidth;
                    const clientWidth = this.clientWidth;
                    
                    // Add visual indicators for scrollable content
                    if (scrollLeft > 0) {
                        this.classList.add('scrolled-left');
                    } else {
                        this.classList.remove('scrolled-left');
                    }
                    
                    if (scrollLeft < scrollWidth - clientWidth) {
                        this.classList.add('scrolled-right');
                    } else {
                        this.classList.remove('scrolled-right');
                    }
                });
            }
        }
    });

    // Modal Enhancements for Mobile
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            // Prevent body scroll when modal is open
            document.body.style.overflow = 'hidden';
            
            // Focus on first input in modal
            const firstInput = modal.querySelector('input, select, textarea');
            if (firstInput && window.innerWidth > 768) {
                firstInput.focus();
            }
        });
        
        modal.addEventListener('hidden.bs.modal', function() {
            // Restore body scroll
            document.body.style.overflow = 'auto';
        });
    });

    // Enhanced Touch Interactions for Service/Room Cards
    const interactiveCards = document.querySelectorAll('.service-card, .room-card, .stat-card');
    interactiveCards.forEach(card => {
        card.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
            this.style.transition = 'transform 0.1s ease';
        });
        
        card.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
            setTimeout(() => {
                this.style.transition = '';
            }, 100);
        });
    });

    // Improved Date/Time Picker for Mobile
    const dateInputs = document.querySelectorAll('input[type="date"], input[type="time"], input[type="datetime-local"]');
    dateInputs.forEach(input => {
        if (window.innerWidth < 768) {
            // Add mobile-friendly styling
            input.style.fontSize = '16px';
            input.style.padding = '0.75rem';
        }
    });

    // Smart Form Validation Messages
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const invalidInputs = form.querySelectorAll(':invalid');
            if (invalidInputs.length > 0 && window.innerWidth < 768) {
                e.preventDefault();
                
                // Scroll to first invalid input
                invalidInputs[0].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
                
                // Focus on the first invalid input
                setTimeout(() => {
                    invalidInputs[0].focus();
                }, 300);
            }
        });
    });

    // Loading States for Buttons
    const submitButtons = document.querySelectorAll('button[type="submit"], .btn-submit');
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.form && this.form.checkValidity()) {
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                this.disabled = true;
                
                // Re-enable after 5 seconds as fallback
                setTimeout(() => {
                    this.disabled = false;
                    this.innerHTML = this.getAttribute('data-original-text') || 'Submit';
                }, 5000);
            }
        });
        
        // Store original text
        button.setAttribute('data-original-text', button.innerHTML);
    });

    // Orientation Change Handler
    window.addEventListener('orientationchange', function() {
        // Delay to ensure proper rendering after orientation change
        setTimeout(() => {
            // Trigger resize events for any responsive elements
            window.dispatchEvent(new Event('resize'));
            
            // Refresh any charts or complex layouts
            const refreshEvent = new CustomEvent('orientationChanged');
            document.dispatchEvent(refreshEvent);
        }, 100);
    });

    // Performance: Lazy load images
    const images = document.querySelectorAll('img[data-src]');
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        images.forEach(img => {
            img.src = img.dataset.src;
        });
    }

    // Connection Aware Features
    if ('connection' in navigator) {
        const connection = navigator.connection;
        
        if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
            // Reduce functionality for slow connections
            document.body.classList.add('slow-connection');
        }
    }

    console.log('Mobile-first JavaScript enhancements loaded successfully!');
});

// Utility Functions
function isMobile() {
    return window.innerWidth < 768;
}

function isTablet() {
    return window.innerWidth >= 768 && window.innerWidth < 1024;
}

function isDesktop() {
    return window.innerWidth >= 1024;
}

// Export utility functions for use in other scripts
window.RUPPMobile = {
    isMobile,
    isTablet,
    isDesktop
};
