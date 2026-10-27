const $ = (selector) => document.querySelector(selector);

const state = {
  scenes: [],
  gestures: [],
  scene: null,
  strategy: "C",
  events: [],
  timers: [],
  startedAt: 0,
  frame: 0,
};

const selectors = {
  scene: $("#sceneSelect"), world: $("#worldState"), constraints: $("#constraints"),
  player: $("#playerLine"), dialogue: $("#dialogue"), list: $("#planList"), count: $("#planCount"),
  timeline: $("#timeline"), playhead: $("#playhead"), stage: $(".stage"), orbit: $("#semanticOrbit"),
  scanline: $("#scanline"), runtime: $("#runtimeState"), dot: $("#stateDot"), result: $("#constraintResult"),
  policy: $("#policyValue"), pending: $("#timerValue"),
};

const functionToGesture = (fn, enforce = false) => {
  const matches = state.gestures.filter((g) => g.functions.includes(fn));
  const allowed = enforce
    ? matches.filter((g) => !state.scene.forbidden.includes(g.id) && !g.blocked.some((tag) => state.scene.state.includes(tag)))
    : matches;
  return allowed.sort((a, b) => Math.abs(a.intensity - .5) - Math.abs(b.intensity - .5))[0];
};

function buildPlan() {
  const expected = state.scene.expected;
  const duration = Math.max(2400, state.scene.dialogue.length * 72);
  if (state.strategy === "A") {
    const gesture = functionToGesture(expected[0], false);
    return gesture ? [{ ...gesture, fn: expected[0], at: 260 }] : [];
  }
  if (state.strategy === "B") {
    const beats = [];
    for (let at = 520; at < duration; at += 1100) beats.push({ id: "beat_small", fn: "rhythm", at, policy: "soft_cancel" });
    const coarse = functionToGesture(expected[0], false);
    if (coarse) beats.push({ ...coarse, fn: expected[0], at: 760, policy: "none" });
    return beats.sort((a, b) => a.at - b.at);
  }
  const gap = Math.max(540, Math.floor(duration / (expected.length + 1)));
  return expected.map((fn, index) => {
    const gesture = functionToGesture(fn, true);
    return gesture ? { ...gesture, fn, at: gap * (index + 1) } : { id: "beat_small", fn: "fallback", at: gap * (index + 1), policy: "soft_cancel" };
  });
}

function setRuntime(label, color = "var(--muted)") {
  selectors.runtime.textContent = label;
  selectors.dot.style.background = color;
  selectors.dot.style.color = color;
}

function renderScene() {
  reset(false);
  state.scene = state.scenes.find((item) => item.id === selectors.scene.value) || state.scenes[0];
  selectors.player.textContent = `“${state.scene.player}”`;
  selectors.dialogue.textContent = "I'm listening. What do you need to know?";
  selectors.world.innerHTML = [
    ["Category", state.scene.category.replace("_", " ")],
    ["Character", state.scene.state.length ? state.scene.state.join(", ") : "ready"],
    ["Interrupt", state.scene.interrupt_ms ? `${state.scene.interrupt_ms} ms` : "manual"],
  ].map(([key, value]) => `<div><dt>${key}</dt><dd>${value}</dd></div>`).join("");
  const forbidden = state.scene.forbidden.length ? state.scene.forbidden : ["No explicit blocks"];
  selectors.constraints.innerHTML = forbidden.map((item) => `<span class="${state.scene.forbidden.length ? "" : "clear"}">${item}</span>`).join("");
  state.events = buildPlan();
  renderPlan();
}

function renderPlan() {
  state.events = buildPlan();
  selectors.count.textContent = `${state.events.length} event${state.events.length === 1 ? "" : "s"}`;
  selectors.list.innerHTML = state.events.map((event, index) => `
    <li data-index="${index}"><time>${(event.at / 1000).toFixed(2)}s</time><b>${event.id}</b><em>${event.fn}</em></li>`).join("");
  selectors.timeline.querySelectorAll(".event").forEach((node) => node.remove());
  state.events.forEach((event) => {
    const node = document.createElement("i");
    node.className = `event ${event.fn.includes("warn") ? "warn" : ""} ${event.fn === "rhythm" ? "rhythm" : ""}`;
    node.style.left = `${Math.min(98, event.at / 40)}%`;
    node.style.width = `${Math.max(1.5, (event.duration_ms || 700) / 40)}%`;
    selectors.timeline.appendChild(node);
  });
  const blocked = state.events.some((event) => state.scene.forbidden.includes(event.id));
  selectors.result.className = blocked ? "" : "pass";
  selectors.result.innerHTML = `<i></i>${blocked ? "Known constraint violated" : "Authored constraints pass"}`;
  selectors.policy.textContent = state.strategy === "C" ? "per-gesture" : state.strategy === "B" ? "rhythm only" : "none";
  selectors.pending.textContent = state.events.length;
}

function fireEvent(event, index) {
  document.querySelector(`[data-index="${index}"]`)?.classList.add("fired");
  if (state.strategy === "C") selectors.orbit.classList.add("visible");
  selectors.scanline.classList.remove("active");
  void selectors.scanline.offsetWidth;
  selectors.scanline.classList.add("active");
  selectors.policy.textContent = event.policy || "none";
  selectors.pending.textContent = Math.max(0, state.events.length - index - 1);
}

function animatePlayhead() {
  const elapsed = performance.now() - state.startedAt;
  selectors.playhead.style.left = `${Math.min(100, elapsed / 40)}%`;
  if (elapsed < 4000 && selectors.stage.classList.contains("speaking")) {
    state.frame = requestAnimationFrame(animatePlayhead);
  }
}

function play() {
  reset(false);
  state.events = buildPlan();
  renderPlan();
  selectors.dialogue.textContent = state.scene.dialogue;
  selectors.stage.classList.add("speaking");
  selectors.playhead.style.opacity = "1";
  setRuntime("Speaking", "var(--jade)");
  state.startedAt = performance.now();
  state.events.forEach((event, index) => state.timers.push(setTimeout(() => fireEvent(event, index), event.at)));
  state.timers.push(setTimeout(() => {
    selectors.stage.classList.remove("speaking");
    selectors.orbit.classList.remove("visible");
    setRuntime("Listening", "var(--amber)");
  }, 4000));
  animatePlayhead();
  if (state.scene.interrupt_ms) state.timers.push(setTimeout(interrupt, state.scene.interrupt_ms));
}

function interrupt() {
  const elapsed = state.startedAt ? performance.now() - state.startedAt : 0;
  state.timers.forEach(clearTimeout);
  state.timers = [];
  cancelAnimationFrame(state.frame);
  selectors.stage.classList.remove("speaking");
  selectors.stage.classList.add("interrupted");
  selectors.orbit.classList.remove("visible");
  selectors.dialogue.textContent = state.scene.second ? `Player takes the floor: “${state.scene.second}”` : "Player takes the floor. Pending actions cancelled.";
  document.querySelectorAll(".plan-list li").forEach((node, index) => {
    if (state.events[index].at >= elapsed) node.classList.add("cancelled");
  });
  selectors.pending.textContent = "0";
  selectors.policy.textContent = state.strategy === "C" ? "soft cancel → listen" : "coarse stop";
  setRuntime("Recovering → Listening", "var(--danger)");
  setTimeout(() => selectors.stage.classList.remove("interrupted"), 650);
}

function reset(rebuild = true) {
  state.timers.forEach(clearTimeout);
  state.timers = [];
  cancelAnimationFrame(state.frame);
  selectors.stage.classList.remove("speaking", "interrupted");
  selectors.orbit.classList.remove("visible");
  selectors.scanline.classList.remove("active");
  selectors.playhead.style.opacity = "0";
  selectors.playhead.style.left = "0";
  document.querySelectorAll(".plan-list li").forEach((node) => node.classList.remove("fired", "cancelled"));
  setRuntime("Idle");
  if (rebuild && state.scene) {
    selectors.dialogue.textContent = "I'm listening. What do you need to know?";
    renderPlan();
  }
}

async function init() {
  const [scenes, gestures] = await Promise.all([
    fetch("../Data/scenarios.json").then((response) => response.json()),
    fetch("../Data/gesture_library.json").then((response) => response.json()),
  ]);
  state.scenes = scenes;
  state.gestures = gestures;
  selectors.scene.innerHTML = scenes.map((scene) => `<option value="${scene.id}">${scene.player}</option>`).join("");
  selectors.scene.value = "interrupt_01";
  renderScene();
}

document.querySelectorAll("[data-strategy]").forEach((button) => button.addEventListener("click", () => {
  state.strategy = button.dataset.strategy;
  document.querySelectorAll("[data-strategy]").forEach((item) => {
    item.classList.toggle("active", item === button);
    item.setAttribute("aria-checked", item === button ? "true" : "false");
  });
  reset(false);
  renderPlan();
}));

selectors.scene.addEventListener("change", renderScene);
$("#playButton").addEventListener("click", play);
$("#interruptButton").addEventListener("click", interrupt);
$("#resetButton").addEventListener("click", () => reset(true));
$("#devToggle").addEventListener("click", () => {
  const visible = document.body.classList.toggle("developer-view");
  $("#devToggle").setAttribute("aria-expanded", visible ? "true" : "false");
  $("#devToggle").textContent = visible ? "Return to game" : "Developer view";
});

init().catch((error) => {
  selectors.dialogue.textContent = `Demo data could not load: ${error.message}. Run through a local HTTP server.`;
  setRuntime("Load error", "var(--danger)");
});
