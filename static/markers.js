var timestampSelector = document.getElementById("timestampSelector");
var timeSelector = document.getElementById("timeSelector");
var button = document.getElementById("view-chart");
var currentTimestamp = "";
var availableTimes = {};

var now = new Date();
var utcYear = now.getUTCFullYear();
var utcMonth = String(now.getUTCMonth() + 1).padStart(2, "0"); // Months are 0-indexed
var utcDay = String(now.getUTCDate()).padStart(2, "0");
var utcHours = String(now.getUTCHours()).padStart(2, "0");

// var currenTime = `${utcYear}${utcMonth}${utcDay}00`;
var currenTime="2024090500"
fetch("/list_html_files")
  .then((response) => response.json())
  .then((files) => {
    htmlFiles = files;
    var datesSet = new Set();
    htmlFiles.forEach((file) => {
      var timestamp = file.replace(".geojson", "");
      //   console.log(timestamp);

      var year = timestamp.slice(0, 4);
      var month = timestamp.slice(4, 6);
      var day = timestamp.slice(6, 8);
      var hours = timestamp.slice(8, 10);
      var date = `${year}-${month}-${day}`;
      datesSet.add(date);
      // If date is not in availableTimes, add it
      if (!availableTimes[date]) {
        availableTimes[date] = [];
      }
      // Add time to the date
      availableTimes[date].push(hours);
    });
    // Convert set to array and sort in descending order
    var sortedDates = Array.from(datesSet).sort((a, b) => b.localeCompare(a));

    // Append sorted dates to the timestampSelector
    sortedDates.forEach((date) => {
      var dateOption = document.createElement("option");
      dateOption.value = date;
      dateOption.textContent = date;
      timestampSelector.appendChild(dateOption);
    });
    // Optionally, initialize the timestamp and time selectors
    updateCurrentTimestamp();
  });

function updateTimeSelector(date) {
  // Clear existing time options
  timeSelector.innerHTML = "";

  // Get times for the selected date
  var times = availableTimes[date] || [];
  times.forEach((hour) => {
    var option = document.createElement("option");
    option.value = hour;
    option.textContent = hour;
    timeSelector.appendChild(option);
  });
}

function updateCurrentTimestamp() {
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
  } else {
    // Set the initial value of timestampSelector to the first date in the list
    var firstDate = timestampSelector.options[0].value;
    timestampSelector.value = firstDate;
    updateTimeSelector(firstDate); // Populate time selector
  }
}

function setZoom() {
  var viewportWidth = window.innerWidth;
  var mapZoom;

  if (viewportWidth < 768) {
    mapZoom = 4; // Mobile
  } else if (viewportWidth >= 768 && viewportWidth < 1024) {
    mapZoom = 5; // Tablet
  } else {
    mapZoom = 6; // Desktop
  }

  return mapZoom;
}

var mapOptions = {
  center: [30.3753, 69.3451],
  zoom: setZoom(),
  minZoom: 4,
  maxZoom: 12,
};
var map = L.map("map", mapOptions);

// Add a tile layer (optional, for reference)
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
}).addTo(map);

const colors = [
  "rgb(149, 137, 211)", // Cool temperature color
  "rgb(150, 209, 216)", // Slightly warm temperature color
  "rgb(129, 204, 197)", // Warm temperature color
  "rgb(103, 180, 186)", // Warmer
  "rgb(95, 143, 197)", // Hot temperature color
  "rgb(80, 140, 62)", // Hotter
  "rgb(121, 146, 28)", // Very hot temperature color
  "rgb(171, 161, 14)", // Extremely hot
  "rgb(223, 177, 6)", // Scorching
  "rgb(236, 95, 21)", // Burning hot
];

var markers = new L.MarkerClusterGroup();
var geoJsonLayer;
var pressureLabels = L.layerGroup(); // Layer group for pressure labels

// Define the function to fetch data and add markers
async function addTemperatureMarkers(timestamp) {
  try {
    // Get the timestamp (you can modify this based on your requirements)
    // timestamp = "2024083012"; // Example timestamp

    // Fetch the data from the API
    const response = await fetch(`/api/temperature?timestamp=${timestamp}`);
    const data = await response.json();
    const airTemps = data.map((item) => item.temp);

    // Calculate min and max temperature
    const minTemp = Math.min(...airTemps);
    const maxTemp = Math.max(...airTemps);

    // Define dynamic temperature range
    const temperatureRange = Array.from(
      { length: colors.length },
      (_, i) => minTemp + (i * (maxTemp - minTemp)) / (colors.length - 1)
    );

    // Function to get the color based on temperature
    function getColor(temp) {
      for (let i = 0; i < temperatureRange.length; i++) {
        if (temp <= temperatureRange[i]) {
          return colors[i];
        }
      }
      return colors[colors.length - 1]; // Fallback to the last color
    }
    // Iterate through the data and add markers to the map
    data.forEach((item) => {
      const lat = item.lat;
      const lon = item.lon;
      const temp = item.temp;
      const station = item.station;
      const color = getColor(temp);
      const code = item.code;
      // Create a custom icon (you can customize this)
      const iconHtml = `<div  class="icon-container" style="background-color: ${color}; ">
            <div style="font-size: 12px; text-align: center ">${temp}&deg;</div>
        </div>`;

      const icon = L.divIcon({
        html: iconHtml,
        className: "custom-div-icon",
      });

      // Add the marker to the map
      var marker = L.marker([lat, lon], { icon: icon })
        .bindTooltip(station)
        .addTo(markers);
      marker.bindPopup(`<div id="popup-content-${code}">Loading...</div>`);

      marker.on("click", () => {
        onMarkerClick(code, timestamp);
      });
    });
    map.addLayer(markers);
  } catch (error) {
    console.error("Error fetching or adding markers:", error);
  }
}
addTemperatureMarkers(currenTime);

timestampSelector.addEventListener("change", (event) => {
  updateTimeSelector(event.target.value);
});

function fetchAndPlotGeoJSON(timestamp) {
  fetch(`/api/geojson?timestamp=${timestamp}`)
    .then((response) => response.json())
    .then((data) => {
      if (geoJsonLayer) {
        map.removeLayer(geoJsonLayer);
      }
      // Create a GeoJSON layer
      geoJsonLayer = L.geoJSON(data, {
        style: function (feature) {
          return {
            color: "black",
            weight: 1,
            opacity: 1,
          };
        },
        onEachFeature: function (feature, layer) {
          // Add labels to the map
          if (feature.properties && feature.properties.label_coords) {
            const labelMarker = L.marker(
              [
                feature.properties.label_coords[1],
                feature.properties.label_coords[0],
              ],
              {
                icon: L.divIcon({
                  className: "pressure-labels",
                  html: `<div">${feature.properties.label}</div>`,
                  iconSize: [28, 15],
                }),
              }
            );
            labelMarker.addTo(pressureLabels);
          }
        },
      }).addTo(map);
      pressureLabels.addTo(map);
    })
    .catch((error) => {
      console.error("Error fetching GeoJSON data:", error);
    });
}

// const timestamp = "2024083012";
fetchAndPlotGeoJSON(currenTime);

function onMarkerClick(code, time_stamp) {
  console.log({ time_stamp });
  fetch("/generate_svg?code=" + code + "&timestamp=" + time_stamp)
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
          Pressure: ${additionalData.pressure ?? "N/A"} hpa<br>
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
button.addEventListener("click", function () {
  var selected_data = timestampSelector.value;
  var selected_time = timeSelector.value;

  var formattedDate = selected_data + selected_time;
  formattedDate = formattedDate.replace(/-/g, "");
  markers.clearLayers();
  if (geoJsonLayer) {
    map.removeLayer(geoJsonLayer);
  }
  pressureLabels.clearLayers(); // Clear pressure labels

  fetchAndPlotGeoJSON(formattedDate);
  addTemperatureMarkers(formattedDate);
});
