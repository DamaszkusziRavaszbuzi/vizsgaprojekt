// themeChange.js: client-side theme application and persistence to server.
// applyThemeClient is used by settings.js and other UI code.

function applyThemeClient(themeName, persistToServer = true) {
  var link = document.getElementById("themeStylesheet");
  if (link) {
    // Change the stylesheet href to the selected theme file. Assumes theme CSS files are available on server.
    link.href = "/static/styles/themes/" + themeName + ".css";
  }

  try {
    // Save to localStorage so the theme persists across page reloads client-side
    localStorage.setItem("theme", themeName);
  } catch (e) {}

  if (persistToServer) {
    // Also persist choice on server to keep user's preference across devices (if logged in)
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

document.addEventListener("DOMContentLoaded", function () {
  var select = document.getElementById("themeSelect");
  if (!select) return;
  select.addEventListener("change", function () {
    applyThemeClient(select.value, true);
  });
});
