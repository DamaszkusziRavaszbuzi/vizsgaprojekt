function showMessage(text, type = "success") {
  const el = document.getElementById("msg");
  el.textContent = text;
  el.className = "message " + (type === "error" ? "error" : "success");
  el.style.display = "block";
  setTimeout(() => {
    el.style.display = "none";
  }, 4000);
}

function loadUserInfo() {
  fetch("/get_user_info")
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        const el = document.getElementById("username");
        if (el) el.value = data.user.username || "";
      } else {
        showMessage(
          data.message || "Hiba a felhasználó adatainak betöltése közben",
          "error"
        );
      }
    })
    .catch(() => showMessage("Hálózati hiba", "error"));
}

function saveChanges() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  if (!username) {
    showMessage("A felhasználónév nem lehet üres", "error");
    return;
  }

  fetch("/update_user", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        showMessage("Beállítások mentve", "success");
        document.getElementById("password").value = "";
      } else {
        showMessage(
          data.message || "Hiba a beállítások mentése közben",
          "error"
        );
      }
    })
    .catch(() => showMessage("Hálózati hiba", "error"));
}

function logout() {
  fetch("/logout", { method: "POST" })
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        window.location.href = "/login";
      } else {
        showMessage("Sikertelen kijelentkezés", "error");
      }
    })
    .catch(() => showMessage("Hálózati hiba", "error"));
}

function applyTheme() {
  const theme = document.getElementById("themeSelect").value;
  applyThemeClient(theme, true);
  showMessage("Téma megváltoztatva: " + theme);
}

document.addEventListener("DOMContentLoaded", () => {
  loadUserInfo();
  const saveBtn = document.getElementById("saveBtn");
  if (saveBtn) saveBtn.addEventListener("click", saveChanges);
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) logoutBtn.addEventListener("click", logout);
  const applyBtn = document.getElementById("applyThemeBtn");
  if (applyBtn) applyBtn.addEventListener("click", applyTheme);
});
