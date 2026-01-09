function applyThemeClient(themeName, persistToServer = true) {
  var link = document.getElementById("themeStylesheet");
  if (link) {
    link.href = "/static/styles/themes/" + themeName + ".css";
  }

  try {
    localStorage.setItem("theme", themeName);
  } catch (e) {}

  if (persistToServer) {
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
