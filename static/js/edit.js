// edit.js: functionality for editing and deleting user words in a table.
// The file loads words, provides inline edit UI and makes AJAX calls to update the server.

function loadWords() {
  // Request user's words and populate the table body (#wordsList)
  fetch("/get_user_words")
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        const wordsList = document.getElementById("wordsList");
        if (!wordsList) return;
        wordsList.innerHTML = "";

        data.words.forEach((word) => {
          const row = document.createElement("tr");
          row.className = "word-row";
          row.setAttribute("data-word-id", word.id);

          // Buttons for edit/delete/save/cancel. Save and cancel are hidden initially by CSS.
          row.innerHTML = `
                                <td class="word-cell">${word.word}</td>
                                <td class="translation-cell">${word.translation}</td>
                                <td>
                                    <button class="button edit-button">Szerkesztés</button>
                                    <button class="button delete-button">Törlés</button>
                                    <button class="button save-button">Mentés</button>
                                    <button class="button cancel-button">Mégsem</button>
                                </td>
                            `;
          wordsList.appendChild(row);
        });
      }
    });
}

function deleteWord(wordId) {
  // Confirm deletion then request server to delete the word
  if (confirm("Biztosan törölni szeretnéd ezt a szót?")) {
    fetch("/delete_word", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ word_id: wordId }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          loadWords();
        }
      });
  }
}

function updateWord(wordId, word, translation) {
  // Send updated word data to server
  fetch("/update_word", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      word_id: wordId,
      word: word,
      translation: translation,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        loadWords();
      }
    });
}

document.addEventListener("DOMContentLoaded", function () {
  const wordsList = document.getElementById("wordsList");
  if (wordsList) {
    // Use event delegation to handle button clicks inside the table
    wordsList.addEventListener("click", function (e) {
      const row = e.target.closest(".word-row");
      if (!row) return;

      const wordId = row.getAttribute("data-word-id");
      const wordCell = row.querySelector(".word-cell");
      const translationCell = row.querySelector(".translation-cell");
      const editButton = row.querySelector(".edit-button");
      const deleteButton = row.querySelector(".delete-button");
      const saveButton = row.querySelector(".save-button");
      const cancelButton = row.querySelector(".cancel-button");

      if (e.target.classList.contains("delete-button")) {
        deleteWord(wordId);
      } else if (e.target.classList.contains("edit-button")) {
        // Turn cells into inputs for inline editing and store original values on the row
        const originalWord = wordCell.textContent;
        const originalTranslation = translationCell.textContent;

        wordCell.innerHTML = `<input type="text" class="input-field" value="${originalWord}">`;
        translationCell.innerHTML = `<input type="text" class="input-field" value="${originalTranslation}">`;

        if (editButton) editButton.style.display = "none";
        if (deleteButton) deleteButton.style.display = "none";
        if (saveButton) saveButton.style.display = "inline";
        if (cancelButton) cancelButton.style.display = "inline";

        row.setAttribute("data-original-word", originalWord);
        row.setAttribute("data-original-translation", originalTranslation);
      } else if (e.target.classList.contains("save-button")) {
        // Read input values and call update
        const newWord = row.querySelector(".word-cell input").value;
        const newTranslation = row.querySelector(
          ".translation-cell input"
        ).value;

        updateWord(wordId, newWord, newTranslation);
      } else if (e.target.classList.contains("cancel-button")) {
        // Restore original values and reset button visibility
        wordCell.textContent = row.getAttribute("data-original-word");
        translationCell.textContent = row.getAttribute(
          "data-original-translation"
        );

        if (editButton) editButton.style.display = "inline";
        if (deleteButton) deleteButton.style.display = "inline";
        if (saveButton) saveButton.style.display = "none";
        if (cancelButton) cancelButton.style.display = "none";
      }
    });

    loadWords();
  }
});
