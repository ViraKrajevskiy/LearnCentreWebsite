/**
 * Валидация и санитизация полей ввода на клиенте.
 * Защита от XSS и некорректных данных (ограничение длины, допустимые символы).
 * Серверная валидация обязательна — это лишь первый уровень.
 */
(function (global) {
  'use strict';

  var MAX_NAME = 255;
  var MAX_NAME_SHORT = 50;
  var MAX_EMAIL = 254;
  var MAX_PHONE = 20;
  var MAX_TELEGRAM = 128;
  var MAX_TEXT = 10000;
  var MAX_TITLE = 255;

  function sanitizeName(val, maxLen) {
    if (val == null) return '';
    var s = String(val).trim().replace(/[<>"'&]/g, '');
    return s.slice(0, maxLen != null ? maxLen : MAX_NAME);
  }

  function sanitizeEmail(val) {
    if (val == null) return '';
    return String(val).trim().toLowerCase().slice(0, MAX_EMAIL);
  }

  function sanitizePhone(val) {
    if (val == null) return '';
    return String(val).replace(/[^0-9\s\+\-\(\)]/g, '').trim().slice(0, MAX_PHONE);
  }

  function sanitizeTelegram(val) {
    if (val == null) return '';
    return String(val).trim().replace(/^@/, '').replace(/[^\w@]/g, '').slice(0, MAX_TELEGRAM);
  }

  function sanitizeText(val, maxLen) {
    if (val == null) return '';
    var s = String(val).trim().replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '');
    return s.slice(0, maxLen != null ? maxLen : MAX_TEXT);
  }

  function sanitizeTitle(val) {
    return sanitizeName(val, MAX_TITLE);
  }

  /** Применить санитизацию к полю при blur и при вводе (ограничение длины и символов). */
  function bindSanitize(el, fn) {
    if (!el) return;
    function apply() {
      var v = fn(el.value);
      if (v !== el.value) {
        var pos = el.selectionStart;
        el.value = v;
        el.setSelectionRange(Math.min(pos, v.length), Math.min(pos, v.length));
      }
    }
    el.addEventListener('blur', apply);
    el.addEventListener('input', apply);
  }

  global.InputValidation = {
    sanitizeName: sanitizeName,
    sanitizeEmail: sanitizeEmail,
    sanitizePhone: sanitizePhone,
    sanitizeTelegram: sanitizeTelegram,
    sanitizeText: sanitizeText,
    sanitizeTitle: sanitizeTitle,
    bindSanitize: bindSanitize,
    MAX_NAME: MAX_NAME,
    MAX_EMAIL: MAX_EMAIL,
    MAX_PHONE: MAX_PHONE,
    MAX_TEXT: MAX_TEXT,
    MAX_TITLE: MAX_TITLE,
  };
})(typeof window !== 'undefined' ? window : this);
