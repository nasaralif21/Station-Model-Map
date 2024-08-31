// JavaScript to inject custom CSS into the head of the document
var link = document.createElement("link");

link.rel = "stylesheet";
link.href = "/static/style.css";
document.head.appendChild(link);
function onMarkerClick(code, time_stamp) {
  console.log({ time_stamp });
  fetch(
    `https://web-production-7bb07.up.railway.app/generate_svg?code=${code}&timestamp=${time_stamp}`
  )
    .then((response) => response.text())
    .then((data) => {
      console.log(data);
      const element = document.getElementById(`model${code}`);

      if (element) {
        element.innerHTML = `<div class="svg-container">${data}</div>`;
      } else {
        console.error(`Element not found: station-model-${code}`);
      }
    });
}

var timestampSelector = document.createElement("select");
timestampSelector.className = "timestamp-selector";
document.body.appendChild(timestampSelector);

var currentTimestamp = window.location.pathname.split("/").pop();

fetch("https://web-production-7bb07.up.railway.app/list_html_files")
  .then((response) => response.json())
  .then((htmlFiles) => {
    htmlFiles.forEach((file) => {
      var timestamp = file.replace(".html", "");
      var option = document.createElement("option");
      option.value = timestamp;
      option.textContent = timestamp;
      timestampSelector.appendChild(option);
    });
    if (currentTimestamp) {
      timestampSelector.value = currentTimestamp;
    }
  });

timestampSelector.addEventListener("change", function () {
  var selectedTimestamp = this.value;
  window.location.href = `https://web-production-7bb07.up.railway.app/${selectedTimestamp}`;
});
