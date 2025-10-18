// Utilities to show messages
function showMessage(text, type = "success") {
  const el = document.getElementById("msg");
  el.textContent = text;
  el.className = "message " + (type === "error" ? "error" : "success");
  el.style.display = "block";
  setTimeout(() => {
    el.style.display = "none";
  }, 4000);
}

// Load current username
function loadUserInfo() {
  fetch("/get_user_info")
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        document.getElementById("username").value = data.user.username || "";
      } else {
        showMessage(
          data.message || "Hiba a felhasználó adatainak betöltése közben",
          "error"
        );
      }
    })
    .catch(() => showMessage("Hálózati hiba", "error"));
}

// Update user info
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

// Logout (re-uses your /logout endpoint)
function logout() {
  fetch("/logout", { method: "POST" })
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        // Redirect to login
        window.location.href = "/login";
      } else {
        showMessage("Sikertelen kijelentkezés", "error");
      }
    })
    .catch(() => showMessage("Hálózati hiba", "error"));
}

// Theme apply placeholder
function applyTheme() {
  const theme = document.getElementById("themeSelect").value;
  showMessage("Téma megváltoztatva: " + theme);
}

document.addEventListener("DOMContentLoaded", () => {
  loadUserInfo();
  document.getElementById("saveBtn").addEventListener("click", saveChanges);
  document.getElementById("logoutBtn").addEventListener("click", logout);
  document
    .getElementById("applyThemeBtn")
    .addEventListener("click", applyTheme);
});
