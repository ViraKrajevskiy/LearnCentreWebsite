(function() {
    function initInvite() {
        var html = document.documentElement;
        var btn = document.getElementById('inviteBgToggle');
        var icon = document.getElementById('inviteBgIcon');

        /* Смена темы фона (светлый/тёмный) */
        if (btn) {
            var saved = localStorage.getItem('inviteBg') || 'default';
            if (saved === 'white') {
                html.setAttribute('data-invite-bg', 'white');
                if (icon) {
                    icon.className = 'bi bi-moon-stars';
                    icon.setAttribute('aria-label', 'Тёмный фон');
                }
                btn.title = 'Тёмный фон';
            } else {
                html.removeAttribute('data-invite-bg');
                if (icon) {
                    icon.className = 'bi bi-sun';
                    icon.setAttribute('aria-label', 'Белый фон');
                }
                btn.title = 'Белый фон';
            }
            btn.addEventListener('click', function() {
                var isWhite = html.getAttribute('data-invite-bg') === 'white';
                if (isWhite) {
                    html.removeAttribute('data-invite-bg');
                    localStorage.setItem('inviteBg', 'default');
                    if (icon) icon.className = 'bi bi-sun';
                    btn.title = 'Белый фон';
                } else {
                    html.setAttribute('data-invite-bg', 'white');
                    localStorage.setItem('inviteBg', 'white');
                    if (icon) icon.className = 'bi bi-moon-stars';
                    btn.title = 'Тёмный фон';
                }
            });
        }

        /* Параллакс: слой фона слегка двигается при наведении */
        var layer = document.getElementById('inviteParallaxLayer');
        if (layer) {
            var w = window.innerWidth;
            var h = window.innerHeight;
            var mouseX = w / 2;
            var mouseY = h / 2;
            var currentX = 0;
            var currentY = 0;
            var raf = null;
            var strength = 18;

            function updateParallax() {
                var targetX = (mouseX / w - 0.5) * strength;
                var targetY = (mouseY / h - 0.5) * strength;
                currentX += (targetX - currentX) * 0.07;
                currentY += (targetY - currentY) * 0.07;
                layer.style.transform = 'translate(' + currentX + 'px, ' + currentY + 'px)';
                raf = requestAnimationFrame(updateParallax);
            }

            document.addEventListener('mousemove', function(e) {
                mouseX = e.clientX;
                mouseY = e.clientY;
                if (!raf) raf = requestAnimationFrame(updateParallax);
            });

            document.addEventListener('mouseleave', function() {
                mouseX = w / 2;
                mouseY = h / 2;
            });

            updateParallax();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initInvite);
    } else {
        initInvite();
    }
})();
