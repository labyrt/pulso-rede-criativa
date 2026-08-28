(() => {
  "use strict";

  const messageIcon = `
    <svg class="pulso-icon pulso-message-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"></path>
    </svg>`;

  const phoneIcon = `
    <svg class="pulso-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2A19.79 19.79 0 0 1 3.09 5.18 2 2 0 0 1 5.07 3h3a2 2 0 0 1 2 1.72c.12.9.33 1.78.62 2.63a2 2 0 0 1-.45 2.11L9 10.73a16 16 0 0 0 4.27 4.27l1.27-1.27a2 2 0 0 1 2.11-.45c.85.29 1.73.5 2.63.62A2 2 0 0 1 22 16.92z"></path>
    </svg>`;

  const videoIcon = `
    <svg class="pulso-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="3" y="6" width="13" height="12" rx="2"></rect>
      <path d="m16 10 5-3v10l-5-3z"></path>
    </svg>`;

  function replaceMessageNavIcons() {
    document.querySelectorAll('[data-nav="messages"]').forEach(link => {
      let holder = link.querySelector('.nav-icon');
      if (!holder) {
        [...link.childNodes]
          .filter(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim())
          .forEach(node => node.remove());
        holder = document.createElement('span');
        holder.className = 'nav-icon nav-icon--svg';
        link.prepend(holder);
      } else {
        holder.classList.add('nav-icon--svg');
      }
      if (!holder.querySelector('.pulso-message-icon')) holder.innerHTML = messageIcon;
    });
  }

  function decorateCallButtons(root = document) {
    root.querySelectorAll?.('[data-call="audio"]').forEach(button => {
      button.classList.add('call-action-button');
      button.setAttribute('aria-label', 'Iniciar ligação de áudio');
      button.setAttribute('title', 'Ligação de áudio');
      if (!button.querySelector('.pulso-icon')) button.innerHTML = phoneIcon;
    });

    root.querySelectorAll?.('[data-call="video"]').forEach(button => {
      button.classList.add('call-action-button');
      button.setAttribute('aria-label', 'Iniciar ligação de vídeo');
      button.setAttribute('title', 'Ligação de vídeo');
      if (!button.querySelector('.pulso-icon')) button.innerHTML = videoIcon;
    });
  }

  function updateVisualViewportHeight() {
    const viewport = window.visualViewport;
    const height = viewport?.height || window.innerHeight;
    if (!height) return;
    document.documentElement.style.setProperty('--pulso-visual-height', `${Math.round(height)}px`);
  }

  replaceMessageNavIcons();
  decorateCallButtons();
  updateVisualViewportHeight();

  const page = document.querySelector('#page-content');
  if (page) {
    const observer = new MutationObserver(mutations => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach(node => {
          if (!(node instanceof Element)) return;
          if (node.matches?.('[data-call]') || node.querySelector?.('[data-call]')) decorateCallButtons(node.matches?.('[data-call]') ? node.parentElement : node);
        });
      }
    });
    observer.observe(page, { childList: true, subtree: true });
  }

  window.addEventListener('resize', updateVisualViewportHeight, { passive: true });
  window.visualViewport?.addEventListener('resize', updateVisualViewportHeight, { passive: true });
  window.visualViewport?.addEventListener('scroll', updateVisualViewportHeight, { passive: true });
})();
