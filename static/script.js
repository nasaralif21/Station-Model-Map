// JavaScript to inject custom CSS into the head of the document
var link = document.createElement("link");

link.rel = "stylesheet";
link.href = "/static/style.css";
document.head.appendChild(link);

var link = document.createElement("link");
link.rel = "icon";
link.type = "image/x-icon";
link.href = "/static/favicon.ico";
document.head.appendChild(link);

var title = document.createElement("title");
title.textContent = "Weather Charts";
document.head.appendChild(title);
map = window.map_id;
console.log(map);

var timestampSelector = document.createElement("select");
timestampSelector.className = "timestamp-selector";
document.body.appendChild(timestampSelector);

var timeSelector = document.createElement("select");
timeSelector.className = "time-selector";
document.body.appendChild(timeSelector);

var loadButton = document.createElement("button");
loadButton.className = "button";
loadButton.textContent = "View Chart";
document.body.appendChild(loadButton);

var currentTimestamp = window.location.pathname.split("/").pop();
console.log(currentTimestamp);

var htmlFiles = [];
var availableTimes = {};

fetch("http://127.0.0.1:5000/list_html_files")
  .then((response) => response.json())
  .then((files) => {
    htmlFiles = files;
    htmlFiles.forEach((file) => {
      var timestamp = file.replace(".html", "");
      var year = timestamp.slice(0, 4);
      var month = timestamp.slice(4, 6);
      var day = timestamp.slice(6, 8);
      var hours = timestamp.slice(8, 10);
      var date = `${year}-${month}-${day}`;

      // If date is not in availableTimes, add it
      if (!availableTimes[date]) {
        availableTimes[date] = [];
        var dateOption = document.createElement("option");
        dateOption.value = date;
        dateOption.textContent = `${day}/${month}/${year}`;
        timestampSelector.appendChild(dateOption);
      }
      // Add time to the date
      availableTimes[date].push(hours);
    });

    // var dateOption = document.createElement("option");
    // dateOption.value = `${year}-${month}-${day}`;
    // dateOption.textContent = `${day}/${month}/${year}`;
    // timestampSelector.appendChild(dateOption);

    // var timeOption = document.createElement("option");
    // timeOption.value = hour;
    // timeOption.textContent = hour;
    // timeSelector.appendChild(timeOption);
  });
if (currentTimestamp) {
  var currentDate = currentTimestamp.slice(0, 8);
  var currentHours = currentTimestamp.slice(8, 10);
  var formattedDate = `${currentDate.slice(0, 4)}-${currentDate.slice(
    4,
    6
  )}-${currentDate.slice(6, 8)}`;
  timestampSelector.value = formattedDate;
  updateTimeSelector(formattedDate); // Populate time selector
  timeSelector.value = currentHours;
}

window.addEventListener("load", function () {
  var selectedData = timestampSelector.value;
  if (currentTimestamp) {
    var currentDate = currentTimestamp.slice(0, 8);
    var currentHours = currentTimestamp.slice(8, 10);
    var formattedDate = `${currentDate.slice(0, 4)}-${currentDate.slice(
      4,
      6
    )}-${currentDate.slice(6, 8)}`;
    timestampSelector.value = formattedDate;
    updateTimeSelector(formattedDate); // Populate time selector
    timeSelector.value = currentHours;
  }
});

timestampSelector.addEventListener("change", function () {
  updateTimeSelector(this.value);
});

function updateTimeSelector(selectedDate) {
  timeSelector.innerHTML = ""; // Clear existing options
  var formattedDate = selectedDate.replace(/-/g, "");
  console.log("Selected Date: " + formattedDate);

  if (availableTimes[selectedDate]) {
    availableTimes[selectedDate].forEach((hours) => {
      var timeOption = document.createElement("option");
      timeOption.value = hours;
      timeOption.textContent = hours;
      timeSelector.appendChild(timeOption);
    });
  }
}

loadButton.addEventListener("click", function () {
  var selectedDate = timestampSelector.value.replace(/-/g, "");
  console.log(selectedDate);

  var selectedTime = timeSelector.value;
  var selectedTimestamp = selectedDate + selectedTime;
  window.location.href = `http://127.0.0.1:5000/${selectedTimestamp}`;
});

function onMarkerClick(code, time_stamp) {
  console.log({ time_stamp });
  fetch(
    "http://127.0.0.1:5000/generate_svg?code=" +
      code +
      "&timestamp=" +
      time_stamp
  )
    .then((response) => response.json()) // Parse the JSON response
    .then((data) => {
      var popupContent = document.getElementById("popup-content-" + code);

      if (popupContent) {
        // Extract SVG data and additional data
        var svgData = data.svg;
        var additionalData = data.additional_data;

        // Update the popup content with the SVG data and additional information
        var updatedContent = `
          <b>${additionalData.place_name}</b><br>
          Temp: ${additionalData.air_temp ?? "N/A"}&deg;C<br>
          Rain: ${additionalData.pressure ?? "N/A"} mm<br>
          Dew Point: ${additionalData.dew_point ?? "N/A"}&deg;C<br>
          Wind: ${additionalData.wind_speed_knots ?? "N/A"} knots<br>
          <div class="svg-container">${svgData}</div>
          
        `;
        popupContent.innerHTML = updatedContent;
      } else {
        console.error("Popup content element not found: popup-content-" + code);
      }
    })
    .catch((error) => {
      console.error("Error fetching SVG data:", error);
    });
}
