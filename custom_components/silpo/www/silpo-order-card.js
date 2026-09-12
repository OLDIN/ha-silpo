/**
 * Silpo Order Card — гарний степер статусу доставки замовлення Сільпо.
 * Горизонтальна лінія з іконками-кроками; заповнюється до поточного статусу.
 *
 *   type: custom:silpo-order-card
 *   entity: sensor.silpo_order_status
 *   eta_entity: sensor.silpo_courier_eta            (опційно)
 *   distance_entity: sensor.silpo_courier_distance  (опційно)
 */

const PINK = "#e6007e";
const ICONS = {
  receipt: "M13,9H18.5L13,3.5V9M6,2H14L20,8V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V4A2,2 0 0,1 6,2M15,18V16H6V18H15M18,14V12H6V14H18Z",
  cart: "M17,18A2,2 0 0,1 19,20A2,2 0 0,1 17,22A2,2 0 0,1 15,20A2,2 0 0,1 17,18M1,2H4.27L5.21,4H20A1,1 0 0,1 21,5C21,5.17 20.95,5.34 20.88,5.5L17.3,11.97C16.96,12.58 16.3,13 15.55,13H8.1L7.2,14.63L7.17,14.75A0.25,0.25 0 0,0 7.42,15H19V17H7C5.89,17 5,16.1 5,15C5,14.65 5.09,14.32 5.24,14.04L6.6,11.59L3,4H1V2M7,18A2,2 0 0,1 9,20A2,2 0 0,1 7,22A2,2 0 0,1 5,20A2,2 0 0,1 7,18Z",
  package: "M12,2L2,7V17L12,22L22,17V7L12,2M12,4.15L18.5,7.5L12,10.85L5.5,7.5L12,4.15M4,8.83L11,12.5V19.17L4,15.5V8.83M13,19.17V12.5L20,8.83V15.5L13,19.17Z",
  truck: "M3,4A2,2 0 0,0 1,6V17H3A3,3 0 0,0 6,20A3,3 0 0,0 9,17H15A3,3 0 0,0 18,20A3,3 0 0,0 21,17H23V12L20,8H17V4M17,9.5H19.5L21.47,12H17M6,15.5A1.5,1.5 0 0,1 7.5,17A1.5,1.5 0 0,1 6,18.5A1.5,1.5 0 0,1 4.5,17A1.5,1.5 0 0,1 6,15.5M18,15.5A1.5,1.5 0 0,1 19.5,17A1.5,1.5 0 0,1 18,18.5A1.5,1.5 0 0,1 16.5,17A1.5,1.5 0 0,1 18,15.5Z",
  check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
};
const STEPS = [
  { key: "new", label: "Нове", icon: "receipt" },
  { key: "collecting", label: "Збираємо", icon: "cart" },
  { key: "collected", label: "Зібрано", icon: "package" },
  { key: "delivery_in_progress", label: "У дорозі", icon: "truck" },
  { key: "received", label: "Доставлено", icon: "check" },
];
const FINAL_BAD = { returned: "Замовлення повернено", canceled: "Замовлення скасовано" };

const svgIcon = (path, color) =>
  `<svg viewBox="0 0 24 24" style="width:22px;height:22px;fill:${color};"><path d="${path}"/></svg>`;

// Екранування значень з API/сенсорів перед вставкою в innerHTML (захист від XSS).
const esc = (v) =>
  v == null ? "" : String(v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

class SilpoOrderCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Вкажіть entity: sensor.silpo_order_status");
    this.config = config;
  }
  set hass(hass) { this._hass = hass; this._render(); }
  getCardSize() { return 3; }

  _s(id) { const s = id && this._hass?.states[id]; return s ? s.state : null; }
  _a(id, a) { const s = id && this._hass?.states[id]; return s?.attributes?.[a] ?? null; }

  _render() {
    if (!this._hass) return;
    const st = this._hass.states[this.config.entity];
    const status = st ? st.state : "unknown";
    const number = st?.attributes?.order_number;
    const slotFrom = st?.attributes?.time_slot_from;
    const slotTo = st?.attributes?.time_slot_to;
    const eta = this._s(this.config.eta_entity);
    const distM = this._s(this.config.distance_entity);
    const distKm = this._a(this.config.distance_entity, "distance_km");

    if (!this.card) { this.card = document.createElement("ha-card"); this.appendChild(this.card); }

    // Немає активного замовлення (unknown/unavailable/порожньо) — empty state
    const known = STEPS.some((s) => s.key === status) || FINAL_BAD[status];
    if (!known) {
      this.card.innerHTML = `
        <div style="padding:32px 16px;text-align:center;color:var(--secondary-text-color,#888);">
          <svg viewBox="0 0 24 24" style="width:40px;height:40px;fill:var(--divider-color,#cfcfcf);">
            <path d="${ICONS.cart}"/></svg>
          <div style="margin-top:10px;font-size:15px;font-weight:600;">Немає активних замовлень</div>
          <div style="margin-top:4px;font-size:12px;">Тут з'явиться статус, коли оформите доставку в Сільпо</div>
        </div>`;
      return;
    }

    let activeIdx = STEPS.findIndex((s) => s.key === status);
    const bad = FINAL_BAD[status];
    if (bad) activeIdx = -1;
    const pct = activeIdx <= 0 ? 0 : (activeIdx / (STEPS.length - 1)) * 100;

    const fmt = (iso) => { try { return new Date(iso).toLocaleTimeString("uk-UA",{hour:"2-digit",minute:"2-digit"}); } catch { return null; } };
    const slot = slotFrom && slotTo ? `${fmt(slotFrom)}–${fmt(slotTo)}` : null;

    const dots = STEPS.map((s, i) => {
      const done = i < activeIdx, current = i === activeIdx;
      const filled = done || current;
      const bg = filled ? PINK : "var(--divider-color,#e0e0e0)";
      const icoColor = filled ? "#fff" : "var(--secondary-text-color,#9e9e9e)";
      const size = current ? 46 : 40;
      const ring = current ? `box-shadow:0 0 0 5px rgba(230,0,126,.20);` : "";
      const anim = current ? "animation:silpoPulse 1.6s ease-in-out infinite;" : "";
      const ico = done ? svgIcon(ICONS.check, "#fff") : svgIcon(ICONS[s.icon], icoColor);
      return `
        <div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:0;z-index:1;">
          <div style="width:${size}px;height:${size}px;border-radius:50%;background:${bg};
               display:flex;align-items:center;justify-content:center;transition:all .35s;${ring}${anim}">
            ${ico}
          </div>
          <div style="margin-top:8px;font-size:11.5px;text-align:center;line-height:1.25;
               color:${current ? PINK : "var(--secondary-text-color,#888)"};
               font-weight:${current ? 700 : 500};">${s.label}</div>
        </div>`;
    }).join("");

    const badges = [];
    if (status === "delivery_in_progress") {
      if (eta && eta !== "unknown") badges.push(`⏱️ ~${esc(eta)} хв`);
      if (distKm) badges.push(`📍 ${esc(distKm)} км`);
      else if (distM && distM !== "unknown") badges.push(`📍 ${esc(Math.round(distM))} м`);
    }
    if (slot) badges.push(`🕐 ${esc(slot)}`);

    const header = number ? `Замовлення №${esc(number)}` : "Замовлення Сільпо";
    const sub = status === "delivery_in_progress"
      ? `<span style="font-size:12px;color:${PINK};font-weight:600;">кур'єр у дорозі 🚚</span>`
      : status === "received"
      ? `<span style="font-size:12px;color:#2e7d32;font-weight:600;">доставлено ✅</span>` : "";

    const badBanner = bad
      ? `<div style="margin-top:14px;padding:10px;border-radius:10px;text-align:center;
           background:rgba(244,67,54,.12);color:#f44336;font-weight:600;">${bad}</div>` : "";

    this.card.innerHTML = `
      <style>@keyframes silpoPulse{0%,100%{box-shadow:0 0 0 5px rgba(230,0,126,.20)}50%{box-shadow:0 0 0 9px rgba(230,0,126,.08)}}</style>
      <div style="padding:18px 16px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:22px;">
          <span style="font-size:17px;font-weight:700;">${header}</span>${sub}
        </div>
        <div style="position:relative;padding:0 6px;">
          <div style="position:absolute;top:20px;left:10%;right:10%;height:4px;
               background:var(--divider-color,#e0e0e0);border-radius:3px;"></div>
          <div style="position:absolute;top:20px;left:10%;height:4px;border-radius:3px;
               background:linear-gradient(90deg,#ff7ac2,${PINK});transition:width .5s ease;
               width:calc(${pct}% * 0.8);"></div>
          <div style="display:flex;justify-content:space-between;position:relative;">${dots}</div>
        </div>
        ${badges.length ? `<div style="margin-top:20px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">
             ${badges.map((b)=>`<span style="background:rgba(230,0,126,.10);color:${PINK};
               padding:6px 12px;border-radius:20px;font-size:13px;font-weight:600;">${b}</span>`).join("")}</div>` : ""}
        ${badBanner}
      </div>`;
  }
}

customElements.define("silpo-order-card", SilpoOrderCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "silpo-order-card", name: "Silpo Order Card",
  description: "Степер статусу доставки замовлення Сільпо" });
console.info("%c SILPO-ORDER-CARD %c завантажено", "background:#e6007e;color:#fff;border-radius:3px", "");
