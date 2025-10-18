(function () {
  // server-side injected theme (for logged in users) is rendered into this placeholder
  // We'll check localStorage first for unauthenticated users
  try {
    var stored = localStorage.getItem("theme");
    if (stored) {
      // by setting window.__preferredTheme we can later use it in the <link> below
      window.__preferredTheme = stored;
    } else {
      // if server injected theme exists it'll be set by template variable below
      window.__preferredTheme = null;
    }
  } catch (e) {
    window.__preferredTheme = null;
  }
})();
