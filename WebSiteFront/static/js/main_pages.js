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
                themeBall.innerHTML = theme === 'light' ?
                    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>' :
                    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
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
