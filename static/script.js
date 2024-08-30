// JavaScript to inject custom CSS into the head of the document
var link = document.createElement("link");

link.rel = "stylesheet";
link.href = "./style.css";
document.head.appendChild(link);

function onMarkerClick(code, time_stamp) {
  console.log({ time_stamp });
  fetch(
    "http://127.0.0.1:5000/generate_svg?code=" +
      code +
      "&timestamp=" +
      time_stamp
  )
    .then((response) => response.text())
    .then((data) => {
      console.log(data);
      var element = document.getElementById("model" + code);

      if (element) {
        element.innerHTML = `<div class="svg-container">${data}</div>`;
      } else {
        console.error("Element not found: station-model-" + code);
      }
    });
}
var timestampSelector = document.createElement("select");
timestampSelector.className = "timestamp-selector";
timestampSelector.innerHTML =
  '<option value="2023050315">2023-05-03 15:00</option>';
document.body.appendChild(timestampSelector);
