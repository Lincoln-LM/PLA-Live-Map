var map = L.map("map", {
    minZoom: 0,
    maxZoom: 2,
    crs: L.CRS.Simple,
}).setView([ 0, 0 ], 1); //setView([lat, long], default zoom level)
var southWest = map.unproject([0, 2048], map.getMaxZoom());
var northEast = map.unproject([2048, 0], map.getMaxZoom());
map.setMaxBounds(new L.LatLngBounds(southWest, northEast));