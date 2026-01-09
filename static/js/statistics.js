let words = [];
let currentSort = { column: "word", ascending: true };

function updateSummary() {
  const totalWords = words.length;
  let avgConfidence = 0;
  if (totalWords === 0) {
    avgConfidence = 0;
  } else {
    avgConfidence =
      words.reduce((acc, word) => acc + word.confidenceIndex, 0) / totalWords;
  }
  const positiveWords = words.filter((word) => word.confidenceIndex > 0).length;
  const negativeWords = words.filter((word) => word.confidenceIndex < 0).length;

  document.getElementById("totalWords").textContent = totalWords;
  document.getElementById("avgConfidence").textContent = Number.isFinite(
    avgConfidence
  )
    ? avgConfidence.toFixed(2)
    : "0.00";
  document.getElementById("positiveWords").textContent = positiveWords;
  document.getElementById("negativeWords").textContent = negativeWords;
}

function getConfidenceClass(confidence) {
  if (confidence > 0) return "confidence-positive";
  if (confidence < 0) return "confidence-negative";
  return "confidence-neutral";
}

function sortWords(column) {
  if (currentSort.column === column) {
    currentSort.ascending = !currentSort.ascending;
  } else {
    currentSort.column = column;
    currentSort.ascending = true;
  }

  words.sort((a, b) => {
    let comparison = 0;
    if (typeof a[column] === "string") {
      comparison = a[column].localeCompare(b[column]);
    } else {
      comparison = a[column] - b[column];
    }
    return currentSort.ascending ? comparison : -comparison;
  });

  displayWords();
}

function displayWords() {
  const tbody = document.getElementById("statsBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  words.forEach((word) => {
    const row = document.createElement("tr");
    row.innerHTML = `
                    <td>${word.word}</td>
                    <td>${word.translation}</td>
                    <td>${word.pass}</td>
                    <td>${word.passWithHelp}</td>
                    <td>${word.fail}</td>
                    <td>${word.failWithHelp}</td>
                    <td class="${getConfidenceClass(word.confidenceIndex)}">${
      word.confidenceIndex
    }</td>
                `;
    tbody.appendChild(row);
  });
}

function loadStatistics() {
  fetch("/get_word_statistics")
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        words = data.words || [];
        updateSummary();
        displayWords();
      }
    });
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".sort-button").forEach((button) => {
    button.addEventListener("click", (e) => {
      const column = e.target.getAttribute("data-sort");
      if (column) sortWords(column);
    });
  });
  loadStatistics();
});
