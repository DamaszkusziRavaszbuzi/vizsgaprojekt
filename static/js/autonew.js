let currentWord = "";
let currentTranslation = "";

function getUrlParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function fetchSuggestion() {
  const isSuggested = getUrlParam("mode") === "suggested";
  const endpoint = isSuggested ? "/recommend_smart_word" : "/recommend_word";

  fetch(endpoint)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        currentWord = data.word;
        currentTranslation = data.translation;
        document.getElementById("word").innerText = currentWord;
        document.getElementById("translation").innerText = currentTranslation;
      } else {
        alert(data.message || "Hiba történt!");
      }
    });
}

function dismissSuggestion() {
  fetchSuggestion();
}

function acceptSuggestion() {
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
        fetchSuggestion();
      } else {
        alert(data.message || "Hiba történt!");
      }
    });
}

window.onload = fetchSuggestion;
