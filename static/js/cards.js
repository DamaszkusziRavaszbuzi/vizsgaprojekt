document.addEventListener("DOMContentLoaded", function () {
  const cardsArea = document.getElementById("cardsArea");
  const addCardBtn = document.getElementById("addCardBtn");
  const deleteBtn = document.getElementById("deleteBtn");

  if (!cardsArea || !addCardBtn) return;

  let cardCount = 0;
  const CARD_WIDTH = 260;
  const CARD_HEIGHT = 200;

  let uniqueWords = new Set();
  let wordLimit = Infinity;

  const originalAddCardText = addCardBtn ? addCardBtn.innerText : "Új kártya";

  function fetchWordLimit() {
    return fetch("/get_word_count")
      .then((response) => response.json())
      .then((data) => {
        wordLimit = data.count;
        return wordLimit;
      })
      .catch((error) => {
        console.error("Error fetching word count:", error);
        wordLimit = Infinity;
        return wordLimit;
      });
  }

  function getRandomWord() {
    return fetch("/get_random_word")
      .then((response) => response.json())
      .then((data) => {
        return {
          word: data.word,
          translation: data.translation,
        };
      })
      .catch((error) => {
        console.error("Error fetching word:", error);
        return { word: "Error", translation: "Error" };
      });
  }

  function getRandomPosition() {
    const padding = 30;
    const maxLeft = window.innerWidth - CARD_WIDTH - padding;
    const maxTop = window.innerHeight - CARD_HEIGHT - padding;
    const left = Math.random() * Math.max(0, maxLeft) + padding / 2;
    const top = Math.random() * Math.max(0, maxTop) + padding / 2;
    return { left, top };
  }

  async function getUniqueWord(maxAttempts = 10) {
    for (let i = 0; i < maxAttempts; i++) {
      const { word, translation } = await getRandomWord();
      if (!uniqueWords.has(word)) {
        return { word, translation };
      }
    }
    return null;
  }

  function isPointOverDelete(x, y) {
    if (!deleteBtn) return false;
    const el = document.elementFromPoint(x, y);
    if (!el) return false;
    return el === deleteBtn || deleteBtn.contains(el);
  }

  async function createCard() {
    if (uniqueWords.size >= wordLimit) {
      addCardBtn.disabled = true;
      addCardBtn.innerText = "Nincs több kártya";
      return;
    }

    const unique = await getUniqueWord();
    if (!unique) {
      alert("Nincs több egyedi szó.");
      addCardBtn.disabled = true;
      addCardBtn.innerText = "Nincs több kártya";
      return;
    }
    const { word, translation } = unique;

    cardCount++;
    uniqueWords.add(word);

    const { left, top } = getRandomPosition();
    const cardContainer = document.createElement("div");
    cardContainer.className = "card-container";
    cardContainer.style.left = `${left}px`;
    cardContainer.style.top = `${top}px`;
    cardContainer.dataset.word = word;

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
        <div class="card-inner">
          <div class="card-front">${word}</div>
          <div class="card-back">${translation}</div>
        </div>
      `;
    cardContainer.appendChild(card);

    let isDragging = false;
    let dragStart = null;
    let dragOffset = { x: 0, y: 0 };
    let lastOverDelete = false;

    cardContainer.addEventListener("mousedown", (e) => {
      isDragging = false;
      dragStart = {
        x: e.clientX,
        y: e.clientY,
        left: cardContainer.offsetLeft,
        top: cardContainer.offsetTop,
      };
      dragOffset.x = e.clientX - cardContainer.offsetLeft;
      dragOffset.y = e.clientY - cardContainer.offsetTop;

      document
        .querySelectorAll(".card-container")
        .forEach((c) => c.classList.remove("active"));
      cardContainer.classList.add("active");

      function onMouseMove(e2) {
        const dx = e2.clientX - dragStart.x;
        const dy = e2.clientY - dragStart.y;
        if (!isDragging && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
          isDragging = true;
        }
        if (isDragging) {
          let newLeft = e2.clientX - dragOffset.x;
          let newTop = e2.clientY - dragOffset.y;
          newLeft = Math.max(
            0,
            Math.min(newLeft, window.innerWidth - CARD_WIDTH)
          );
          newTop = Math.max(
            0,
            Math.min(newTop, window.innerHeight - CARD_HEIGHT)
          );
          cardContainer.style.left = newLeft + "px";
          cardContainer.style.top = newTop + "px";

          const overDelete = isPointOverDelete(e2.clientX, e2.clientY);
          if (overDelete && !lastOverDelete) {
            lastOverDelete = true;
            if (deleteBtn) deleteBtn.classList.add("delete-hover");
          } else if (!overDelete && lastOverDelete) {
            lastOverDelete = false;
            if (deleteBtn) deleteBtn.classList.remove("delete-hover");
          }
        }
      }
      function onMouseUp(e2) {
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);

        if (isDragging && isPointOverDelete(e2.clientX, e2.clientY)) {
          cardContainer.remove();

          const removedWord = cardContainer.dataset.word;
          if (removedWord) {
            uniqueWords.delete(removedWord);
          }

          if (addCardBtn.disabled && uniqueWords.size < wordLimit) {
            addCardBtn.disabled = false;
            addCardBtn.innerText = originalAddCardText;
          }
        } else {
          if (!isDragging) {
            card.classList.toggle("flipped");
          }
        }

        if (deleteBtn) deleteBtn.classList.remove("delete-hover");
      }
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    });

    card.addEventListener("dragstart", (e) => e.preventDefault());

    cardsArea.appendChild(cardContainer);

    if (uniqueWords.size >= wordLimit) {
      addCardBtn.disabled = true;
      addCardBtn.innerText = "No more cards";
    }
  }

  addCardBtn.addEventListener("click", () => {
    createCard();
  });

  (async () => {
    await fetchWordLimit();
    for (let i = 1; i <= 3; i++) {
      if (uniqueWords.size >= wordLimit) break;
      await createCard();
    }
  })();

  window.addEventListener("resize", () => {
    document.querySelectorAll(".card-container").forEach((container) => {
      let left = parseInt(container.style.left) || 0;
      let top = parseInt(container.style.top) || 0;
      if (left + CARD_WIDTH > window.innerWidth)
        container.style.left = window.innerWidth - CARD_WIDTH - 10 + "px";
      if (top + CARD_HEIGHT > window.innerHeight)
        container.style.top = window.innerHeight - CARD_HEIGHT - 10 + "px";
    });
  });
});
