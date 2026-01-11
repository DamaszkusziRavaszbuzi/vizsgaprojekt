// cards.js: dynamic card creation and drag-to-delete behavior for the cards UI.

document.addEventListener("DOMContentLoaded", function () {
  const cardsArea = document.getElementById("cardsArea");
  const addCardBtn = document.getElementById("addCardBtn");
  const deleteBtn = document.getElementById("deleteBtn");

  if (!cardsArea || !addCardBtn) return;

  let cardCount = 0;
  const CARD_WIDTH = 260;
  const CARD_HEIGHT = 200;

  // Keep track of words already shown in card set to avoid duplicates
  let uniqueWords = new Set();
  // wordLimit is fetched from backend; used to decide when to stop creating new cards
  let wordLimit = Infinity;

  const originalAddCardText = addCardBtn ? addCardBtn.innerText : "Új kártya";

  function fetchWordLimit() {
    // Request how many words the user has; UI uses this to prevent creating more cards than words.
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
    // Fetch a random word from server. Returns an object {word, translation}.
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
    // Compute a random position inside the viewport, leaving some padding.
    const padding = 30;
    const maxLeft = window.innerWidth - CARD_WIDTH - padding;
    const maxTop = window.innerHeight - CARD_HEIGHT - padding;
    const left = Math.random() * Math.max(0, maxLeft) + padding / 2;
    const top = Math.random() * Math.max(0, maxTop) + padding / 2;
    return { left, top };
  }

  async function getUniqueWord(maxAttempts = 10) {
    // Try to fetch a random word that is not already present in uniqueWords.
    // After maxAttempts, give up and return null.
    for (let i = 0; i < maxAttempts; i++) {
      const { word, translation } = await getRandomWord();
      if (!uniqueWords.has(word)) {
        return { word, translation };
      }
    }
    return null;
  }

  function isPointOverDelete(x, y) {
    // Detect whether a client coordinate is over the delete button area.
    // This approach uses elementFromPoint so it respects overlapping elements.
    if (!deleteBtn) return false;
    const el = document.elementFromPoint(x, y);
    if (!el) return false;
    return el === deleteBtn || deleteBtn.contains(el);
  }

  async function createCard() {
    // Create a draggable flip card showing a word and its translation on the back.
    if (uniqueWords.size >= wordLimit) {
      addCardBtn.disabled = true;
      addCardBtn.innerText = "Nincs több kártya";
      return;
    }

    const unique = await getUniqueWord();
    if (!unique) {
      // No unique words available (all words are shown already)
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
    // Store word in dataset for easy removal bookkeeping later
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

    // Drag helpers
    let isDragging = false;
    let dragStart = null;
    let dragOffset = { x: 0, y: 0 };
    let lastOverDelete = false;

    // mousedown initiates either a click (flip) or drag
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

      // Manage active class so only the selected card appears focused
      document
        .querySelectorAll(".card-container")
        .forEach((c) => c.classList.remove("active"));
      cardContainer.classList.add("active");

      function onMouseMove(e2) {
        // If the mouse moves sufficiently, consider it a drag instead of a click.
        const dx = e2.clientX - dragStart.x;
        const dy = e2.clientY - dragStart.y;
        if (!isDragging && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
          isDragging = true;
        }
        if (isDragging) {
          // Keep card inside viewport bounds
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

          // Visual feedback when dragging over delete area
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
        // Clean up listeners
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);

        if (isDragging && isPointOverDelete(e2.clientX, e2.clientY)) {
          // If released over delete, remove card from DOM and update uniqueWords set
          cardContainer.remove();

          const removedWord = cardContainer.dataset.word;
          if (removedWord) {
            uniqueWords.delete(removedWord);
          }

          // If adding was previously disabled due to reaching limit, re-enable if possible
          if (addCardBtn.disabled && uniqueWords.size < wordLimit) {
            addCardBtn.disabled = false;
            addCardBtn.innerText = originalAddCardText;
          }
        } else {
          // If it was a click (no dragging), toggle flip state
          if (!isDragging) {
            card.classList.toggle("flipped");
          }
        }

        if (deleteBtn) deleteBtn.classList.remove("delete-hover");
      }
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    });

    // Prevent native drag behavior which interferes with custom dragging
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

  // Initialize by fetching word count and creating up to 3 cards
  (async () => {
    await fetchWordLimit();
    for (let i = 1; i <= 3; i++) {
      if (uniqueWords.size >= wordLimit) break;
      await createCard();
    }
  })();

  // Keep cards within viewport bounds after resizing window
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
