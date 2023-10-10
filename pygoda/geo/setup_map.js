var map = L.map('map').setView([0.0, 0.0], 2);
//var map = L.map('map').setView([51.505, -0.09], 13);

// access_token = 'pk.eyJ1Ijoic25vcmZhbG9ycGFndXMiLCJhIjoic1oxRTMxcyJ9.eC6cjtLmFs9EcVwmT1isOQ';
// L.tileLayer('https://{s}.tiles.mapbox.com/v4/examples.map-i86nkdio/{z}/{x}/{y}@2x.png?access_token='+access_token, {
//     maxZoom: 18,
//     attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
//         '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
//         'Imagery &copy; <a href="http://mapbox.com">Mapbox</a>',
//     id: 'examples.map-i86nkdio',
// }).addTo(map);

// let myFilter = [
//     'blur:0px',
//     'brightness:95%',
//     'contrast:130%',
//     'grayscale:80%',
//     'hue:290deg',
//     'opacity:100%',
//     'invert:100%',
//     'saturate:300%',
//     'sepia:10%',
// ];

// L.tileLayer.colorFilter('https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png', {
//     attribution: '<a href="https://wikimediafoundation.org/wiki/Maps_Terms_of_Use">Wikimedia</a>',
//     filter: myFilter,
// }).addTo(map);

var OpenStreetMap_Mapnik = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  	attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  });
var Wikimedia = L.tileLayer('https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png', {
  attribution: '<a href="https://wikimediafoundation.org/wiki/Maps_Terms_of_Use">Wikimedia maps</a> | Map data &copy; <a href="http://openstreetmap.org/copyright">OpenStreetMap contributors</a>'});
var Esri_NatGeoWorldMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}', {
  	attribution: 'Powered by Esri | <a href="https://www.arcgis.com/home/item.html?id=3d1a30626bbc46c582f148b9252676ce">attributions</a>',
    // Source: National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC // too long to display
  	maxZoom: 16
  });
var Esri_WorldPhysical = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}', {
  	attribution: 'Tiles &copy; Esri &mdash; Source: US National Park Service',
  	maxZoom: 8
  });
//var Thunderforest_Landscape = L.tileLayer('https://{s}.tile.thunderforest.com/landscape/{z}/{x}/{y}.png?apikey={apikey}', {
//  	attribution: '&copy; <a href="http://www.thunderforest.com/">Thunderforest</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
//  	apikey: '<your apikey>',
//  	maxZoom: 22
//  });
var CartoDB_PositronNoLabels = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
  	attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  	subdomains: 'abcd',
  	maxZoom: 20
  });
var CartoDB_DarkMatterNoLabels = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
  	attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  	subdomains: 'abcd',
  	maxZoom: 20
  });
var Esri_WorldImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
	attribution: 'Powered by Esri | <a href="https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9">attributions</a>'
  //Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community // too long to display
  // Reference: https://support.esri.com/en/technical-article/000012040
});
//var MapQuest_Imagery = L.tileLayer("http://{s}.mqcdn.com/tiles/1.0.0/sat/{z}/{x}/{y}.png", {
//  attribution: 'Tiles Courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="http://developer.mapquest.com/content/osm/mq_logo.png">',
//  subdomains: ['otile1','otile2','otile3','otile4']});

var baseMaps = {
    "OpenStreetMap": OpenStreetMap_Mapnik,
    "Wikimedia": Wikimedia,
    "Esri Nat. Geo. Worldmap": Esri_NatGeoWorldMap,
    "Esri World Physical": Esri_WorldPhysical,
    //"Thunderforest Landscape": Thunderforest_Landscape,
    "CartoDB Positron": CartoDB_PositronNoLabels,
    "CartoDB Dark": CartoDB_DarkMatterNoLabels,
    "Esri World Imagery": Esri_WorldImagery,
    //"MapQuest Imagery": MapQuest_Imagery
};

var overlays =  {};

L.control.layers(baseMaps, overlays, {position: 'bottomleft'}).addTo(map);
baseMaps["Esri World Imagery"].addTo(map);

// When all visible tiles have been loaded
//baseMaps["Esri World Imagery"].on("load", function() {  });

// L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
//     attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
// }).addTo(map);
