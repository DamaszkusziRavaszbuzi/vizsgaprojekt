// randomPractice.js: core practice interactions for checking answers, getting help and learning-mode flow.

let currentWord;
let currentTranslation;
let wordID;
let translationDirection = true; // true means display English and expect Hungarian
let helpUsed = false;

let learningMode = false;
let learningWordIDs = [];
let usedLearningWordIDs = [];

const wordDisplay = document.querySelector(".wordDisplay h1");
const inputField = document.querySelector(".inputField");
const feedbackDiv = document.getElementById("feedback");

function showFeedback(message, isCorrect) {
  feedbackDiv.innerText = message;
  feedbackDiv.style.color = isCorrect ? "limegreen" : "orange";
}

function clearFeedback() {
  feedbackDiv.innerText = "";
}

function setInputState(enabled) {
  // Enable/disable interactive controls while waiting for responses
  inputField.disabled = !enabled;
  document.querySelector("#Check").disabled = !enabled;
  document.querySelector("#GiveUp").disabled = !enabled;
}

function getUrlParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

if (getUrlParam("mode") === "learning") {
  // If URL contains mode=learning, toggle learning flow which pulls IDs from /get_learning_words
  learningMode = true;
}

function pickNextLearningWord() {
  // If we have no cached learningWordIDs, request them from server.
  if (learningWordIDs.length === 0) {
    fetch("/get_learning_words")
      .then((r) => r.json())
      .then((data) => {
        if (data.status !== "success" || !data.word_ids.length) {
          wordDisplay.innerText = "Nincs több gyakorló szó!";
          setInputState(false);
          return;
        }
        learningWordIDs = data.word_ids.slice();
        usedLearningWordIDs = [];
        pickNextLearningWord();
      })
      .catch(() => {
        wordDisplay.innerText = "Hiba a szavak betöltésekor!";
        setInputState(false);
      });
    return;
  }

  // Choose an unused ID at random; if all used, reset usedLearningWordIDs to allow repeats
  let available = learningWordIDs.filter(
    (id) => !usedLearningWordIDs.includes(id)
  );
  if (available.length === 0) {
    usedLearningWordIDs = [];
    available = learningWordIDs.slice();
  }
  const idx = Math.floor(Math.random() * available.length);
  const wordIDToUse = available[idx];
  usedLearningWordIDs.push(wordIDToUse);

  // Fetch the word details by ID from server
  fetch("/get_word_by_id", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word_id: wordIDToUse }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.status !== "success") {
        showFeedback("Hiba a szó betöltésekor!", false);
        return;
      }
      currentWord = data.word;
      currentTranslation = data.translation;
      wordID = data.word_id;
      inputField.value = "";
      clearFeedback();
      setInputState(true);
      if (translationDirection) {
        wordDisplay.innerText = currentWord;
        inputField.placeholder = currentTranslation;
      } else {
        wordDisplay.innerText = currentTranslation;
        inputField.placeholder = currentWord;
      }
    })
    .catch(() => {
      showFeedback("Hiba a szó betöltésekor!", false);
    });
}

function loadRandomWord() {
  // Central entry point for loading the next word into the UI.
  setInputState(false);
  helpUsed = false;
  if (learningMode) {
    pickNextLearningWord();
  } else {
    fetch("/get_random_word")
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "error") {
          wordDisplay.innerText = data.message || "Nincs több szó!";
          inputField.placeholder = "";
          setInputState(false);
          return;
        }
        currentWord = data.word;
        currentTranslation = data.translation;
        wordID = data.word_id;
        inputField.value = "";
        clearFeedback();
        setInputState(true);

        if (translationDirection) {
          wordDisplay.innerText = currentWord;
          inputField.placeholder = currentTranslation;
        } else {
          wordDisplay.innerText = currentTranslation;
          inputField.placeholder = currentWord;
        }
      })
      .catch((error) => {
        wordDisplay.innerText = "Hiba a szó betöltésekor!";
        setInputState(false);
        console.error("Error fetching word:", error);
      });
  }
}

window.onload = loadRandomWord;

document.querySelector("#Switch").addEventListener("click", function () {
  // Toggle translation direction on both server (session) and client for immediate UX changes.
  fetch("/switch_translation", { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      translationDirection = !translationDirection;
      if (translationDirection) {
        wordDisplay.innerText = currentWord;
        inputField.placeholder = currentTranslation;
      } else {
        wordDisplay.innerText = currentTranslation;
        inputField.placeholder = currentWord;
      }
      inputField.value = "";
      clearFeedback();
    })
    .catch((error) => console.error("Hiba", error));
});

document.querySelector("#Check").addEventListener("click", function () {
  // When user checks an answer, compute status based on correctness and whether help was used.
  setInputState(false);
  const userInput = inputField.value.trim();
  const correctAnswer = translationDirection ? currentTranslation : currentWord;
  const isCorrect = userInput === correctAnswer;

  let status;
  if (isCorrect) {
    status = helpUsed ? "passWithHelp" : "pass";
  } else {
    status = helpUsed ? "failWithHelp" : "fail";
  }

  // Persist result to server, then show feedback and load next word after a small delay.
  fetch("/update_score", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      word_id: wordID,
      status: status,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      showFeedback(
        isCorrect ? "Helyes!" : `Helytelen! A jó válasz: "${correctAnswer}"`,
        isCorrect
      );
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    })
    .catch((error) => {
      showFeedback("Hiba a pontszám frissítésénél!", false);
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    });
});

document.querySelector("#GiveUp").addEventListener("click", function () {
  // User gives up: count as fail (or failWithHelp if helpUsed true), show correct answer and move on.
  setInputState(false);
  const correctAnswer = translationDirection ? currentTranslation : currentWord;

  const status = helpUsed ? "failWithHelp" : "fail";

  fetch("/update_score", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      word_id: wordID,
      status: status,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      showFeedback(`Feladva! A jó válasz: "${correctAnswer}"`, false);
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    })
    .catch((error) => {
      showFeedback("Hiba a pontszám frissítésénél!", false);
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    });
});

function showHelpModal() {
  // Present help modal with options multiple choice or show vowels
  document.getElementById("helpModal").style.display = "flex";
  document.getElementById("helpChoices").innerHTML = "";
}
function hideHelpModal() {
  document.getElementById("helpModal").style.display = "none";
  document.getElementById("helpChoices").innerHTML = "";
}

document.querySelector("#Help").addEventListener("click", function () {
  showHelpModal();
});

document.getElementById("helpCancel").onclick = hideHelpModal;

document.getElementById("helpMultipleChoice").onclick = function () {
  // Help: show multiple choice alternatives. Mark helpUsed=true so scoring reflects help.
  helpUsed = true;

  fetch("/get_choices", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      word_id: wordID,
      direction: translationDirection,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status !== "success") {
        document.getElementById("helpChoices").innerText =
          "Nem sikerült a válaszlehetőségek betöltése!";
        return;
      }

      const helpChoicesDiv = document.getElementById("helpChoices");
      helpChoicesDiv.innerHTML = "<p>Válaszd ki a helyes választ:</p>";
      data.choices.forEach((choice) => {
        const btn = document.createElement("button");
        btn.className = "highlightOnHoverButton";
        btn.innerText = choice;
        btn.style = "padding: 8px; margin: 3px;";
        // Clicking a choice fills the input and closes the modal
        btn.onclick = () => {
          inputField.value = choice;
          hideHelpModal();
        };
        helpChoicesDiv.appendChild(btn);
      });
    })
    .catch(() => {
      document.getElementById("helpChoices").innerText =
        "Hiba a lehetőségek betöltésekor!";
    });
};

document.getElementById("helpShowVowels").onclick = function () {
  // Help option to reveal vowels in the correct answer as a hint.
  helpUsed = true;

  const answer = translationDirection ? currentTranslation : currentWord;

  // Use a regex that covers Hungarian vowels (including accented characters)
  const vowels = answer.match(/[aeiouáéíóöőúüűAEIOUÁÉÍÓÖŐÚÜŰ]/g);
  const vowelString = vowels ? vowels.join("") : "";
  inputField.placeholder = `Magánhangzók: ${vowelString}`;
  inputField.focus();
  hideHelpModal();
};
