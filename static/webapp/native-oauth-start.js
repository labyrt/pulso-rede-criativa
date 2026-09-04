(() => {
  "use strict";
  const form = document.getElementById("native-oauth-form");
  if (!form) return;
  const button = form.querySelector('button[type="submit"]');
  if (!button) return;

  // Android may open this page in a freshly created browser task. Let the
  // browser commit the first-party CSRF cookie before the user continues;
  // auto-submitting immediately can send a stale cookie with the new form
  // token and Django correctly rejects that request.
  button.disabled = true;
  button.textContent = "Preparando acesso seguro…";

  const ready = () => document.cookie
    .split("; ")
    .some(row => row.startsWith("csrftoken="));

  const enable = () => {
    button.disabled = false;
    button.textContent = button.dataset.readyLabel || "Continuar";
    button.focus({ preventScroll: true });
  };

  if (ready()) {
    window.setTimeout(enable, 180);
    return;
  }

  let attempts = 0;
  const timer = window.setInterval(() => {
    attempts += 1;
    if (ready()) {
      window.clearInterval(timer);
      enable();
      return;
    }
    if (attempts >= 20) {
      window.clearInterval(timer);
      button.disabled = false;
      button.textContent = "Recarregar acesso seguro";
      button.addEventListener("click", event => {
        event.preventDefault();
        window.location.reload();
      }, { once: true });
    }
  }, 100);
})();
