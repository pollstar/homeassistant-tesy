// Unit tests for the pure helpers of the Lovelace card: node --test tests/js
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  tempRole, angleFor, tempFromPoint, scheduleCalls, heaterView, deviceEntities, DAYS,
  loadedVersion, staleAction, pickLang, cardSupported, markReloaded, errorView, numberLocale,
} from "../../custom_components/tesy/frontend/tesy-boiler-card.js";

test("temperature roles", () => {
  assert.equal(tempRole(null), "empty");
  assert.equal(tempRole(14), "off");
  assert.equal(tempRole(15), "t20");
  assert.equal(tempRole(50), "t55");
  assert.equal(tempRole(75), "t75");
});

test("dial angle and drag point round-trip", () => {
  assert.equal(angleFor(14), -135);
  assert.equal(angleFor(75), 135);
  for (const t of [15, 40, 60, 75]) {
    const a = (angleFor(t) * Math.PI) / 180;
    const x = 140 + 116 * Math.sin(a), y = 140 - 116 * Math.cos(a);
    assert.equal(tempFromPoint(x, y), t);
  }
  // the gap at the bottom clamps to the nearer end, never below 15
  assert.equal(tempFromPoint(100, 279), 15);
  assert.equal(tempFromPoint(180, 279), 75);
});

test("schedule calls group identical days and skip unchanged ones", () => {
  const p1 = [14,14,50,50,50,50,25,25,25,25,40,40,75,75,75,75,50,50,50,50,50,50,14,14];
  const orig = { 1: Object.fromEntries(DAYS.map((d) => [d, p1.slice()])) };
  const edit = JSON.parse(JSON.stringify(orig));
  const mo = p1.slice(); mo[6] = 60;
  for (const d of ["mo", "tu", "we"]) edit[1][d] = mo.slice();
  edit[1].su[0] = 20;
  assert.deepEqual(scheduleCalls(orig, edit), [
    { program: 1, days: ["mo", "tu", "we"], temperatures: mo },
    { program: 1, days: ["su"], temperatures: [20, ...p1.slice(1)] },
  ]);
  assert.deepEqual(scheduleCalls(orig, orig), []);
});

test("heater view from the water_heater state", () => {
  const st = (state, attrs) => ({ state, attributes: attrs });
  // P1 at night: 14 °C = heating off
  let v = heaterView(st("p1", { temperature: 14, current_temperature: 42.3, is_heating: false }), false);
  assert.equal(v.status, "heatOff"); assert.equal(v.off, true); assert.equal(v.manual, false);
  // manual, heating, Boost
  v = heaterView(st("performance", { temperature: 75, current_temperature: 42.3, is_heating: true }), true);
  assert.equal(v.status, "heatingBoost"); assert.equal(v.manual, true);
  // powered off / unavailable
  assert.equal(heaterView(st("off", {}), false).status, "off");
  assert.equal(heaterView(st("unavailable", {}), false).status, "unavailable");
  assert.equal(heaterView(undefined, false).available, false);
});

test("device entities by translation key with entity_id fallback", () => {
  const hass = {
    entities: {
      "water_heater.b_heater": { entity_id: "water_heater.b_heater", device_id: "d1", platform: "tesy" },
      "switch.b_boost": { entity_id: "switch.b_boost", device_id: "d1", translation_key: "boost" },
      "sensor.b_energy_consumed_resettable": { entity_id: "sensor.b_energy_consumed_resettable", device_id: "d1" },
      "sensor.b_energy_consumed": { entity_id: "sensor.b_energy_consumed", device_id: "d1" },
      "switch.other_boost": { entity_id: "switch.other_boost", device_id: "d2", translation_key: "boost" },
    },
    devices: { d1: { name: "Boiler", model: "ModEco 2" } },
  };
  const e = deviceEntities(hass, "water_heater.b_heater");
  assert.equal(e.boost, "switch.b_boost");
  assert.equal(e.energy_consumed, "sensor.b_energy_consumed");
  assert.equal(e.energy_consumed_resettable, "sensor.b_energy_consumed_resettable");
  assert.equal(e.device.model, "ModEco 2");
});

test("stale page detection reloads once, then shows a banner", () => {
  assert.equal(loadedVersion("https://ha.example/tesy_static/tesy-boiler-card.js?v=183e0b81"), "183e0b81");
  assert.equal(loadedVersion("https://ha.example/local/tesy-boiler-card.js"), null);
  assert.equal(loadedVersion("not a url"), null);
  assert.equal(staleAction("aaaa", "aaaa", null), "ok");
  assert.equal(staleAction(null, "bbbb", null), "ok");        // loaded without ?v= (manual resource)
  assert.equal(staleAction("aaaa", undefined, null), "ok");   // integration without the endpoint
  assert.equal(staleAction("aaaa", "bbbb", null), "reload");
  assert.equal(staleAction("aaaa", "bbbb", "bbbb"), "banner"); // already reloaded for this version
  assert.equal(staleAction("aaaa", "cccc", "bbbb"), "reload"); // newer update again
});

test("card language follows the HA UI language, English otherwise", () => {
  assert.equal(pickLang("ru"), "ru");
  assert.equal(pickLang("uk"), "uk");
  assert.equal(pickLang("en-GB"), "en");
  assert.equal(pickLang("uk_UA"), "uk");
  assert.equal(pickLang("de"), "en");
  assert.equal(pickLang("zh-Hans"), "en");
  assert.equal(pickLang(undefined), "en");
  assert.equal(pickLang("constructor"), "en");
});

test("card support follows the tesy_features attribute", () => {
  assert.equal(cardSupported({ state: "performance", attributes: { tesy_features: ["card", "schedule"] } }), true);
  assert.equal(cardSupported({ state: "performance", attributes: { tesy_features: ["schedule"] } }), false);
  assert.equal(cardSupported({ state: "performance", attributes: {} }), false);
  assert.equal(cardSupported({ state: "unavailable", attributes: {} }), null);
  assert.equal(cardSupported(undefined), null);
});

test("reload marker: no reload loop when storage is blocked", () => {
  const store = new Map();
  const ok = { setItem: (k, v) => store.set(k, v), getItem: (k) => store.get(k) ?? null };
  assert.equal(markReloaded(ok, "abc"), true);
  assert.equal(staleAction("old", "abc", ok.getItem("tesy-boiler-card-reloaded-for")), "banner");
  const blocked = { setItem: () => { throw new Error("SecurityError"); }, getItem: () => null };
  assert.equal(markReloaded(blocked, "abc"), false);
  const ignored = { setItem: () => {}, getItem: () => null }; // e.g. a no-op storage
  assert.equal(markReloaded(ignored, "abc"), false);
});

test("error sensor: no data is not a fault", () => {
  for (const s of [undefined, null, "", "unavailable", "unknown"]) assert.deepEqual(errorView(s), { kind: "unknown", code: null });
  assert.deepEqual(errorView("00"), { kind: "ok", code: "00" });
  assert.deepEqual(errorView("0"), { kind: "ok", code: "00" });
  assert.deepEqual(errorView("03"), { kind: "error", code: "03" });
  assert.deepEqual(errorView("3"), { kind: "error", code: "03" });
});

test("number locale accepts HA language codes", () => {
  assert.equal(numberLocale("uk_UA"), "uk-UA");
  assert.equal(numberLocale("ru"), "ru");
  assert.equal(numberLocale("en-GB"), "en-GB");
  for (const bad of [undefined, "", "not a locale!", "x_"]) assert.equal(numberLocale(bad), "en");
  assert.doesNotThrow(() => new Intl.NumberFormat(numberLocale("uk_UA")).format(42.5));
});
