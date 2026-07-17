const form = document.querySelector("#prompt-form");
const promptInput = document.querySelector("#prompt");
const characterCount = document.querySelector("#character-count");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = document.querySelector(".button-label");
const result = document.querySelector("#result");
const answer = document.querySelector("#answer");
const responseMeta = document.querySelector("#response-meta");
const errorBox = document.querySelector("#error");

promptInput.addEventListener("input", () => {
  characterCount.textContent = `${promptInput.value.length} / 4000`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;

  submitButton.disabled = true;
  buttonLabel.textContent = "Modellen tenker …";
  result.hidden = true;
  errorBox.hidden = true;

  try {
    const response = await fetch("/api/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Tjenesten kunne ikke svare.");
    }

    answer.textContent = payload.answer;
    responseMeta.textContent = `${payload.model} · ${payload.response_time_ms} ms`;
    result.hidden = false;
  } catch (error) {
    errorBox.textContent = error instanceof Error
      ? error.message
      : "Kunne ikke kontakte AI-tjenesten.";
    errorBox.hidden = false;
  } finally {
    submitButton.disabled = false;
    buttonLabel.textContent = "Send prompt";
  }
});

