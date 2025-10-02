let currentWord;
let currentTranslation;
let wordID;
let translationDirection = true; // true = word -> translation, false = translation -> word

// On page load, fetch a random word
window.onload = function () {
  fetch("/get_random_word")
    .then((response) => response.json())
    .then((data) => {
      currentWord = data.word;
      currentTranslation = data.translation;
      wordID = data.word_id;
      console.log(wordID); //gecis faszé nem működik ez a szar majd kijavitom
      document.querySelector(".wordDisplay h1").innerText = currentWord; // Display word
      document.querySelector(".inputField").placeholder = currentTranslation; // Input should be the translation
    })
    .catch((error) => console.error("Error fetching word:", error));
};

// Switch button logic
document.querySelector("#Switch").addEventListener("click", function () {
  fetch("/switch_translation", { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      translationDirection = !translationDirection;
      if (translationDirection) {
        document.querySelector(".wordDisplay h1").innerText = currentWord;
        document.querySelector(".inputField").placeholder = currentTranslation;
      } else {
        document.querySelector(".wordDisplay h1").innerText =
          currentTranslation;
        document.querySelector(".inputField").placeholder = currentWord;
      }
    })
    .catch((error) =>
      console.error("Error switching translation direction:", error)
    );
});

// Check button logic
document.querySelector("#Check").addEventListener("click", function () {
  const userInput = document.querySelector(".inputField").value;
  const isCorrect = translationDirection
    ? userInput === currentTranslation
    : userInput === currentWord;

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
    .then((data) => console.log(data))
    .catch((error) => console.error("Error updating score:", error));
});

// Give up button logic
document.querySelector("#GiveUp").addEventListener("click", function () {
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
    .then((data) => console.log(data))
    .catch((error) => console.error("Error updating score:", error));
});
