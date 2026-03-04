/* LearnCentre - Main Pages (Public) — WebSiteFront */

document.addEventListener('DOMContentLoaded', function() {
    const html = document.documentElement;
    const themeBtn = document.getElementById('themeToggle') || document.getElementById('themeTogglePublic');
    const themeBall = document.getElementById('themeBall') || document.getElementById('themeBallPublic');

    function setTheme(theme, showToast) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        if (themeBall) {
            var darkIcon = themeBall.querySelector('.theme-nav-icon-dark');
            var lightIcon = themeBall.querySelector('.theme-nav-icon-light');
            if (darkIcon || lightIcon) {
                if (darkIcon) darkIcon.style.display = theme === 'dark' ? 'flex' : 'none';
                if (lightIcon) lightIcon.style.display = theme === 'light' ? 'flex' : 'none';
            } else {
                themeBall.textContent = theme === 'light' ? '☀️' : '🌙';
            }
        }

        if (showToast) {
            const toast = document.createElement('div');
            toast.className = 'theme-toast-main';
            toast.textContent = theme === 'dark' ? 'Тёмная тема' : 'Светлая тема';
            toast.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:12px 20px;background:var(--sur);border:1px solid var(--brd);border-radius:12px;z-index:9999;font-size:0.9rem;color:var(--txt);';
            document.body.appendChild(toast);
            setTimeout(function() { toast.remove(); }, 2000);
        }
    }

    var saved = localStorage.getItem('theme') || 'light';
    setTheme(saved, false);

    if (themeBtn) {
        themeBtn.addEventListener('click', function() {
            var next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            setTheme(next, true);
        });
    }

    var burger = document.getElementById('navBurger');
    var mobile = document.getElementById('navMobile');
    if (burger && mobile) {
        burger.addEventListener('click', function() { mobile.classList.toggle('open'); });
        mobile.querySelectorAll('a').forEach(function(a) {
            a.addEventListener('click', function() { mobile.classList.remove('open'); });
        });
    }
});
