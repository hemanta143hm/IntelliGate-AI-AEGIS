"use strict";

const clock = document.querySelector("#clock");
function updateClock() {
  clock.textContent = new Intl.DateTimeFormat([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date());
}
updateClock();
window.setInterval(updateClock, 1000);
