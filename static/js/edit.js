function loadWords() {
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
        const newWord = row.querySelector(".word-cell input").value;
        const newTranslation = row.querySelector(
          ".translation-cell input"
        ).value;

        updateWord(wordId, newWord, newTranslation);
      } else if (e.target.classList.contains("cancel-button")) {
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
