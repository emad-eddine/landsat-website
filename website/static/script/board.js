// // // // map
// // GeoTIFF
 var tiff = "http://localhost:8080/lstProjet.tif";

var map = L.map('map');

        /* Basemap */
        var url = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
        L.tileLayer(url, {
            attribution: 'CartoDB & OSM',
            subdomains: 'abc',
            maxZoom: 19
        }).addTo(map);

        /*
            Some ScalarField layers with custom styles
        */
            fetch(tiff).then(r => r.arrayBuffer()).then(function(buffer)  {
                var s = L.ScalarField.fromGeoTIFF(buffer);

            var layer2 = L.canvasLayer.scalarField(s, {
                color: chroma.scale(['black','red','yellow','white']).correctLightness().domain(s.range).classes(25),
                mouseMoveCursor: null,
                opacity: 0.87
            }).addTo(map);;
            layer2.on("click", function(e) {
                if (e.value !== null) {
                  let popup = L.popup()
                  .setLatLng(e.latlng)
                  .setContent(`${e.value}`)
                  .openOn(map);
                }
              });
              map.fitBounds(layer2.getBounds());
            })