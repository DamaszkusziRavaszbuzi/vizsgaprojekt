// menuToggle.js: accessible mobile side navigation toggling.
// Implements open/close behavior, focus management and escape-to-close.

(function () {
  const menuToggle = document.getElementById("menuToggle");
  const sidenav = document.getElementById("sidenav");
  const overlay = document.getElementById("overlay");
  let lastFocused = null;

  if (!sidenav || !menuToggle || !overlay) return;

  function initState() {
    // Hide the sidenav on mobile by default and set ARIA attributes accordingly
    sidenav.classList.add("mobile-hidden");
    sidenav.classList.remove("open");
    overlay.classList.remove("show");
    overlay.setAttribute("aria-hidden", "true");
    menuToggle.setAttribute("aria-expanded", "false");
  }

  function openMenu() {
    // Open sidenav and move focus to first link for keyboard users
    sidenav.classList.add("open");
    sidenav.classList.remove("mobile-hidden");
    overlay.classList.add("show");
    overlay.setAttribute("aria-hidden", "false");
    menuToggle.setAttribute("aria-expanded", "true");
    lastFocused = document.activeElement;
    const firstLink = sidenav.querySelector("a");
    if (firstLink) firstLink.focus();
  }

  function closeMenu() {
    sidenav.classList.remove("open");
    sidenav.classList.add("mobile-hidden");
    overlay.classList.remove("show");
    overlay.setAttribute("aria-hidden", "true");
    menuToggle.setAttribute("aria-expanded", "false");
    // Restore focus to the element that opened the menu
    if (lastFocused) lastFocused.focus();
  }

  function toggleMenu() {
    const isOpen = sidenav.classList.contains("open");
    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  }

  menuToggle.addEventListener("click", function (e) {
    e.preventDefault();
    toggleMenu();
  });

  // Close when clicking overlay or a link inside the nav
  overlay.addEventListener("click", function () {
    closeMenu();
  });

  sidenav.addEventListener("click", function (e) {
    if (e.target && e.target.tagName === "A") {
      closeMenu();
    }
  });

  // ESC closes the menu for keyboard users
  window.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (sidenav.classList.contains("open")) closeMenu();
    }
  });

  // Reset to initial state on resize to avoid inconsistent states between desktop/mobile
  window.addEventListener("resize", function () {
    initState();
  });

  initState();
})();
