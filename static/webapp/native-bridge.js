(() => {
  "use strict";

  const android = window.PulsoAndroid;

  if (android) {
    const callAndroid = (method, ...args) => {
      try {
        if (!android || !android[method]) return false;
        android[method](...args);
        return true;
      } catch (_) {
        return false;
      }
    };

    const showNativeAuthError = () => {
      const message = "Este APK precisa ser atualizado para concluir o login social com segurança.";
      const box = document.getElementById("form-error");
      if (box) {
        box.textContent = message;
        box.setAttribute("role", "alert");
        box.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } else {
        window.alert(message);
      }
    };

    const widgetButtons = [...document.querySelectorAll("[data-native-widget]")];
    widgetButtons.forEach(button => {
      button.hidden = false;
      button.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        callAndroid("requestPinWidget");
      });
    });

    const pushEmbeddedSummary = () => {
      const node = document.getElementById("pulso-widget-summary");
      if (!node?.textContent) return false;
      try {
        const payload = JSON.parse(node.textContent);
        return callAndroid("updateWidgetSummary", JSON.stringify(payload));
      } catch (_) {
        return false;
      }
    };

    const syncWidgetSummary = async () => {
      // The authenticated shell contains a server-rendered, privacy-safe
      // snapshot. Push it first so the widget can become ready immediately
      // after email/password login, even if the follow-up API call is delayed.
      pushEmbeddedSummary();

      try {
        const response = await fetch("/api/v1/widget/summary/", {
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        if (response.ok) {
          const payload = await response.json();
          callAndroid("updateWidgetSummary", JSON.stringify(payload));
        } else if (response.status === 401 || response.status === 403) {
          callAndroid("clearWidgetSummary");
        }
      } catch (_) {
        // Keep the last privacy-safe summary when the network is temporarily unavailable.
      }
    };

    document.querySelectorAll("[data-native-social-provider]").forEach(control => {
      const eventName = control.matches("form") ? "submit" : "click";
      control.addEventListener(eventName, event => {
        const provider = control.dataset.nativeSocialProvider;
        if (!provider) return;
        event.preventDefault();
        event.stopPropagation();

        // A social-login POST made directly from an older WebView can carry a
        // stale CSRF token. Never fall back to that unsafe path inside the APK:
        // current Android builds hand OAuth to the system browser and return
        // through the protected challenge/verifier flow instead.
        if (!callAndroid("startSocialLogin", provider)) showNativeAuthError();
      });
    });

    // Multiple cheap sync points make WebView lifecycle differences across
    // Android vendors harmless. The embedded snapshot prevents extra network
    // requests from being required for the first successful update.
    syncWidgetSummary();
    window.setTimeout(syncWidgetSummary, 300);
    window.setTimeout(syncWidgetSummary, 1_200);
    window.addEventListener("pageshow", syncWidgetSummary);
    window.addEventListener("focus", syncWidgetSummary);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") syncWidgetSummary();
    });
    window.setInterval(() => {
      if (document.visibilityState === "visible") syncWidgetSummary();
    }, 60_000);
  }

  const params = new URLSearchParams(window.location.search);
  if (params.get("composer") === "1") {
    window.setTimeout(() => {
      document.querySelector('[data-action="open-composer"]')?.click();
      params.delete("composer");
      const query = params.toString();
      history.replaceState({}, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
    }, 120);
  }
})();
