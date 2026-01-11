// styleLoader.js: small snippet executed early to set preferred theme from localStorage.
// It populates window.__preferredTheme so other scripts can use it synchronously if needed.

(function () {
  try {
    var stored = localStorage.getItem("theme");
    if (stored) {
      window.__preferredTheme = stored;
    } else {
      window.__preferredTheme = null;
    }
  } catch (e) {
    // Accessing localStorage can throw (e.g. in some privacy modes), so fall back gracefully
    window.__preferredTheme = null;
  }
})();
