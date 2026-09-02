/**
 * Wrapper mínimo de comunicación con el LMS (SCORM 1.2 / SCORM 2004).
 * Busca el objeto API (SCORM 1.2) o API_1484_11 (SCORM 2004) recorriendo
 * la jerarquía de ventanas/frames, tal como exige el estándar.
 *
 * Generado por scorm-tools. Puede reemplazarse por otra librería
 * (p. ej. pipwerks SCORM API Wrapper) si se prefiere.
 */
(function (global) {
  "use strict";

  var MAX_ANCESTORS = 500;

  function findAPI(win) {
    var attempts = 0;
    while (win && attempts < MAX_ANCESTORS) {
      if (win.API_1484_11) return { api: win.API_1484_11, version: "2004" };
      if (win.API) return { api: win.API, version: "1.2" };
      if (win.parent && win.parent !== win) {
        win = win.parent;
      } else if (win.opener) {
        win = win.opener;
      } else {
        break;
      }
      attempts += 1;
    }
    return null;
  }

  var ScormAPI = {
    _handle: null,
    _connected: false,

    init: function () {
      this._handle = findAPI(global);
      if (!this._handle) {
        console.warn("[scorm-api] No se encontró un API de LMS. Ejecutando en modo standalone.");
        return false;
      }
      var ok =
        this._handle.version === "2004"
          ? this._handle.api.Initialize("")
          : this._handle.api.LMSInitialize("");
      this._connected = ok === "true" || ok === true;
      return this._connected;
    },

    _set: function (key12, key2004, value) {
      if (!this._connected) return;
      if (this._handle.version === "2004") {
        this._handle.api.SetValue(key2004, value);
      } else {
        this._handle.api.LMSSetValue(key12, value);
      }
    },

    setCompleted: function () {
      this._set("cmi.core.lesson_status", "cmi.completion_status", "completed");
    },

    setScore: function (score) {
      if (this._handle && this._handle.version === "2004") {
        this._set(null, "cmi.score.raw", String(score));
      } else {
        this._set("cmi.core.score.raw", null, String(score));
      }
    },

    commit: function () {
      if (!this._connected) return;
      this._handle.version === "2004"
        ? this._handle.api.Commit("")
        : this._handle.api.LMSCommit("");
    },

    terminate: function () {
      if (!this._connected) return;
      this.commit();
      this._handle.version === "2004"
        ? this._handle.api.Terminate("")
        : this._handle.api.LMSFinish("");
      this._connected = false;
    },
  };

  global.ScormAPI = ScormAPI;
})(window);
