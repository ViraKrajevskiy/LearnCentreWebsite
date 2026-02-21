/* LearnCentre - Student Frontend JS */

function setTheme(nextTheme, showToast) {
    const html = document.documentElement;
    html.setAttribute('data-theme', nextTheme);
    localStorage.setItem('theme', nextTheme);
    
    const label = document.getElementById('themeLabel');
    if (label) {
        label.textContent = nextTheme === 'light' ? 'Тёмная' : 'Светлая';
    }
    
    if (showToast) {
        const existing = document.querySelector('.theme-toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = 'theme-toast';
        toast.textContent = nextTheme === 'dark' ? 'Тёмная тема включена' : 'Светлая тема включена';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2300);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const html = document.documentElement;
    const themeToggle = document.getElementById('themeToggle');
    const themeToggleTopbar = document.getElementById('themeToggleTopbar');

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme, false);

    function toggleTheme() {
        const current = html.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        setTheme(next, true);
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    if (themeToggleTopbar) {
        themeToggleTopbar.addEventListener('click', toggleTheme);
    }

    // Mobile sidebar
    const sidebar = document.getElementById('sidebar');
    const sidebarOpen = document.getElementById('sidebarOpen');
    const sidebarClose = document.getElementById('sidebarClose');

    if (sidebarOpen) {
        sidebarOpen.addEventListener('click', () => sidebar?.classList.add('open'));
    }
    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => sidebar?.classList.remove('open'));
    }

    // Mark active nav item based on current page
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = item.getAttribute('href') || '';
        if (href && (currentPath === href || currentPath.startsWith(href.replace(/\/$/, '') + '/'))) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Animate elements on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.stat-card, .card-ai, .animate-on-scroll, .anim-fade-up').forEach(el => {
        if (!el.classList.contains('animate-on-scroll') && !el.classList.contains('anim-fade-up')) {
            el.classList.add('animate-on-scroll');
        }
        observer.observe(el);
    });

    // Hero animate on load
    setTimeout(() => {
        document.querySelectorAll('.page-hero .anim-fade-up, .page-hero .animate-on-scroll').forEach(el => {
            el.classList.add('animate-in');
        });
    }, 80);
});
