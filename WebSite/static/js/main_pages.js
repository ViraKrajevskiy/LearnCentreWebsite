/* LearnCentre - Main Pages (Public) */

document.addEventListener('DOMContentLoaded', function() {
    const html = document.documentElement;
    const themeBtn = document.getElementById('themeTogglePublic');
    const themeLabel = document.getElementById('themeLabelPublic');

    function setTheme(theme, showToast) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        if (themeLabel) themeLabel.textContent = theme === 'light' ? 'Тёмная' : 'Светлая';
        if (showToast) {
            const toast = document.createElement('div');
            toast.className = 'theme-toast-main';
            toast.textContent = theme === 'dark' ? 'Тёмная тема' : 'Светлая тема';
            toast.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:12px 20px;background:var(--mp-card);border:1px solid var(--mp-border);border-radius:12px;z-index:9999;font-size:0.9rem;animation:fadeIn 0.3s ease;';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2000);
        }
    }

    const saved = localStorage.getItem('theme') || 'light';
    setTheme(saved, false);

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            setTheme(next, true);
        });
    }

    // Mobile menu
    const burger = document.getElementById('navBurger');
    const mobile = document.getElementById('navMobile');
    if (burger && mobile) {
        burger.addEventListener('click', () => mobile.classList.toggle('open'));
        mobile.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', () => mobile.classList.remove('open'));
        });
    }

    // Карусель «Наши преимущества»
    const advantagesCarousel = document.getElementById('advantagesCarousel');
    const advantagesPrev = document.getElementById('advantagesPrev');
    const advantagesNext = document.getElementById('advantagesNext');
    if (advantagesCarousel && advantagesPrev && advantagesNext) {
        const getScrollAmount = () => {
            const first = advantagesCarousel.querySelector('.advantage-card-strict');
            if (!first) return 344;
            const style = getComputedStyle(advantagesCarousel);
            const gap = parseFloat(style.gap) || 24;
            return first.offsetWidth + gap;
        };
        advantagesPrev.addEventListener('click', () => {
            advantagesCarousel.scrollBy({ left: -getScrollAmount(), behavior: 'smooth' });
        });
        advantagesNext.addEventListener('click', () => {
            advantagesCarousel.scrollBy({ left: getScrollAmount(), behavior: 'smooth' });
        });
    }

});
