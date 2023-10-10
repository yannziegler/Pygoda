"use strict";

new QWebChannel(qt.webChannelTransport, function (channel) {
    var qtobject = channel.objects.jslink;
    if(typeof qtobject != 'undefined') {
        const DEFAULT = 0;
        const HOVERED = 1;
        const SELECTED = 2;
        const HSELECTED = 3;
        var marker_template = '';

        // used for debugging
        var qtPrint = function(msg) {
            qtobject.jsPrint(msg);
        };

        // Get marker style from CSS
        // var declaration = document.styleSheets[0].cssRules[0].style;
        // var icon_width = declaration.getPropertyValue('width');
        // var icon_height = declaration.getPropertyValue('height');
        var dummy;
        dummy = document.createElement('div');
        document.body.appendChild(dummy);
        dummy.classList.add('station-divicon-plotted');
        dummy = document.querySelector('.station-divicon-plotted');
        var icon_width_plotted = parseInt(getComputedStyle(dummy).width);
        var icon_height_plotted = parseInt(getComputedStyle(dummy).height);
        dummy.classList.remove('station-divicon');
        dummy.classList.add('station-divicon-noplot');
        dummy = document.querySelector('.station-divicon-noplot');
        var icon_width_noplot = parseInt(getComputedStyle(dummy).width);
        var icon_height_noplot = parseInt(getComputedStyle(dummy).height);
        dummy.remove();
        // alert(parseInt(icon_width_plotted));

        // Icon maker
        // const station_icon = makeIcon(staname, marker_desc);
        var getMarkerTemplate = function(marker_svg) {
            marker_template = marker_svg;
        };
        qtobject.sendMarkerTemplate.connect(getMarkerTemplate);
        var makeIcon = function(staname, plotted) {
            // marker_svg = JSON.parse(marker_svg);
            // From: https://stackoverflow.com/a/45488783
            // var svg_icon = "<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><path d='M2,111 h300 l-242.7,176.3 92.7,-285.3 92.7,285.3 z' fill='#0000aa'/></svg>";
            // var svg_icons = ['', '', '', ''];
            // svg_icons[DEFAULT] = marker_desc.svg.replace("{color}", marker_desc.color).replace("{alpha}", marker_desc.alpha).replace("{stroke_color}", marker_desc.stroke_color).replace("{stroke_width}", marker_desc.stroke_width);
            // svg_icons[HOVERED] = svg_icons[DEFAULT];
            // svg_icons[SELECTED] = marker_desc.svg.replace("{color}", "#f0e442").replace("{alpha}", marker_desc.alpha).replace("{stroke_color}", marker_desc.stroke_color).replace("{stroke_width}", marker_desc.stroke_width);
            // svg_icons[HSELECTED] = svg_icons[SELECTED];
            // var icons_size = [marker_desc.size, 1.2*marker_desc.size, marker_desc.size, 1.2*marker_desc.size];
            // var icons_uri = '';
            // var icons = [null, null, null, null];
            // icons_uri = encodeURI("data:image/svg+xml," + svg_icons[i]).replace(/#/g, '%23');
            // icon_uri = 'data:image/svg+xml;base64,' + btoa(svg_icon);
            // icons[i] = L.icon({
            //     iconUrl: icons_uri,
            //     iconSize: icons_size[i]});
            var station_marker = marker_template.replace(/{staname}/g, staname);
            var className, icon_width, icon_height;
            if (plotted) {
                className = 'station-divicon-plotted';
                icon_width = icon_width_plotted;
                icon_height = icon_height_plotted;
            } else {
                className = 'station-divicon-noplot';
                icon_width = icon_width_noplot;
                icon_height = icon_height_noplot;
            };
            var station_icon = L.divIcon({
                className: className,
                html: station_marker,
                iconSize: [icon_height, icon_width],
                iconAnchor: [.5*icon_height, .5*icon_width]
            });
            return station_icon;
        };

        // var lon = qtobject.lon;
        // var lat = qtobject.lat;
        // alert(lon + ', ' + lat);
        // qtobject.lon = 7.0;
        // qtobject.lat = 48.0;
        // alert(qtobject.lon + ', ' + qtobject.lat);
        // const getMethods = (obj) => {
        //     // From: https://flaviocopes.com/how-to-list-object-methods-javascript/
        //     let properties = new Set();
        //     let currentObj = obj;
        //     do {
        //         Object.getOwnPropertyNames(currentObj).map(item => properties.add(item));
        //     } while ((currentObj = Object.getPrototypeOf(currentObj)));
        //     return [...properties.keys()].filter(item => typeof obj[item] === 'function');
        // };
        // alert(getMethods(qtobject));
        // alert(getMethods(qtobject.addMarker));
        // var getList = function(python_list) {
        //     alert(python_list);
        // };
        // qtobject.sendList.connect(getList);

        // Map events
        var onMapMove = function() {
            qtobject.onMapMove(map.getCenter().lng, map.getCenter().lat);
        };
        var onMapLeftClick = function(e) {
            qtobject.onMapLeftClick(e.latlng['lng'], e.latlng['lat']);
        };
        var onMapRightClick = function(e) {
            qtobject.onMapRightClick();
        };
        //var onMapLoad = function(e) {
        //    qtobject.onMapLoad();
        //};
        map.on('move', onMapMove);
        map.on('click', onMapLeftClick);
        map.on('contextmenu', onMapRightClick);
        //map.on('load', onMapLoad);

        // Markers events
        var onMarkerMouseover = function(event) {
            var marker = event.propagatedFrom;
            var staname = marker.staname;
            // marker.addState(HOVERED);
            qtobject.onMarkerMouseover(staname);
        };
        var onMarkerMouseout = function(event) {
            var marker = event.propagatedFrom;
            var staname = marker.staname;
            // marker.removeState(HOVERED);
            qtobject.onMarkerMouseout(staname);
        };
        var onMarkerClick = function(event) {
            var marker = event.propagatedFrom;
            var staname = marker.staname;
            if (marker.current_state < SELECTED) {
                // marker.addState(SELECTED);
                qtobject.onMarkerClick(staname, SELECTED);
            } else {
                // marker.removeState(SELECTED);
                qtobject.onMarkerClick(staname, ~SELECTED);
            };
        };
        var getStationData = function(staname, data) {
            data = JSON.parse(data);
            createPlot(staname, data);
        };
        qtobject.sendStationData.connect(getStationData);
        var onMarkerRightClick = function(event) {
            // alert(event.propagatedFrom.staname);
            var marker = event.propagatedFrom;
            var staname = marker.staname;
            // marker.custom_popup.addTo(map);
            qtobject.onMarkerRightClick(staname);
            // marker.custom_popup.openOn(map);
            // marker.openPopup(marker.custom_popup);
            map.openPopup(marker.custom_popup);
        };

        // Marker group creation
        var markersGroup = L.featureGroup().addTo(map);
        markersGroup.on("click", onMarkerClick);
        markersGroup.on("contextmenu", onMarkerRightClick);
        markersGroup.on("mouseover", onMarkerMouseover);
        markersGroup.on("mouseout", onMarkerMouseout);

        // Stations creation and destruction
        var addSingleStation = function(staname, lat, lng, tooltip, plotted) {
            var coord = [lat, lng];
            var popupContent = "<div style='padding: 0; margin: 0; width: 400px; height: 250px;' id='plot_" + staname + "'></div>";

            // var marker = L.marker(map.getCenter()).addTo(map);
            var station_icon = makeIcon(staname, plotted);
            var marker = L.marker(coord, {icon: station_icon}).addTo(markersGroup);
            // marker.bindPopup(popupContent, {maxWidth: "auto", opacity: 0.9});
            marker.custom_popup = L.popup({maxWidth: "auto", opacity: 0.9}).setContent(popupContent).setLatLng(coord);
            marker.bindTooltip(tooltip);
            marker.staname = staname;
            marker.current_state = DEFAULT;
            marker.addState = function(state) {
                this.current_state += state;
                var state_name;
                if (state == HOVERED) {
                    marker.fire('mouseover');
                    state_name = 'hovered';
                } else if (state == SELECTED) {
                    marker.fire('mouseclick');
                    state_name = 'selected';
                }
                document.getElementById("svg-icon-" + this.staname).classList.add('svg-icon-' + state_name);
                document.getElementById("svg-component-" + this.staname).classList.add('svg-component-' + state_name);
                // this.setIcon(this.icons[this.current_state]);
            };
            marker.removeState = function(state) {
                this.current_state -= state;
                var state_name;
                if (state == HOVERED) {
                    marker.fire('mouseout');
                    state_name = 'hovered';
                } else if (state == SELECTED) {
                    marker.fire('mouseclick');
                    state_name = 'selected';
                }
                document.getElementById("svg-icon-" + this.staname).classList.remove('svg-icon-' + state_name);
                document.getElementById("svg-component-" + this.staname).classList.remove('svg-component-' + state_name);
                // this.setIcon(this.icons[this.current_state]);
            };

            // marker.openPopup();
        };
        qtobject.addSingleStation.connect(addSingleStation);
        var addStations = function(stadict) {
            stadict = JSON.parse(stadict);
            var stanames = stadict.staname;
            var stalat = stadict.lat;
            var stalng = stadict.lon;
            var statooltip = stadict.tooltip;
            var staplotted = stadict.plotted;
            for (var i = 0; i < stanames.length; i++) {
                addSingleStation(stanames[i], stalat[i], stalng[i], statooltip[i], staplotted[i]);
            };
            // map.fitBounds(markersGroup.getBounds());
        };
        qtobject.addStations.connect(addStations);
        var clearStations = function() {
            markersGroup.clearLayers();
        };
        qtobject.clearStations.connect(clearStations);

        // Update markers
        var setMarkersColors = function(stacolors) {
            stacolors = JSON.parse(stacolors);
            for (var i = 0; i < stacolors.staname.length; i++) {
                document.getElementById('svg-component-' + stacolors.staname[i]).style.fill = stacolors.color[i];
            };
        };
        qtobject.setMarkersColors.connect(setMarkersColors);
        var setStationsState = function(sta_modified, state) {
            sta_modified = JSON.parse(sta_modified);
            for (var i = 0; i < sta_modified.length; i++) {
                markersGroup.eachLayer(function(marker) {
                    if (sta_modified.includes(marker.staname)) {
                        if (state > 0) {
                            marker.addState(state);
                        } else {
                            marker.removeState(~state);
                        };
                    };
                });
            };
        };
        qtobject.setStationsState.connect(setStationsState);

        // Map
        var fitMapBound = function() {
            map.fitBounds(markersGroup.getBounds());
        };
        qtobject.fitMapBound.connect(fitMapBound);

        qtobject.onMapLoad(); // tells Pygoda that everything is set and ready
    };
});
