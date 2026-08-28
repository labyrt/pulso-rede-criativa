(() => {
  "use strict";

  const shell = document.querySelector("#app-shell");
  if (!shell) return;

  const key = "pulso-brand-intro-seen";
  if (sessionStorage.getItem(key) === "1") return;
  sessionStorage.setItem(key, "1");

  const intro = document.createElement("div");
  intro.className = "pulso-brand-intro";
  intro.setAttribute("aria-hidden", "true");
  intro.innerHTML = `
    <div class="pulso-brand-intro__mark">
      <i class="pulso-brand-intro__bar"></i>
      <i class="pulso-brand-intro__bar"></i>
      <i class="pulso-brand-intro__bar"></i>
    </div>`;
  document.body.append(intro);

  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  const visibleFor = reduced ? 180 : 860;
  window.setTimeout(() => {
    intro.classList.add("is-leaving");
    window.setTimeout(() => intro.remove(), reduced ? 20 : 240);
  }, visibleFor);
})();