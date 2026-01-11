// autonew.js: logic for the automatic suggestion page (autonew.html).
// Provides functions to fetch suggested words (smart or random) and accept/dismiss them.

let currentWord = "";
let currentTranslation = "";

// Read query param helper
function getUrlParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function fetchSuggestion() {
  // mode=suggested triggers smarter recommendation (recommend_smart_word), otherwise random recommendation
  const isSuggested = getUrlParam("mode") === "suggested";
  const endpoint = isSuggested ? "/recommend_smart_word" : "/recommend_word";

  fetch(endpoint)
    .then((r) => r.json())
    .then((data) => {
      // Expecting {status: "success", word, translation}
      if (data.status === "success") {
        currentWord = data.word;
        currentTranslation = data.translation;
        document.getElementById("word").innerText = currentWord;
        document.getElementById("translation").innerText = currentTranslation;
      } else {
        // On error, show an alert. In production a nicer UI message would be preferable.
        alert(data.message || "Hiba történt!");
      }
    });
}

function dismissSuggestion() {
  // Replace current suggestion with a new one
  fetchSuggestion();
}

function acceptSuggestion() {
  // Send accepted suggestion to server to be added to user's word list.
  fetch("/accept_word", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      word: currentWord,
      translation: currentTranslation,
    }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        // After accepting, request next suggestion
        fetchSuggestion();
      } else {
        alert(data.message || "Hiba történt!");
      }
    });
}

// Fetch first suggestion when page loads
window.onload = fetchSuggestion;
