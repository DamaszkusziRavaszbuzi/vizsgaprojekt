let currentWord;
let currentTranslation;
let wordID;
let translationDirection = true; // true = word -> translation, false = translation -> word

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
  inputField.disabled = !enabled;
  document.querySelector("#Check").disabled = !enabled;
  document.querySelector("#GiveUp").disabled = !enabled;
}

function loadRandomWord() {
  setInputState(false);
  fetch("/get_random_word")
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "error") {
        wordDisplay.innerText = data.message || "No words!";
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
      wordDisplay.innerText = "Error fetching word!";
      setInputState(false);
      console.error("Error fetching word:", error);
    });
}

// On page load
window.onload = loadRandomWord;

// Switch button logic
document.querySelector("#Switch").addEventListener("click", function () {
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
    .catch((error) =>
      console.error("Error switching translation direction:", error)
    );
});

// Check button logic
document.querySelector("#Check").addEventListener("click", function () {
  setInputState(false);
  const userInput = inputField.value.trim();
  const correctAnswer = translationDirection ? currentTranslation : currentWord;
  const isCorrect = userInput === correctAnswer;

  // Update the score based on whether the answer is correct
  fetch("/update_score", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      word_id: wordID,
      status: isCorrect ? "pass" : "fail",
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      showFeedback(
        isCorrect
          ? "Correct!"
          : `Incorrect! The correct answer was: "${correctAnswer}"`,
        isCorrect
      );
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    })
    .catch((error) => {
      showFeedback("Error updating score!", false);
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    });
});

// Give up button logic
document.querySelector("#GiveUp").addEventListener("click", function () {
  setInputState(false);
  const correctAnswer = translationDirection ? currentTranslation : currentWord;

  fetch("/update_score", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      word_id: wordID,
      status: "fail",
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      showFeedback(
        `Give up! The correct answer was: "${correctAnswer}"`,
        false
      );
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    })
    .catch((error) => {
      showFeedback("Error updating score!", false);
      setTimeout(() => {
        clearFeedback();
        loadRandomWord();
      }, 1700);
    });
});
