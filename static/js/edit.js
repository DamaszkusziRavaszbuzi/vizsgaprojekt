function loadWords() {
  fetch("/get_user_words")
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        const wordsList = document.getElementById("wordsList");
        wordsList.innerHTML = "";

        data.words.forEach((word) => {
          const row = document.createElement("tr");
          row.className = "word-row";
          row.setAttribute("data-word-id", word.id);

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
  if (confirm("Are you sure you want to delete this word?")) {
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

document.getElementById("wordsList").addEventListener("click", function (e) {
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
    // Store original values
    const originalWord = wordCell.textContent;
    const originalTranslation = translationCell.textContent;

    // Replace text with input fields
    wordCell.innerHTML = `<input type="text" class="input-field" value="${originalWord}">`;
    translationCell.innerHTML = `<input type="text" class="input-field" value="${originalTranslation}">`;

    // Toggle buttons
    editButton.style.display = "none";
    deleteButton.style.display = "none";
    saveButton.style.display = "inline";
    cancelButton.style.display = "inline";

    // Store original content for cancel
    row.setAttribute("data-original-word", originalWord);
    row.setAttribute("data-original-translation", originalTranslation);
  } else if (e.target.classList.contains("save-button")) {
    const newWord = row.querySelector(".word-cell input").value;
    const newTranslation = row.querySelector(".translation-cell input").value;

    updateWord(wordId, newWord, newTranslation);
  } else if (e.target.classList.contains("cancel-button")) {
    // Restore original content
    wordCell.textContent = row.getAttribute("data-original-word");
    translationCell.textContent = row.getAttribute("data-original-translation");

    // Toggle buttons back
    editButton.style.display = "inline";
    deleteButton.style.display = "inline";
    saveButton.style.display = "none";
    cancelButton.style.display = "none";
  }
});

// Load words when the page loads
document.addEventListener("DOMContentLoaded", loadWords);
