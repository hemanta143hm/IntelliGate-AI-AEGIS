"use strict";

const video = document.querySelector("#camera-video");
const cameraSelect = document.querySelector("#camera-select");
const startButton = document.querySelector("#start-camera");
const stopButton = document.querySelector("#stop-camera");
const snapshotButton = document.querySelector("#snapshot");
const videoEmpty = document.querySelector("#video-empty");
const feedTag = document.querySelector("#feed-tag");
const cameraStatus = document.querySelector("#camera-status");
const statusDetail = document.querySelector("#status-detail");
const healthDot = document.querySelector("#health-dot");
const permissionState = document.querySelector("#permission-state");
const cameraMessage = document.querySelector("#camera-message");
const cameraName = document.querySelector("#camera-name");
const connectionState = document.querySelector("#connection-state");
const processingState = document.querySelector("#processing-state");
const resolution = document.querySelector("#resolution");
const fps = document.querySelector("#fps");
const framesSent = document.querySelector("#frames-sent");

let stream = null;
let uploadTimer = null;
let frameCount = 0;
let frameWindowStart = 0;
let lastFrameTime = 0;
let videoFrameHandle = null;

function setStatus(status, detail) {
  cameraStatus.textContent = status;
  statusDetail.textContent = detail;
  healthDot.className = `status-dot status-${status.toLowerCase()}`;
  feedTag.textContent = status === "ONLINE" ? "LIVE" : "NO SIGNAL";
}

function setPermission(state, message) {
  permissionState.textContent = state;
  cameraMessage.textContent = message;
}

function describeCameraError(error) {
  const messages = {
    NotAllowedError: "Camera permission was denied. Allow access in the browser site settings and try again.",
    PermissionDeniedError: "Camera permission was denied. Allow access in the browser site settings and try again.",
    NotFoundError: "No camera is available. Connect a camera and refresh the device list.",
    DevicesNotFoundError: "No camera is available. Connect a camera and refresh the device list.",
    NotReadableError: "The selected camera is unavailable or already in use.",
    OverconstrainedError: "The selected camera is no longer available. Refresh the device list.",
    SecurityError: "Camera access is blocked by the browser security policy.",
  };
  return messages[error.name] || `Camera could not start: ${error.message || "unsupported browser or device"}`;
}

async function enumerateCameras() {
  if (!navigator.mediaDevices?.enumerateDevices) {
    setPermission("UNSUPPORTED", "This browser does not support camera enumeration.");
    cameraSelect.replaceChildren(new Option("Browser camera API unavailable", ""));
    startButton.disabled = true;
    return;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter((device) => device.kind === "videoinput");
    const previous = cameraSelect.value;
    cameraSelect.replaceChildren();
    cameras.forEach((device, index) => {
      const label = device.label || `Camera ${index + 1}`;
      cameraSelect.append(new Option(label, device.deviceId));
    });
    if (!cameras.length) {
      cameraSelect.append(new Option("No camera detected", ""));
      setPermission("NO CAMERA", "No browser video input is currently available.");
      startButton.disabled = true;
      return;
    }
    cameraSelect.value = cameras.some((device) => device.deviceId === previous) ? previous : cameras[0].deviceId;
    cameraName.textContent = cameraSelect.selectedOptions[0].textContent;
    startButton.disabled = false;
  } catch (error) {
    setPermission("ERROR", `Unable to enumerate cameras: ${error.message}`);
  }
}

function updateCameraName() {
  cameraName.textContent = cameraSelect.selectedOptions[0]?.textContent || "No camera selected";
}

function updateFps(timestamp) {
  if (lastFrameTime) {
    frameCount += 1;
    if (!frameWindowStart) frameWindowStart = timestamp;
    const elapsed = timestamp - frameWindowStart;
    if (elapsed >= 1000) {
      fps.textContent = `${Math.round((frameCount * 1000) / elapsed)} FPS`;
      frameCount = 0;
      frameWindowStart = timestamp;
    }
  }
  lastFrameTime = timestamp;
  if (video.requestVideoFrameCallback) videoFrameHandle = video.requestVideoFrameCallback(updateFps);
}

function updateDimensions() {
  resolution.textContent = video.videoWidth && video.videoHeight ? `${video.videoWidth} x ${video.videoHeight}` : "-- x --";
}

function stopFps() {
  if (videoFrameHandle && video.cancelVideoFrameCallback) video.cancelVideoFrameCallback(videoFrameHandle);
  videoFrameHandle = null;
  lastFrameTime = 0;
  frameCount = 0;
  frameWindowStart = 0;
  fps.textContent = "--";
}

function stopCamera(finalStatus = "STOPPED", detail = "Camera stream stopped") {
  if (uploadTimer) window.clearInterval(uploadTimer);
  uploadTimer = null;
  stopFps();
  if (stream) stream.getTracks().forEach((track) => track.stop());
  stream = null;
  video.srcObject = null;
  videoEmpty.hidden = false;
  document.querySelector("#recording-indicator").classList.remove("is-visible");
  startButton.disabled = !cameraSelect.value;
  stopButton.disabled = true;
  snapshotButton.disabled = true;
  connectionState.textContent = "Not connected";
  processingState.textContent = "Idle";
  setStatus(finalStatus, detail);
}

async function startCamera() {
  if (!window.isSecureContext && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
    setStatus("ERROR", "Camera access requires HTTPS or localhost.");
    setPermission("SECURE CONTEXT", "Open this application through HTTPS in the browser.");
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus("ERROR", "This browser does not support MediaDevices camera access.");
    setPermission("UNSUPPORTED", "Use a current browser with WebRTC support.");
    return;
  }
  stopCamera();
  setStatus("REQUESTING", "Requesting camera permission");
  setPermission("REQUESTING", "Approve camera access in the browser prompt.");
  try {
    const constraints = { video: cameraSelect.value ? { deviceId: { exact: cameraSelect.value } } : true, audio: false };
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream;
    await video.play();
    setStatus("ONLINE", "Live camera stream active");
    setPermission("GRANTED", "Camera permission is active for this tab.");
    connectionState.textContent = "Browser stream online";
    processingState.textContent = "Waiting for frame";
    videoEmpty.hidden = true;
    document.querySelector("#recording-indicator").classList.add("is-visible");
    startButton.disabled = true;
    stopButton.disabled = false;
    snapshotButton.disabled = false;
    updateDimensions();
    if (video.requestVideoFrameCallback) videoFrameHandle = video.requestVideoFrameCallback(updateFps);
    uploadTimer = window.setInterval(sendFrame, 2000);
    video.srcObject.getVideoTracks()[0].addEventListener("ended", () => {
      connectionState.textContent = "Camera disconnected";
      stopCamera("ERROR", "Camera disconnected. Select a device and restart.");
    });
    await sendFrame();
  } catch (error) {
    stream = null;
    setStatus("ERROR", describeCameraError(error));
    setPermission(error.name === "NotAllowedError" ? "DENIED" : "ERROR", describeCameraError(error));
    connectionState.textContent = "Not connected";
  }
}

function captureBlob() {
  if (!video.videoWidth || !video.videoHeight) return Promise.resolve(null);
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
}

async function sendFrame() {
  const blob = await captureBlob();
  if (!blob) return;
  processingState.textContent = "Sending frame";
  try {
    const response = await fetch("/api/camera/frame", { method: "POST", headers: { "Content-Type": "image/jpeg" }, body: blob });
    if (!response.ok) throw new Error(`Backend returned ${response.status}`);
    const result = await response.json();
    framesSent.textContent = result.frames_received;
    connectionState.textContent = "Backend connected";
    processingState.textContent = "Frame accepted";
  } catch (error) {
    connectionState.textContent = "Backend unavailable";
    processingState.textContent = "Transport error";
  }
}

async function snapshot() {
  const blob = await captureBlob();
  if (!blob) return;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `aegis-snapshot-${new Date().toISOString().replaceAll(":", "-")}.jpg`;
  link.click();
  URL.revokeObjectURL(url);
}

startButton.addEventListener("click", startCamera);
stopButton.addEventListener("click", stopCamera);
snapshotButton.addEventListener("click", snapshot);
cameraSelect.addEventListener("change", updateCameraName);
if (navigator.mediaDevices?.addEventListener) navigator.mediaDevices.addEventListener("devicechange", enumerateCameras);
enumerateCameras();
