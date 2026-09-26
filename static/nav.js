(() => {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('navToggle');
    const close = document.getElementById('closeSidebar');
    const backdrop = document.getElementById('navBackdrop');
    const shell = document.getElementById('pageShell');
    const mobile = window.matchMedia('(max-width: 760px)');
    let collapsed = false;
    let opened = false;

    function sync() {
        document.body.classList.toggle('nav-collapsed', !mobile.matches && collapsed);
        document.body.classList.toggle('nav-open', mobile.matches && opened);
        backdrop.hidden = !mobile.matches || !opened;
        sidebar.inert = mobile.matches && !opened;
        shell.inert = mobile.matches && opened;
        toggle.setAttribute('aria-expanded', String(mobile.matches ? opened : !collapsed));
        toggle.setAttribute('aria-label', mobile.matches ? 'Открыть меню' : collapsed ? 'Развернуть меню' : 'Свернуть меню');
        if (mobile.matches && opened) {
            sidebar.setAttribute('role', 'dialog');
            sidebar.setAttribute('aria-modal', 'true');
        } else {
            sidebar.removeAttribute('role');
            sidebar.removeAttribute('aria-modal');
        }
    }
    function dismiss(returnFocus = true) {
        opened = false;
        sync();
        if (returnFocus) toggle.focus();
    }
    toggle.addEventListener('click', () => {
        if (mobile.matches) {
            opened = !opened;
            sync();
            if (opened) close.focus();
        } else {
            collapsed = !collapsed;
            sync();
        }
    });
    close.addEventListener('click', () => dismiss());
    backdrop.addEventListener('click', () => dismiss());
    sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
        if (mobile.matches) {
            dismiss(false);
            if (link.hash && link.pathname === window.location.pathname) {
                const target = document.getElementById(link.hash.slice(1));
                if (target) { target.setAttribute('tabindex', '-1'); target.focus({ preventScroll: true }); }
            }
        }
    }));
    document.addEventListener('keydown', event => {
        if (!mobile.matches || !opened) return;
        if (event.key === 'Escape') { dismiss(); return; }
        if (event.key !== 'Tab') return;
        const focusable = [...sidebar.querySelectorAll('a, button')].filter(item => item.getClientRects().length);
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    mobile.addEventListener('change', () => {
        const focusWasInside = sidebar.contains(document.activeElement);
        opened = false;
        sync();
        if (mobile.matches && focusWasInside) toggle.focus();
    });
    function activeLink() {
        if (window.location.pathname !== '/') return;
        const selected = window.location.hash === '#manual-entry' ? 'manual' : 'index';
        sidebar.querySelectorAll('.nav-link').forEach(link => {
            const active = link.dataset.page === selected;
            link.classList.toggle('active', active);
            if (active) link.setAttribute('aria-current', selected === 'manual' ? 'location' : 'page');
            else link.removeAttribute('aria-current');
        });
    }
    window.addEventListener('hashchange', activeLink);
    sync();
    activeLink();
})();
