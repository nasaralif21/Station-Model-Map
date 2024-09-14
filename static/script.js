var timestampSelector = document.getElementById("timestampSelector");
var timeSelector = document.getElementById("timeSelector");
var button = document.getElementById("view-chart");
var currentTimestamp = "";
var availableTimes = {};
var cachedData = {}; // Cache for fetched data

var now = new Date();
var utcYear = now.getUTCFullYear();
var utcMonth = String(now.getUTCMonth() + 1).padStart(2, "0"); // Months are 0-indexed
var utcDay = String(now.getUTCDate()).padStart(2, "0");
var utcHours = String(now.getUTCHours()).padStart(2, "0");

var now = new Date();
var utcNow = new Date(now.toUTCString()); // Convert to UTC
var hour = utcNow.getUTCHours();
console.log(hour);
console.log(hour);

var intervalStartHour = Math.floor(hour / 3) * 3;
utcNow.setUTCHours(intervalStartHour, 0, 0, 0); // Set hour, minute, second, and millisecond to the interval start
console.log(intervalStartHour);

// var timestamp = utcNow.toISOString().replace(/[-:T]/g, "").slice(0, 10); // Format as "YYYYMMDDHH"
var timestamp = "2024091300";
console.log(timestamp);
currentTimestamp = timestamp;

fetch("/list_data_files")
  .then((response) => response.json())
  .then((files) => {
    htmlFiles = files;
    var datesSet = new Set();
    htmlFiles.forEach((file) => {
      var timestamp = file.replace(".geojson", "");
      var year = timestamp.slice(0, 4);
      var month = timestamp.slice(4, 6);
      var day = timestamp.slice(6, 8);
      var hours = timestamp.slice(8, 10);
      var date = `${year}-${month}-${day}`;
      datesSet.add(date);
      if (!availableTimes[date]) {
        availableTimes[date] = [];
      }
      availableTimes[date].push(hours);
    });
    var sortedDates = Array.from(datesSet).sort((a, b) => b.localeCompare(a));
    sortedDates.forEach((date) => {
      var dateOption = document.createElement("option");
      dateOption.value = date;
      dateOption.textContent = date;
      timestampSelector.appendChild(dateOption);
    });
    updateCurrentTimestamp();
  });

function updateTimeSelector(date) {
  timeSelector.innerHTML = "";
  var times = availableTimes[date] || [];
  times.sort((a, b) => a.localeCompare(b));
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
    updateTimeSelector(formattedDate);
    timeSelector.value = currentHours;
  } else {
    var firstDate = timestampSelector.options[0].value;
    timestampSelector.value = firstDate;
    updateTimeSelector(firstDate);
  }
}

function setZoom() {
  var viewportWidth = window.innerWidth;
  var mapZoom;
  if (viewportWidth < 768) {
    mapZoom = 4;
  } else if (viewportWidth >= 768 && viewportWidth < 1024) {
    mapZoom = 5;
  } else {
    mapZoom = 6;
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

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
}).addTo(map);

const colors = [
  "rgb(149, 137, 211)",
  "rgb(150, 209, 216)",
  "rgb(129, 204, 197)",
  "rgb(103, 180, 186)",
  "rgb(95, 143, 197)",
  "rgb(80, 140, 62)",
  "rgb(121, 146, 28)",
  "rgb(171, 161, 14)",
  "rgb(223, 177, 6)",
  "rgb(236, 95, 21)",
];
let temperatureRange = [];
// Helper to convert "rgb(r, g, b)" format to an array [r, g, b]
function rgbStringToArray(rgbString) {
  return rgbString
    .replace(/[^\d,]/g, "") // Remove non-numeric characters
    .split(",")
    .map(Number); // Convert strings to numbers
}

// Helper to interpolate between two colors based on a factor
function interpolateColor(color1, color2, factor) {
  return [
    Math.round(color1[0] + factor * (color2[0] - color1[0])),
    Math.round(color1[1] + factor * (color2[1] - color1[1])),
    Math.round(color1[2] + factor * (color2[2] - color1[2])),
  ];
}

// Helper to convert an RGB array back to a string "rgb(r, g, b)"
function rgbArrayToString(rgbArray) {
  return `rgb(${rgbArray[0]}, ${rgbArray[1]}, ${rgbArray[2]})`;
}

// Get interpolated color based on temperature
function getColor(temp, minTemp, maxTemp) {
  // Normalize temperature into a range [0, 1]
  const normalizedTemp = (temp - minTemp) / (maxTemp - minTemp);

  // Determine which two colors to interpolate between
  const colorStep = 1 / (colors.length - 1);
  const lowerIndex = Math.floor(normalizedTemp / colorStep);
  const upperIndex = Math.min(lowerIndex + 1, colors.length - 1);

  const lowerColor = rgbStringToArray(colors[lowerIndex]);
  const upperColor = rgbStringToArray(colors[upperIndex]);

  // Interpolate between the two colors
  const factor = (normalizedTemp - lowerIndex * colorStep) / colorStep;
  const interpolatedColor = interpolateColor(lowerColor, upperColor, factor);

  return rgbArrayToString(interpolatedColor);
}

var markers = new L.MarkerClusterGroup({
  iconCreateFunction: function (cluster) {
    const markers = cluster.getAllChildMarkers();
    // console.log(markers);

    let totalTemp = 0;
    let count = 0;

    // Loop through each marker to extract temperature

    markers.forEach((marker) => {
      const popup = marker.getPopup();
      if (popup) {
        const content = popup.getContent();
        const tempMatch = content.match(/(\d+(\.\d+)?)&deg;/); // Match temperature
        if (tempMatch) {
          const temp = parseFloat(tempMatch[1]); // Convert to float
          // console.log(temp);

          totalTemp += temp; // Accumulate temperature
          count++; // Count valid temperatures
        }
      }
    });

    const avgTemp = (totalTemp / count).toFixed(2); // Calculate average
    const color = getColor(
      avgTemp,
      Math.min(...temperatureRange),
      Math.max(...temperatureRange)
    );

    return L.divIcon({
      html: `<div class="cluster-icon" style="background-color: ${color};">${avgTemp}&deg;</div>`,
      className: "custom-cluster-icon",
      iconSize: L.point(40, 40),
    });
  },
});
var geoJsonLayer;
var pressureLabels = L.layerGroup();

async function addTemperatureMarkers(timestamp) {
  markers.clearLayers();
  if (geoJsonLayer) {
    map.removeLayer(geoJsonLayer);
  }
  pressureLabels.clearLayers();
  try {
    if (cachedData[timestamp] && cachedData[timestamp].temperature) {
      updateTemperatureMarkers(cachedData[timestamp].temperature, timestamp);
      return;
    }
    const response = await fetch(`/api/temperature?timestamp=${timestamp}`);
    if (!response.ok) {
      throw new Error("Temperature data not available");
    }
    const data = await response.json();
    if (!data || data.length === 0) {
      throw new Error("Temperature data not available");
    }
    cachedData[timestamp] = { ...cachedData[timestamp], temperature: data };
    updateTemperatureMarkers(data, timestamp);
  } catch (error) {
    console.error("Error fetching or adding markers:", error);
    // alert(
    //   "Temperature data not available for the selected timestamp. Displaying data for the first timestamp of the day."
    // );
    // Fallback to the first timestamp of the day
    const fallbackTimestamp = timestamp.slice(0, 8) + "00"; // YYYYMMDD00
    currentTimestamp = timestamp.slice(0, 8) + "00";
    await addTemperatureMarkers(fallbackTimestamp);
  }
}

function updateTemperatureMarkers(data, timestamp) {
  markers.clearLayers();
  const airTemps = data.map((item) => item.temp);
  const minTemp = Math.min(...airTemps);
  const maxTemp = Math.max(...airTemps);
  temperatureRange = Array.from(
    { length: 7 },
    (_, i) => minTemp + (i * (maxTemp - minTemp)) / (7 - 1)
  );

  data.forEach((item) => {
    const lat = item.lat;
    const lon = item.lon;
    const temp = item.temp;
    const station = item.station;
    const color = getColor(temp, minTemp, maxTemp);
    const code = item.code;
    const iconHtml = `<div class="icon-container" style="background-color: ${color};">
          <div style="font-size: 12px; text-align: center">${temp}&deg;</div>
      </div>`;
    const icon = L.divIcon({
      html: iconHtml,
      className: "custom-div-icon",
    });
    var marker = L.marker([lat, lon], { icon: icon })
      .bindTooltip(station)
      .addTo(markers);
    marker.bindPopup(`<div id="popup-content-${code}">${temp}&deg;</div>`);

    marker.on("click", () => {
      onMarkerClick(code, timestamp);
    });
  });
  map.addLayer(markers);
}

timestampSelector.addEventListener("change", (event) => {
  updateTimeSelector(event.target.value);
});

async function fetchAndPlotGeoJSON(timestamp) {
  if (cachedData[timestamp] && cachedData[timestamp].geojson) {
    updateGeoJSONLayer(cachedData[timestamp].geojson);
    return;
  }
  fetch(`/api/geojson?timestamp=${timestamp}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("GeoJSON data not available");
      }
      return response.json();
    })
    .then((data) => {
      if (!data || Object.keys(data).length === 0) {
        throw new Error("GeoJSON data not available");
      }
      cachedData[timestamp] = { ...cachedData[timestamp], geojson: data };
      updateGeoJSONLayer(data);
    })
    .catch(async (error) => {
      const fallbackTimestamp = timestamp.slice(0, 8) + "00"; // YYYYMMDD00
      currentTimestamp = timestamp.slice(0, 8) + "00";
      updateCurrentTimestamp();
      await fetchAndPlotGeoJSON(fallbackTimestamp);
    });
}

function updateGeoJSONLayer(data) {
  if (geoJsonLayer) {
    map.removeLayer(geoJsonLayer);
  }
  pressureLabels.clearLayers();
  geoJsonLayer = L.geoJSON(data, {
    style: function (feature) {
      return {
        color: "black",
        weight: 1,
        opacity: 1,
      };
    },
    onEachFeature: function (feature, layer) {
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
}

function onMarkerClick(code, time_stamp) {
  fetch("/generate_svg?code=" + code + "&timestamp=" + time_stamp)
    .then((response) => response.json())
    .then((data) => {
      var popupContent = document.getElementById("popup-content-" + code);
      if (popupContent) {
        var svgData = data.svg;
        var additionalData = data.additional_data;
        var updatedContent = `
          <b>${additionalData.place_name}</b><br>
          Temp: ${additionalData.air_temp ?? "N/A"}&deg;C<br>
          Station Pressure: ${additionalData.pressure ?? "N/A"} hpa<br>
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
addTemperatureMarkers(timestamp);
fetchAndPlotGeoJSON(timestamp);
button.addEventListener("click", function () {
  markers.clearLayers();
  if (geoJsonLayer) {
    map.removeLayer(geoJsonLayer);
  }
  pressureLabels.clearLayers(); // Clear existing pressure labels
  var selected_data = timestampSelector.value;
  var selected_time = timeSelector.value;
  var formattedDate = selected_data + selected_time;
  formattedDate = formattedDate.replace(/-/g, "");
  currentTimestamp = formattedDate; // Update the current timestamp
  addTemperatureMarkers(formattedDate);
  fetchAndPlotGeoJSON(formattedDate);
});
