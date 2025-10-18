// Apply theme immediately (update the link href and store in localStorage).
function applyThemeClient(themeName, persistToServer = true) {
  // swap stylesheet href
  var link = document.getElementById("themeStylesheet");
  if (link) {
    link.href = "/static/styles/themes/" + themeName + ".css";
  }
  // persist locally for unauthenticated users / immediate future visits
  try {
    localStorage.setItem("theme", themeName);
  } catch (e) {
    /* ignore */
  }

  if (persistToServer) {
    // notify backend to persist to session and DB (if logged-in)
    fetch("/set_theme", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme: themeName }),
    })
      .then((res) => res.json())
      .then((res) => {
        if (!res || res.status !== "success") {
          console.warn("Theme persist failed", res);
        }
      })
      .catch((err) => console.warn("Theme persist network error", err));
  }
}

// Example: hook up theme select on the settings page
document.addEventListener("DOMContentLoaded", function () {
  var select = document.getElementById("themeSelect");
  if (!select) return;
  select.addEventListener("change", function () {
    applyThemeClient(select.value, true);
  });
});
