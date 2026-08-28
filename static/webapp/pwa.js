(() => {
  "use strict";

  let deferredInstallPrompt = null;
  const isStandalone = () => window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;

  function toast(message) {
    const stack = document.querySelector("#toast-stack");
    if (!stack) return;
    const item = document.createElement("div");
    item.className = "toast";
    item.textContent = message;
    stack.append(item);
    setTimeout(() => item.remove(), 3800);
  }

  async function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return null;
    try {
      return await navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
    } catch (_) {
      return null;
    }
  }

  function addPreferenceButtons() {
    document.querySelectorAll("#account-menu, #mobile-account-menu").forEach(menu => {
      if (!menu.querySelector('[data-pwa-action="notifications"]') && "Notification" in window) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.pwaAction = "notifications";
        button.innerHTML = "Ativar notificações <span>◉</span>";
        menu.insertBefore(button, menu.lastElementChild);
      }
      if (!isStandalone() && !menu.querySelector('[data-pwa-action="install"]')) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.pwaAction = "install";
        button.innerHTML = "Instalar PULSO <span>↓</span>";
        menu.insertBefore(button, menu.lastElementChild);
      }
    });
  }

  async function requestNotifications() {
    if (!("Notification" in window)) {
      toast("Este navegador não oferece notificações do sistema.");
      return "unsupported";
    }
    if (Notification.permission === "granted") {
      toast("As notificações do PULSO já estão ativas.");
      return "granted";
    }
    const permission = await Notification.requestPermission();
    toast(permission === "granted" ? "Notificações do PULSO ativadas." : "Notificações não foram ativadas.");
    return permission;
  }

  async function installApp() {
    if (isStandalone()) return;
    if (deferredInstallPrompt) {
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice.catch(() => null);
      deferredInstallPrompt = null;
      return;
    }
    const isiOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    if (isiOS) toast("No Safari, use Compartilhar → Adicionar à Tela de Início.");
    else toast("Use a opção “Instalar app” ou “Adicionar à tela inicial” do navegador.");
  }

  async function showNotification(title, options = {}) {
    if (!("Notification" in window) || Notification.permission !== "granted") return false;
    const registration = await navigator.serviceWorker?.ready.catch(() => null);
    const data = { url: options.url || "/app/", ...(options.data || {}) };
    const notificationOptions = {
      body: options.body || "",
      icon: "/static/webapp/icons/pulso-192.png",
      badge: "/static/webapp/icons/pulso-192.png",
      tag: options.tag || "pulso-live",
      renotify: Boolean(options.renotify),
      requireInteraction: Boolean(options.requireInteraction),
      data,
    };
    if (registration?.showNotification) {
      await registration.showNotification(title, notificationOptions);
      return true;
    }
    new Notification(title, notificationOptions);
    return true;
  }

  window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault();
    deferredInstallPrompt = event;
    addPreferenceButtons();
  });

  window.addEventListener("appinstalled", () => {
    deferredInstallPrompt = null;
    toast("PULSO instalado na sua tela inicial.");
    document.querySelectorAll('[data-pwa-action="install"]').forEach(button => button.remove());
  });

  document.addEventListener("click", event => {
    const target = event.target.closest("[data-pwa-action]");
    if (!target) return;
    if (target.dataset.pwaAction === "install") installApp();
    if (target.dataset.pwaAction === "notifications") requestNotifications();
  });

  window.PulsoPWA = { showNotification, requestNotifications, installApp, isStandalone };
  registerServiceWorker();
  addPreferenceButtons();
})();
