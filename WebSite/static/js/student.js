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

    // Sidebar: скрыть/показать (десктоп) или открыть оверлей (мобильный)
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarClose = document.getElementById('sidebarClose');
    const SIDEBAR_COLLAPSED_KEY = 'sidebarCollapsed';

    function isDesktop() {
        return window.innerWidth >= 992;
    }

    function applySidebarCollapsed(collapsed) {
        if (collapsed) {
            document.body.classList.add('sidebar-collapsed');
            if (sidebarToggle) {
                sidebarToggle.setAttribute('title', 'Показать меню');
                sidebarToggle.setAttribute('aria-label', 'Показать меню');
            }
        } else {
            document.body.classList.remove('sidebar-collapsed');
            if (sidebarToggle) {
                sidebarToggle.setAttribute('title', 'Скрыть меню');
                sidebarToggle.setAttribute('aria-label', 'Скрыть/показать меню');
            }
        }
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            if (isDesktop()) {
                const collapsed = document.body.classList.toggle('sidebar-collapsed');
                localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? 'true' : 'false');
                applySidebarCollapsed(collapsed);
            } else {
                sidebar?.classList.add('open');
            }
        });
    }
    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => sidebar?.classList.remove('open'));
    }

    // Восстановить состояние «меню скрыто» на десктопе
    if (isDesktop() && localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true') {
        document.body.classList.add('sidebar-collapsed');
        applySidebarCollapsed(true);
    }
    window.addEventListener('resize', function() {
        if (!isDesktop()) {
            document.body.classList.remove('sidebar-collapsed');
            sidebar?.classList.remove('open');
        } else if (localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true') {
            document.body.classList.add('sidebar-collapsed');
            applySidebarCollapsed(true);
        }
    });

    // Подсветка только выбранного раздела: «Главная» (/student) — только при точном совпадении
    const currentPath = (window.location.pathname || '').replace(/\/$/, '') || '/';
    const studentRoot = '/student';
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = (item.getAttribute('href') || '').replace(/\/$/, '') || '';
        let active = false;
        if (href) {
            if (currentPath === href) {
                active = true;
            } else if (href !== studentRoot && href !== '/' && currentPath.startsWith(href + '/')) {
                active = true; // подстраница раздела (например урок внутри курса)
            }
        }
        item.classList.toggle('active', active);
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

    // Уведомления: загрузка, бейдж, выпадающий список
    var notificationsLoaded = false;
    var notificationsData = { notifications: [], unread_count: 0 };
    var notificationsBtn = document.getElementById('notificationsBtn');
    var notificationsBadge = document.getElementById('notificationsBadge');
    var notificationsDropdown = document.getElementById('notificationsDropdown');
    var notificationsList = document.getElementById('notificationsList');
    var notificationsEmpty = document.getElementById('notificationsEmpty');
    var notificationsMarkAllRead = document.getElementById('notificationsMarkAllRead');

    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        var name = 'csrftoken';
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var parts = cookies[i].trim().split('=');
            if (parts[0] === name) return decodeURIComponent(parts[1] || '');
        }
        return '';
    }

    function loadNotifications(callback) {
        fetch('/student/notifications/api/', { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                notificationsData = data;
                notificationsLoaded = true;
                if (notificationsBadge) {
                    var n = data.unread_count || 0;
                    notificationsBadge.textContent = n > 99 ? '99+' : n;
                    notificationsBadge.style.display = n > 0 ? 'inline-block' : 'none';
                }
                if (typeof callback === 'function') callback(data);
            })
            .catch(function() {
                if (notificationsList) notificationsList.innerHTML = '<div class="text-center text-secondary py-4 small">Не удалось загрузить</div>';
                if (typeof callback === 'function') callback({ notifications: [], unread_count: 0 });
            });
    }

    function renderNotificationsList() {
        var list = notificationsData.notifications || [];
        if (!notificationsList) return;
        if (list.length === 0) {
            notificationsList.innerHTML = '<div class="text-center text-secondary py-4 small">Нет уведомлений</div>';
            return;
        }
        var kinds = { news: 'Новость', homework: 'Домашнее задание', lesson_soon: 'Урок через 30 мин', lesson_started: 'Урок начался' };
        var html = '';
        list.forEach(function(n) {
            var kindLabel = kinds[n.kind] || n.kind;
            var cls = 'notification-item' + (n.is_read ? '' : ' unread');
            var link = (n.link && n.link.length) ? n.link : '#';
            var timeStr = n.created_at ? new Date(n.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
            html += '<a href="' + link + '" class="' + cls + '" data-id="' + (n.id || '') + '">';
            html += '<span class="notification-title">' + (n.title || '') + '</span>';
            html += '<div class="notification-meta">' + kindLabel + (timeStr ? ' · ' + timeStr : '') + '</div>';
            if (n.message) html += '<div class="notification-meta mt-1">' + (n.message.substring(0, 80) + (n.message.length > 80 ? '…' : '')) + '</div>';
            html += '</a>';
        });
        notificationsList.innerHTML = html;
    }

    function markReadAll() {
        var token = getCsrfToken();
        fetch('/student/notifications/read/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
            body: JSON.stringify({})
        }).then(function() { loadNotifications(renderNotificationsList); });
    }

    if (notificationsBtn && notificationsDropdown) {
        notificationsBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationsDropdown.classList.toggle('show');
            if (notificationsDropdown.classList.contains('show')) {
                if (!notificationsLoaded) loadNotifications(renderNotificationsList);
                else renderNotificationsList();
            }
        });
    }
    document.addEventListener('click', function() {
        if (notificationsDropdown && notificationsDropdown.classList) notificationsDropdown.classList.remove('show');
    });
    if (notificationsDropdown) notificationsDropdown.addEventListener('click', function(e) { e.stopPropagation(); });
    if (notificationsMarkAllRead) notificationsMarkAllRead.addEventListener('click', function(e) { e.preventDefault(); markReadAll(); });
    loadNotifications();
});
