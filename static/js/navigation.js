// Navigation functionality
class NavigationManager {
    constructor() {
        this.initializeNavigation();
    }
    
    initializeNavigation() {
        // Mobile menu toggle
        const mobileToggle = document.getElementById('mobile-toggle');
        const navLinks = document.querySelector('.nav-links');
        
        if (mobileToggle && navLinks) {
            mobileToggle.addEventListener('click', () => {
                navLinks.classList.toggle('mobile-open');
            });
        }
        
        // Active link highlighting
        this.highlightActiveLink();
    }
    
    highlightActiveLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new NavigationManager();
});
