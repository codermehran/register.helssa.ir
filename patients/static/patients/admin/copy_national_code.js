(function () {
  "use strict";

  function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(value);
    }

    var textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();

    try {
      document.execCommand("copy");
      return Promise.resolve();
    } catch (error) {
      return Promise.reject(error);
    } finally {
      textarea.remove();
    }
  }

  function getTenDigitCode(input) {
    var value = (input.value || "").trim();
    var digits = value.replace(/\D/g, "");
    return digits.length === 10 ? digits : "";
  }

  function setButtonState(button, input) {
    var canCopy = Boolean(getTenDigitCode(input));
    button.disabled = !canCopy;
    button.title = canCopy ? "کپی کد ملی" : "کد ملی باید ۱۰ رقمی باشد";
  }

  function createCopyButton(input) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "national-code-copy-button";
    button.setAttribute("aria-label", "کپی کد ملی");
    button.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
      '<rect x="8" y="8" width="11" height="11" rx="2"></rect>' +
      '<path d="M5 15V6a1 1 0 0 1 1-1h9"></path>' +
      "</svg>" +
      '<span class="national-code-copy-button__status">کپی شد</span>';

    button.addEventListener("click", function () {
      var code = getTenDigitCode(input);
      if (!code) {
        setButtonState(button, input);
        return;
      }

      copyText(code).then(function () {
        button.classList.add("national-code-copy-button--copied");
        window.setTimeout(function () {
          button.classList.remove("national-code-copy-button--copied");
        }, 1200);
      });
    });

    input.addEventListener("input", function () {
      setButtonState(button, input);
    });

    setButtonState(button, input);
    return button;
  }

  function initNationalCodeCopy() {
    var inputs = document.querySelectorAll("[data-copy-national-code='true']");

    inputs.forEach(function (input) {
      if (input.dataset.copyButtonReady === "true") {
        return;
      }

      var wrapper = document.createElement("span");
      wrapper.className = "national-code-copy";
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
      wrapper.appendChild(createCopyButton(input));
      input.dataset.copyButtonReady = "true";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNationalCodeCopy);
  } else {
    initNationalCodeCopy();
  }
})();
