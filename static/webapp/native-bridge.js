(() => {
  "use strict";

  const android = window.PulsoAndroid;
  const widgetButtons = [...document.querySelectorAll("[data-native-widget]")];

  if (android && typeof android.requestPinWidget === "function") {
    widgetButtons.forEach(button => {
      button.hidden = false;
      button.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        try {
          android.requestPinWidget();
        } catch (_) {
          // Native bridge is progressive enhancement only.
        }
      });
    });

    try {
      android.refreshWidget?.();
    } catch (_) {
      // The web experience remains fully functional without the native layer.
    }
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