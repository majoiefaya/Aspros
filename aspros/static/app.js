const devicesNode = document.querySelector("#devices");
const scenesNode = document.querySelector("#scenes");
const statusNode = document.querySelector("#status");
const responseNode = document.querySelector("#response");
const form = document.querySelector("#command-form");
const input = document.querySelector("#command");

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Une erreur est survenue.");
  return body;
}

function formatState(state) {
  return Object.entries(state).map(([key, value]) => {
    const labels = { power: "Alimentation", brightness: "Luminosité", temperature_celsius: "Température", battery: "Batterie", locked: "Verrouillé" };
    const suffix = key === "brightness" || key === "battery" ? " %" : key === "temperature_celsius" ? " °C" : "";
    const shown = typeof value === "boolean" ? (value ? "Oui" : "Non") : value;
    return `<li><span>${labels[key] || key}</span><strong>${shown}${suffix}</strong></li>`;
  }).join("");
}

function deviceCard(device) {
  const powered = device.state.power === "on";
  const powerControls = device.capabilities.some((item) => item.name === "turn_on");
  return `<article class="card ${powered ? "on" : ""}">
    <p class="type">${device.kind}</p>
    <h3>${device.name}</h3>
    <ul>${formatState(device.state)}</ul>
    ${powerControls ? `<div class="actions"><button onclick="deviceAction('${device.id}', '${powered ? "turn_off" : "turn_on"}')">${powered ? "Éteindre" : "Allumer"}</button></div>` : ""}
  </article>`;
}

function sceneCard(scene) {
  return `<article class="card scene"><p class="type">scène</p><h3>${scene.name}</h3><p>${scene.description}</p><button onclick="executeScene('${scene.id}')">Lancer</button></article>`;
}

async function refresh() {
  const [devices, scenes] = await Promise.all([request("/api/devices"), request("/api/scenes")]);
  devicesNode.innerHTML = devices.devices.map(deviceCard).join("");
  scenesNode.innerHTML = scenes.scenes.map(sceneCard).join("");
}

async function sendCommand(text) {
  responseNode.textContent = "ASPROS analyse ta demande…";
  try {
    const body = await request("/api/commands", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    responseNode.textContent = body.message;
    await refresh();
  } catch (error) {
    responseNode.textContent = error.message;
  }
}

window.deviceAction = async (deviceId, action) => {
  try {
    const body = await request(`/api/devices/${deviceId}/actions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
    responseNode.textContent = body.message;
    await refresh();
  } catch (error) { responseNode.textContent = error.message; }
};

window.executeScene = async (sceneId) => {
  try {
    await request(`/api/scenes/${sceneId}/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    responseNode.textContent = "Scène exécutée.";
    await refresh();
  } catch (error) { responseNode.textContent = error.message; }
};

form.addEventListener("submit", (event) => { event.preventDefault(); if (input.value.trim()) sendCommand(input.value.trim()); });
document.querySelectorAll("[data-command]").forEach((button) => button.addEventListener("click", () => { input.value = button.dataset.command; sendCommand(input.value); }));
document.querySelector("#refresh").addEventListener("click", refresh);

(async () => {
  try { await request("/api/health"); statusNode.textContent = "● En ligne"; statusNode.classList.add("online"); await refresh(); }
  catch (error) { statusNode.textContent = "● Hors ligne"; responseNode.textContent = error.message; }
})();
