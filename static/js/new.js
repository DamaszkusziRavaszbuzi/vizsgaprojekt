// new.js: UI for adding a new word via the "new" page.
// Uses application/x-www-form-urlencoded POST as the server expects form encoded data.

document.addEventListener("DOMContentLoaded", function () {
  const addButton = document.getElementById("addButton");
  const wordInput = document.getElementById("word");
  const translationInput = document.getElementById("translation");

  if (!addButton || !wordInput || !translationInput) return;

  addButton.addEventListener("click", function () {
    const word = wordInput.value.trim();
    const translation = translationInput.value.trim();

    // Send as form-encoded since server route reads from request.form
    fetch("/add_word", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ word, translation }).toString(),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success") {
          alert(data.message);
          wordInput.value = "";
          translationInput.value = "";
        } else {
          alert(data.message || "Hiba történt");
        }
      })
      .catch(() => alert("Hálózati hiba"));
  });
});
