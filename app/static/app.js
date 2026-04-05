const ranges = document.querySelectorAll("[data-rating-range]");

for (const range of ranges) {
  const output = document.querySelector("[data-rating-output]");
  const sync = () => {
    if (output) {
      output.textContent = range.value;
    }
  };
  range.addEventListener("input", sync);
  sync();
}

