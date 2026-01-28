// autonew.js: AI-backed suggestion UI.
// No fallback words are ever shown. If AI is unavailable or still generating,
// the user is informed and placeholders remain.

let currentWord = "";
let currentTranslation = "";
let isFetching = false;
let waitTimer = null;
const WAIT_THRESHOLD_MS = 800; // when to show "AI is generating" indicator

function getUrlParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function setAiStatus(show, text) {
  const aiStatus = document.getElementById("aiStatus");
  const aiStatusText = document.getElementById("aiStatusText");
  const dismissBtn = document.getElementById("dismissBtn");
  const acceptBtn = document.getElementById("acceptBtn");

  if (text) aiStatusText.innerText = text;

  if (show) {
    aiStatus.style.display = "block";
    dismissBtn.disabled = true;
    acceptBtn.disabled = true;
    aiStatus.setAttribute("aria-busy", "true");
  } else {
    aiStatus.style.display = "none";
    dismissBtn.disabled = false;
    acceptBtn.disabled = false;
    aiStatus.setAttribute("aria-busy", "false");
  }
}

function handleServerFailure(status, data) {
  // Keep placeholders ("...") visible. Inform the user.
  if (status === 202 || (data && data.status === "busy")) {
    setAiStatus(true, (data && data.message) || "AI dolgozik — kérlek várj...");
    return;
  }
  if (status === 503 || (data && data.status === "error")) {
    setAiStatus(false);
    alert(
      (data && data.message) ||
        "AI nem elérhető. Ellenőrizd, hogy az AI szerver fut-e."
    );
    return;
  }
  // Generic error
  setAiStatus(false);
  alert((data && data.message) || "Hiba történt a javaslat lekérése közben.");
}

function fetchSuggestion() {
  if (isFetching) {
    // Already fetching: tell user to wait
    setAiStatus(true, "AI dolgozik — kérlek várj...");
    return;
  }

  isFetching = true;
  // Keep placeholders until we have a valid suggestion (per spec)
  document.getElementById("word").innerText = "...";
  document.getElementById("translation").innerText = "...";

  const isSuggested = getUrlParam("mode") === "suggested";
  const endpoint = isSuggested ? "/recommend_smart_word" : "/recommend_word";

  waitTimer = setTimeout(() => {
    setAiStatus(true, "AI dolgozik — kérlek várj...");
  }, WAIT_THRESHOLD_MS);

  fetch(endpoint, { credentials: "same-origin" })
    .then(async (r) => {
      clearTimeout(waitTimer);
      waitTimer = null;
      isFetching = false;

      let data = {};
      try {
        data = await r.json();
      } catch (e) {
        data = {};
      }

      if (!r.ok || data.status !== "success") {
        handleServerFailure(r.status, data);
        return;
      }

      // Successful response with a valid suggestion
      setAiStatus(false);
      currentWord = data.word || "";
      currentTranslation = data.translation || "";
      document.getElementById("word").innerText = currentWord;
      document.getElementById("translation").innerText = currentTranslation;
    })
    .catch((err) => {
      clearTimeout(waitTimer);
      waitTimer = null;
      isFetching = false;
      setAiStatus(false);
      console.error("Fetch suggestion failed:", err);
      alert(
        "Nem sikerült kapcsolódni a szerverhez. Kérlek próbáld újra később."
      );
    });
}

function dismissSuggestion() {
  if (isFetching) {
    setAiStatus(true, "AI dolgozik — kérlek várj...");
    return;
  }
  // Request next suggestion; backend controls buffering/generation.
  fetchSuggestion();
}

function acceptSuggestion() {
  if (isFetching) {
    setAiStatus(true, "AI dolgozik — kérlek várj...");
    return;
  }
  if (!currentWord || !currentTranslation) {
    alert("Nincs elfogadható javaslat. Várj, amíg az AI válaszol.");
    return;
  }

  setAiStatus(true, "Elfogadás feldolgozása — kérlek várj...");

  fetch("/accept_word", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      word: currentWord,
      translation: currentTranslation,
    }),
  })
    .then(async (r) => {
      let data = {};
      try {
        data = await r.json();
      } catch (e) {
        data = {};
      }
      setAiStatus(false);
      if (r.ok && data.status === "success") {
        // Clear current suggestion and fetch the next one
        currentWord = "";
        currentTranslation = "";
        fetchSuggestion();
      } else {
        alert((data && data.message) || "Hiba az elfogadás során.");
      }
    })
    .catch((err) => {
      console.error("Accept suggestion failed:", err);
      setAiStatus(false);
      alert("Nem sikerült elfogadni a javaslatot. Kérlek próbáld újra.");
    });
}

// On load, immediately request the first suggestion. UI stays in placeholder state until valid AI reply.
window.addEventListener("load", () => {
  // Show small loading indicator until first suggestion arrives.
  setAiStatus(true, "Betöltés...");
  // Brief delay to make the UX smoother when server responds very fast.
  setTimeout(() => {
    fetchSuggestion();
  }, 150);
});
