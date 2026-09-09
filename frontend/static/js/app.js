"use strict";

const clock = document.querySelector("#clock");

function updateClock() {
  clock.textContent = new Intl.DateTimeFormat([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date());
}

function setText(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.textContent = value;
}

function updateSystemStatus(status) {
  setText("#system-status", status.system_status.toUpperCase());
  setText("#health-status", status.system_health.status.toUpperCase());
  setText("#health-database", status.system_health.components.database.toUpperCase());
  setText("#health-storage", status.system_health.components.storage.toUpperCase());
  setText("#health-application", status.system_health.components.application.toUpperCase());
  setText("#known-presence", status.known_presence);
  setText("#unrecognized-events", status.unrecognized_events);
  setText("#open-incidents", status.open_incidents);
}

function updateCameraStatus(camera) {
  const ready = camera.status === "ONLINE";
  setText("#camera-engine-status", ready ? "READY" : "OFFLINE");
  setText("#camera-control-status", ready ? "READY" : "OFFLINE");
  setText("#frames-received", camera.frames_received);
  const vision = camera.vision || {};
  setText("#people-detected", vision.person_count ?? 0);
  setText("#current-occupancy", vision.person_count ?? 0);
  setText("#processing-latency", vision.processing_latency_ms == null ? "--" : `${vision.processing_latency_ms} ms`);
  setText("#processing-rate", vision.processing_rate_fps == null ? "-- FPS processing rate" : `${Number(vision.processing_rate_fps).toFixed(1)} FPS processing rate`);
  setText("#vision-status", vision.status || "STANDBY");
  setText("#person-detection-status", vision.status || "STANDBY");
  setText("#vision-error", vision.status === "UNAVAILABLE" ? "Vision model unavailable" : (vision.error || "No identity claim is made by person detection."));
}

async function pollTelemetry() {
  const [cameraResponse, systemResponse] = await Promise.all([
    fetch("/api/camera/test", { cache: "no-store" }),
    fetch("/api/system/status", { cache: "no-store" }),
  ]);
  if (cameraResponse.ok) updateCameraStatus(await cameraResponse.json());
  if (systemResponse.ok) updateSystemStatus(await systemResponse.json());
}

updateClock();
window.setInterval(updateClock, 1000);
pollTelemetry().catch(() => {});
window.setInterval(() => pollTelemetry().catch(() => {}), 2000);
