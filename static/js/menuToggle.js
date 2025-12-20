// Put this file at ../static/js/menuToggle.js
// Toggles the mobile side menu and overlay. Closes the menu when a sidenav link is clicked.
// Ensures state resets when resizing back to desktop.

(function () {
  const BREAKPOINT = 768;
  const menuToggle = document.getElementById('menuToggle');
  const sidenav = document.getElementById('sidenav');
  const overlay = document.getElementById('overlay');

  if (!sidenav || !menuToggle || !overlay) return;

  // Initialize mobile hidden state if on small screen
  function initState() {
    if (window.innerWidth <= BREAKPOINT) {
      sidenav.classList.add('mobile-hidden');
      sidenav.classList.remove('open');
      overlay.classList.remove('show');
      overlay.setAttribute('aria-hidden', 'true');
    } else {
      // On desktop, show sidenav (remove mobile-hidden)
      sidenav.classList.remove('mobile-hidden');
      sidenav.classList.remove('open');
      overlay.classList.remove('show');
      overlay.setAttribute('aria-hidden', 'true');
    }
  }

  // Toggle handler
  function toggleMenu() {
    const isOpen = sidenav.classList.contains('open');
    if (isOpen) {
      sidenav.classList.remove('open');
      overlay.classList.remove('show');
      overlay.setAttribute('aria-hidden', 'true');
    } else {
      sidenav.classList.add('open');
      overlay.classList.add('show');
      overlay.setAttribute('aria-hidden', 'false');
    }
  }

  menuToggle.addEventListener('click', function (e) {
    e.preventDefault();
    toggleMenu();
  });

  overlay.addEventListener('click', function () {
    // close menu
    sidenav.classList.remove('open');
    overlay.classList.remove('show');
    overlay.setAttribute('aria-hidden', 'true');
  });

  // Close when a link inside the sidenav is clicked (mobile)
  sidenav.addEventListener('click', function (e) {
    if (e.target && e.target.tagName === 'A' && window.innerWidth <= BREAKPOINT) {
      sidenav.classList.remove('open');
      overlay.classList.remove('show');
      overlay.setAttribute('aria-hidden', 'true');
    }
  });

  // Reset state on resize
  let resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      initState();
    }, 150);
  });

  // initial
  initState();
})();
