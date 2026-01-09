(function () {
  try {
    var stored = localStorage.getItem("theme");
    if (stored) {
      window.__preferredTheme = stored;
    } else {
      window.__preferredTheme = null;
    }
  } catch (e) {
    window.__preferredTheme = null;
  }
})();
