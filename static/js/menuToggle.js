(function () {
  const menuToggle = document.getElementById("menuToggle");
  const sidenav = document.getElementById("sidenav");
  const overlay = document.getElementById("overlay");
  let lastFocused = null;

  if (!sidenav || !menuToggle || !overlay) return;

  function initState() {
    sidenav.classList.add("mobile-hidden");
    sidenav.classList.remove("open");
    overlay.classList.remove("show");
    overlay.setAttribute("aria-hidden", "true");
    menuToggle.setAttribute("aria-expanded", "false");
  }

  function openMenu() {
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

  overlay.addEventListener("click", function () {
    closeMenu();
  });

  sidenav.addEventListener("click", function (e) {
    if (e.target && e.target.tagName === "A") {
      closeMenu();
    }
  });

  window.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (sidenav.classList.contains("open")) closeMenu();
    }
  });

  window.addEventListener("resize", function () {
    initState();
  });

  initState();
})();
