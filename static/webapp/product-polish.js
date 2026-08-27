(() => {
  "use strict";

  const RANDOM_PIX_PATTERN = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const RANDOM_PIX_EXAMPLE = "123e4567-e12b-12d1-a456-426655440000";

  function enhanceProfileSupport(root = document) {
    const buttons = root.querySelectorAll?.('.outline-button--pink[data-action="support"]') || [];
    buttons.forEach(button => {
      if (button.dataset.supportPolished === "true") return;
      button.dataset.supportPolished = "true";
      button.classList.add("profile-support-action");
      button.setAttribute("aria-label", "Apoiar este perfil diretamente via Pix");
      button.innerHTML = '<span class="profile-support-icon" aria-hidden="true">♡</span><span>Apoiar via Pix</span>';
    });
  }

  function enhanceRandomPixForm(root = document) {
    const form = root.matches?.("#profile-form") ? root : root.querySelector?.("#profile-form");
    if (!form) return;

    const typeSelect = form.querySelector('select[name="pix_key_type"]');
    const keyInput = form.querySelector('input[name="pix_key"]');
    if (!keyInput) return;

    if (typeSelect) {
      const typeLabel = typeSelect.closest("label");
      typeLabel?.remove();
    }

    const keyLabel = keyInput.closest("label");
    if (!keyLabel || keyLabel.dataset.randomPixReady === "true") return;
    keyLabel.dataset.randomPixReady = "true";

    keyInput.placeholder = RANDOM_PIX_EXAMPLE;
    keyInput.pattern = RANDOM_PIX_PATTERN;
    keyInput.autocomplete = "off";
    keyInput.inputMode = "text";
    keyInput.setAttribute("aria-describedby", "pix-random-help");

    const labelText = [...keyLabel.childNodes].find(node => node.nodeType === Node.TEXT_NODE);
    if (labelText) labelText.textContent = "Chave aleatória Pix";

    const note = document.createElement("div");
    note.className = "pix-random-only";
    note.id = "pix-random-help";
    note.innerHTML = `
      <strong>Somente chave aleatória (EVP)</strong>
      <small>Para proteger seus dados pessoais, a PULSO não aceita CPF, telefone ou e-mail como chave. Crie uma chave aleatória no aplicativo do seu banco e cole aqui.</small>
      <code>${RANDOM_PIX_EXAMPLE}</code>`;
    keyLabel.before(note);
  }

  function enhance(root = document) {
    enhanceProfileSupport(root);
    enhanceRandomPixForm(root);
  }

  enhance();

  const observer = new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (!(node instanceof Element)) continue;
        enhance(node);
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
})();
