document.addEventListener("DOMContentLoaded", function () {
  const addButton = document.getElementById("addButton");
  const wordInput = document.getElementById("word");
  const translationInput = document.getElementById("translation");

  if (!addButton || !wordInput || !translationInput) return;

  addButton.addEventListener("click", function () {
    const word = wordInput.value.trim();
    const translation = translationInput.value.trim();

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
