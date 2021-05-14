{% macro script(this, kwargs) %}
var idToValuesInDays = {{this.idToValuesInDays}};
var dateList = {{this.dateList}};

{% if this.dateTimeList is not none  %}
var idToValuesInDaysTimes = {{this.idToValuesInDaysTimes}};
var dateTimeList = {{this.dateTimeList}};
{% else %}
    // NONE
var idToValuesInDaysTimes = null;
var dateTimeList = null;
{% endif %}

var datatype = "{{this.datatype}}";
var currentDateIndex = 0;
// var dataUrl = "{{this.dataUrl}}"

var currentBand = "";
if (datatype == "MODIS" || datatype == "MODIS-ET/PET/LE/PLE")
    currentBand = "ET";
else if (datatype == "MODIS-LAI" || datatype == "MODIS-LAI/FPAR")
    currentBand = "LAI";
else if (datatype == "SMAP")
    currentBand = "surface";
  else if (datatype == "GPM")
      currentBand = "PRECIP";

else
    currentBand = "";
var currentSubbasin = "";
var subbasinList = {{this.subbasinList}};
var minMax = {{this.minMax}};
var zip = new JSZip();

var highlighted_area = null;
var MAP_STYLE_NORMAL = {fillOpacity: 0.55, weight: 1};
var MAP_STYLE_SELECTED = {fillOpacity: 0.9, weight: 5};
//console.log(idToValuesInDays)
//console.log(dateList)
//console.log(currentDateIndex)

var colors = ['#FFEDA0','#FED976','#FEB24C','#FD8D3C','#FC4E2A','#E31A1C','#BD0026','#800026'];

$('div.folium-map').append('<div id="circularG" class="loadingCircle">\
                        <div id="circularG_1" class="circularG"></div>\
                        <div id="circularG_2" class="circularG"></div>\
                        <div id="circularG_3" class="circularG"></div>\
                        <div id="circularG_4" class="circularG"></div>\
                        <div id="circularG_5" class="circularG"></div>\
                        <div id="circularG_6" class="circularG"></div>\
                        <div id="circularG_7" class="circularG"></div>\
                        <div id="circularG_8" class="circularG"></div>\
                    </div>');

$('div.folium-map').append('<div id="circularGbg" class="loadingCircle"></div>');

$('.loadingCircle').hide();

// console.log(dataUrl);

// $.ajax({
// 	url: dataUrl,
// 	dataType: 'jsonp',
// 	jsonpCallback: "visJsonpCallback",
// 	success: function (data){
// 	   draw_map(data);
// 	}
//  });

// get data via postmessage
function onMessage(event) {
    draw_map(event.data);
}
window.addEventListener('message', onMessage, false);



function getColor(v, min, max) {
    normValue = (v - min) / (max - min)
    return normValue > 7/8.0 ? '#800026' :
           normValue > 6/8.0 ? '#BD0026' :
           normValue > 5/8.0 ? '#E31A1C' :
           normValue > 4/8.0 ? '#FC4E2A' :
           normValue > 3/8.0 ? '#FD8D3C' :
           normValue > 2/8.0 ? '#FEB24C' :
           normValue > 1/8.0 ? '#FED976' :
                               '#FFEDA0';
}


window.{{this.get_name()}} = L.geoJson().addTo({{this._parent.get_name()}});
                              




function draw_map(data){

  {% if this.highlight %}
      {{this.get_name()}}_vis_onEachFeature = function onEachFeature(feature, layer) {
          layer.on({
              mouseout: function(e) {
                  if(highlighted_area == null || e.target != highlighted_area)
                      e.target.setStyle(MAP_STYLE_NORMAL);
                  //info.update();
                },
              mouseover: function(e) {
                  if(highlighted_area == null || e.target != highlighted_area)
                      e.target.setStyle({fillOpacity: 0.6, weight: 3});
                  info.update(e.target.feature.properties);},
              click: function(e) {
                  //{{this._parent.get_name()}}.fitBounds(e.target.getBounds());
                  //remove highlight from the previously selected area
                  if(highlighted_area != null){
                      highlighted_area.setStyle(MAP_STYLE_NORMAL);
                      highlighted_area = null;
                  }
                  e.target.setStyle(MAP_STYLE_SELECTED);
                  highlighted_area = e.target;
                  var id = e.target.feature.properties.subbasin;
                  currentSubbasin = id;
                  drawMyChart(id);
                  }
              });
      };
  {% endif %}

/*
  var {{this.get_name()}} = L.geoJson(data

      {% if this.smooth_factor is not none or this.highlight %}
          , {
          {% if this.smooth_factor is not none  %}
              smoothFactor:{{this.smooth_factor}}
          {% endif %}
          {% if this.highlight %}
              {% if this.smooth_factor is not none  %}
              ,
              {% endif %}
              onEachFeature: {{this.get_name()}}_onEachFeature
          {% endif %}
          }
      {% endif %}
      ).addTo({{this._parent.get_name()}});
 */                           
  window.{{this.get_name()}}_vis = L.geoJson(data

      {% if this.smooth_factor is not none or this.highlight %}
          , {
          {% if this.smooth_factor is not none  %}
              smoothFactor:1
          {% endif %}
          {% if this.highlight %}
              {% if this.smooth_factor is not none  %}
              ,
              {% endif %}
              onEachFeature: {{this.get_name()}}_vis_onEachFeature
          {% endif %}
          }
      {% endif %}
      ).addTo({{this._parent.get_name()}});
                              


/*
var {{this.get_name()}} = L.geoJson(
    {% if this.embed %}{{this.style_data()}}{% else %}"{{this.data}}"{% endif %}
    {% if this.smooth_factor is not none or this.highlight %}
        , {
        {% if this.smooth_factor is not none  %}
            smoothFactor:{{this.smooth_factor}}
        {% endif %}
        {% if this.highlight %}
            {% if this.smooth_factor is not none  %}
            ,
            {% endif %}
            onEachFeature: {{this.get_name()}}_onEachFeature
        {% endif %}
        }
    {% endif %}
    ).addTo({{this._parent.get_name()}});
*/

    {{this.get_name()}}_vis.setStyle(function(feature) {
                                        {% if this.datatype == "MODIS" or this.datatype == "MODIS-ET/PET/LE/PLE" %}
                                            val = feature.properties.ET
                                        {% elif this.datatype == "MODIS-LAI" or this.datatype == "MODIS-LAI/FPAR" %}
                                            val = feature.properties.LAI
                                        {% elif this.datatype == "SMAP" %}
                                            val = feature.properties.surface
                                        {% elif this.datatype == "GPM" %}
                                            val = feature.properties.PRECIP
                                        {% endif %}
                                        colorCode = getColor(val, minMax[currentBand][0], minMax[currentBand][1])
                                        return {color: "black", fillColor: colorCode, fillOpacity: 0.55, opacity: 0.5, weight: 1};
                                    });

    // SLIDER DIV ////////////////////////////////////////////////////////////////////////////////////////////

    var slider = L.control({position: 'topright'});
    slider.onAdd = function(map) {
        this._div = L.DomUtil.create('div', 'slider');
        this._div.innerHTML=''
        this._div.id="slider"
        $(this._div).mousedown(function () {
                    map.dragging.disable();
                });
        $(document).mouseup(function () {
                    map.dragging.enable();
                });
        return this._div;

    }
    slider.addTo({{this._parent.get_name()}});

    $( "#slider" ).slider({
          range: "max",
          min: 0,
          max: dateList.length - 1,
          value: 0,
          slide: function( event, ui ) {
            $("#dateInInfoDIv").html("Date: " + dateList[ui.value]);
            currentDateIndex = ui.value;

            //legend.update();
            switchFeaturesColor();
            if(highlighted_area != null)
              info.update(highlighted_area.feature.properties);
            else
              info.update();
          }
    });


    function switchFeaturesColor(){
        {{this.get_name()}}_vis.setStyle(function(feature) {
                                            subbasinID = feature.properties.subbasin;
                                            val = idToValuesInDays[dateList[currentDateIndex]][subbasinID][currentBand]
                                            colorCode = getColor(val, minMax[currentBand][0], minMax[currentBand][1]);

                                            if(highlighted_area != null && highlighted_area.feature.properties.subbasin == subbasinID)
                                              return {color: "black", fillColor: colorCode, fillOpacity: 0.55, opacity: 0.9, weight: 5};
                                            else
                                              return {color: "black", fillColor: colorCode, fillOpacity: 0.55, opacity: 0.5, weight: 1};
                                        });
        //{color: "black", fillColor: "blue", fillOpacity: 0.55, opacity: 0.5, weight: 1}
    }


    // VISUALIZING LEGEND DIV ////////////////////////////////////////////////////////////////////////////////////////////

    function setLegendList(){
        var legendList = [];
        for(i = 0; i < 8; i++)
        {
            legendList.push(parseFloat((minMax[currentBand][0]
                                        + i/8.0*(minMax[currentBand][1]-minMax[currentBand][0]))
                                        .toFixed(2)));
        }
        return legendList;
    }

    var legend = L.control({position: 'bottomleft'});

    legend.onAdd = function (map) {

        this._div = L.DomUtil.create('div', 'info legend');
        this.update();
        return this._div;
    };

    legend.update = function () {
        // loop through our density intervals and generate a label with a colored square for each interval
        this._div.innerHTML = "";
        grades = setLegendList();
        for (var i = 0; i < grades.length; i++) {
            this._div.innerHTML +=
                '<i style="background:' + colors[i] + '"></i> ' +
                grades[i] + (grades[i + 1] ? '&ndash;' + grades[i + 1] + '<br>' : '+');
        }
    };

    legend.addTo({{this._parent.get_name()}});


    // VISUALIZING RADIO BUTTON DIV ////////////////////////////////////////////////////////////////////////////////////////////
    var radioButtons = L.control({position: 'bottomleft'});

    radioButtons.onAdd = function (map) {

        this._div = L.DomUtil.create('div', 'info toggles');
        this.update();
        return this._div;
    };

    radioButtons.update = function () {
        this._div.innerHTML = "";
        {% if this.datatype == "MODIS" or this.datatype == "MODIS-ET/PET/LE/PLE" %}
            this._div.innerHTML = '<input type="radio" name="radioButton" id="radio-1" value="ET" checked><label class="radioLabel" for="radio-1">ET</label><br/>'+
                                    '<input type="radio" name="radioButton" id="radio-2" value="LE" ><label class="radioLabel" for="radio-2">LE</label><br/>'+
                                    '<input type="radio" name="radioButton" id="radio-3" value="PET" ><label class="radioLabel" for="radio-3">PET</label><br/>'+
                                    '<input type="radio" name="radioButton" id="radio-4" value="PLE" ><label class="radioLabel" for="radio-4">PLE</label>';
        {% elif this.datatype == "MODIS-LAI" or this.datatype == "MODIS-LAI/FPAR" %}
            this._div.innerHTML = '<input type="radio" name="radioButton" id="radio-1" value="LAI" checked><label class="radioLabel" for="radio-1">LAI</label><br/>'+
                                    '<input type="radio" name="radioButton" id="radio-2" value="FPAR" ><label class="radioLabel" for="radio-2">FPAR</label>';
        {% elif this.datatype == "SMAP" %}
            this._div.innerHTML = '<input type="radio" name="radioButton" id="radio-1" value="surface" checked><label class="radioLabel" for="radio-1">Surface</label><br/>'+
                                    '<input type="radio" name="radioButton" id="radio-2" value="rootzone" ><label class="radioLabel" for="radio-2">Rootzone</label>';
        {% elif this.datatype == "GPM" %}
            this._div.innerHTML = '<input type="radio" name="radioButton" id="radio-1" value="PRECIP" checked><label class="radioLabel" for="radio-1">PRECIP</label>';
        {% endif %}
    };

    function set_radio_event(){
      var radios = $('input:radio[name="radioButton"]');
      if(radios.length == 0){
        setTimeout(set_radio_event, 1000);
        return;
      }

      $('input:radio[name="radioButton"]').change(function() {
          currentBand = $(this).val();
          legend.update();
          switchFeaturesColor();
          info.update();
      });
    }

    $(document).ready(function() {
        set_radio_event();
    });

    radioButtons.addTo({{this._parent.get_name()}});

    // VISUALIZING CSV DOWNLOAD BUTTON DIV ////////////////////////////////////////////////////////////////////////////////////////////
    var csvDownloadControl =  L.Control.extend({

        options: {
            position: 'bottomleft'
        },

        onAdd: function (map) {
            var container = L.DomUtil.create('div', 'downloadCsv imgButton');

            container.style.backgroundColor = 'transparent';
            // container.style.backgroundImage = "url(http://t1.gstatic.com/images?q=tbn:ANd9GcR6FCUMW5bPn8C4PbKak2BJQQsmC-K9-mbYBeFZm1ZM2w2GRy40Ew)";
            container.style.backgroundImage = "url(http://icons.iconarchive.com/icons/custom-icon-design/flatastic-9/32/Save-icon.png)";
            container.style.backgroundSize = "30px 30px";
            container.style.width = '30px';
            container.style.height = '30px';
            container.style.cursor = 'pointer';
            // container.innerHTML = "D";

            container.onclick = function(){
                $('.loadingCircle').show();
                // console.log('buttonClicked');
                var allZip = zip.folder("CSVs");
                {% if this.datatype == "MODIS" or this.datatype == "MODIS-ET/PET/LE/PLE" %}
                    for(i = 0; i < subbasinList.length; i++)
                    {
                        csv = "year,day,ET,LE,PET,PLE\n";
                        for(j = 0; j < dateList.length; j++)
                        {
                            tmp = dateList[j].split("-");
                            year = parseInt(tmp[0]);
                            day = parseInt(tmp[1]);
                            csv += year + "," + day + ",";

                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["ET"] + ",";
                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["LE"] + ",";
                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["PET"]+ ",";
                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["PLE"]+ "\n";
                        }
                        allZip.file(subbasinList[i]+".csv", csv);
                    }
                {% elif this.datatype == "MODIS-LAI" or this.datatype == "MODIS-LAI/FPAR" %}
                    for(i = 0; i < subbasinList.length; i++)
                    {
                        csv = "year,day,LAI,FPAR\n";
                        for(j = 0; j < dateList.length; j++)
                        {
                            tmp = dateList[j].split("-");
                            year = parseInt(tmp[0]);
                            day = parseInt(tmp[1]);
                            csv += year + "," + day + ",";

                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["LAI"] + ",";
                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["FPAR"]+ "\n";
                        }
                        allZip.file(subbasinList[i]+".csv", csv);
                    }
                {% elif this.datatype == "SMAP" %}
                    for(i = 0; i < subbasinList.length; i++)
                    {
                        csv = "date,surface,rootzone\n";
                        for(j = 0; j < dateList.length; j++)
                        {
                            tmp = dateList[j].split("-");
                            year = tmp[0];
                            date = tmp[1];
                            csv += year + "-" + date + ","

                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["surface"] + ",";
                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["rootzone"]+ "\n";
                        }
                        allZip.file("D"+subbasinList[i]+".csv", csv);

                        if(dateTimeList != null)
                        {
                            csv = "date,time,surface,rootzone\n";
                            for(j = 0; j < dateTimeList.length; j++)
                            {
                                tmp = dateTimeList[j].split("-");
                                year = tmp[0];
                                date = tmp[1];
                                time = tmp[2];
                                csv += year + "-" + date + "," + time + ",";

                                csv += idToValuesInDaysTimes[dateTimeList[j]][subbasinList[i]]["surface"] + ",";
                                csv += idToValuesInDaysTimes[dateTimeList[j]][subbasinList[i]]["rootzone"]+ "\n";
                            }
                            allZip.file("H"+subbasinList[i]+".csv", csv);
                        }

                    }
                {% elif this.datatype == "GPM" %}
                    for(i = 0; i < subbasinList.length; i++)
                    {
                        csv = "date,start_time,end_time,PRECIP\n";
                        for(j = 0; j < dateList.length; j++)
                        {
                            tmp = dateList[j].split("-");
                            date = parseInt(tmp[0]);
                            start_time = parseInt(tmp[1]);
                            end_time = parseInt(tmp[1]);
                            csv += date + "," + start_time + "," + end_time + ",";

                            csv += idToValuesInDays[dateList[j]][subbasinList[i]]["PRECIP"]+ "\n";
                        }
                        allZip.file(subbasinList[i]+".csv", csv);
                    }
                {% endif %}

                allZip.generateAsync({type:"blob"})
                        .then(function (blob) {
                            saveAs(blob, "CSVs.zip");
                            $('.loadingCircle').hide();
                });


            }

        return container;
      }
    });
    var csvDownloadButton = new csvDownloadControl();
    csvDownloadButton.addTo({{this._parent.get_name()}});

    // VISUALIZING INFO DIV ////////////////////////////////////////////////////////////////////////////////////////////
    var info = L.control({position: 'topright'});

    info.onAdd = function (map) {
        this._div = L.DomUtil.create('div', 'info'); // create a div with a class "info"
        this.update();
        return this._div;
    };

    // method that we will use to update the control based on feature properties passed
    info.update = function (props) {
        {% if this.datatype == "MODIS" or this.datatype == "MODIS-ET/PET/LE/PLE" %}
        this._div.innerHTML = '<h4 id="dateInInfoDIv">Date: ' + dateList[currentDateIndex] + '</h4>' +  (props ?
            'Subbasin ID: <b>' + props.subbasin + '</b><br />' +
            (currentBand == "ET" ? "<b>":"") + 'ET: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["ET"]
            + "<br />" + (currentBand == "ET" ? "</b>":"") +
            (currentBand == "LE" ? "<b>":"") + 'LE: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["LE"]
            + "<br />" + (currentBand == "LE" ? "</b>":"") +
            (currentBand == "PET" ? "<b>":"") + 'PET: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["PET"]
            + "<br />" + (currentBand == "PET" ? "</b>":"") +
            (currentBand == "PLE" ? "<b>":"") + 'PLE: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["PLE"]
            + (currentBand == "PLE" ? "</b>":"")
            : 'Subbasin ID: <b>' + 'N/A' + '</b><br />ET: N/A <br />LE: N/A <br />PET: N/A <br />PLE: N/A');
        {% elif this.datatype == "MODIS-LAI" or this.datatype == "MODIS-LAI/FPAR" %}
            this._div.innerHTML = '<h4 id="dateInInfoDIv">Date: ' + dateList[currentDateIndex] + '</h4>' +  (props ?
                'Subbasin ID: <b>' + props.subbasin + '</b><br />' +
                (currentBand == "LAI" ? "<b>":"") + 'LAI: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["LAI"]
                + "<br />" + (currentBand == "LAI" ? "</b>":"") +
                (currentBand == "FPAR" ? "<b>":"") + 'FPAR: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["FPAR"]
                + (currentBand == "FPAR" ? "</b>":"")
                : 'Subbasin ID: <b>' + 'N/A' + '</b><br />LAI: N/A <br />FPAR: N/A');
        {% elif this.datatype == "SMAP" %}
            this._div.innerHTML = '<h4 id="dateInInfoDIv">Date: ' + dateList[currentDateIndex] + '</h4>' +  (props ?
                'Subbasin ID: <b>' + props.subbasin + '</b><br />' +
                (currentBand == "surface" ? "<b>":"") + 'Surface: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["surface"]
                + "<br />" + (currentBand == "surface" ? "</b>":"") +
                (currentBand == "rootzone" ? "<b>":"") + 'Rootzone: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["rootzone"]
                + (currentBand == "rootzone" ? "</b>":"")
                : 'Subbasin ID: <b>' + 'N/A' + '</b><br />Surface: N/A <br />Rootzone: N/A');
        {% elif this.datatype == "GPM" %}
            this._div.innerHTML = '<h4 id="dateInInfoDIv">Date: ' + dateList[currentDateIndex] + '</h4>' +  (props ?
                'Subbasin ID: <b>' + props.subbasin + '</b><br />' +
                (currentBand == "PRECIP" ? "<b>":"") + 'Precipitation: ' + idToValuesInDays[dateList[currentDateIndex]][props.subbasin]["PRECIP"]
                + "<br />" + (currentBand == "PRECIP" ? "</b>":"")
                : 'Subbasin ID: <b>' + 'N/A' + '</b><br />Precipitation: N/A');
        {% endif %}
    };

    info.addTo({{this._parent.get_name()}});

    // VISUALIZING CHART DIV ////////////////////////////////////////////////////////////////////////////////////////////
    var chartDiv = L.control({position : 'bottomright'});
    chartDiv.onAdd = function(map) {
        this._div = L.DomUtil.create('div', 'myChart');
        this._div.innerHTML=''
        this._div.id="myChart"
        return this._div;

    }
    chartDiv.addTo({{this._parent.get_name()}});


    // CHART CLOSE BUTTON ////////////////////////////////////////////////////////////////////////////////////////////
    var chartCloseControl =  L.Control.extend({
      options: {
        position: 'bottomright'
      },
      update: function (map){
        this._div.style.display = 'inline-block';
        this.saveIcon.style.display = 'block';
        this.closeIcon.style.display = 'block';
        // this._div.style.display = 'inline-block';
      },
      onAdd: function (map) {
        // this._div = L.DomUtil.create('div', 'iconBox leaflet-bar leaflet-control leaflet-control-custom');
        this._div = L.DomUtil.create('div', 'iconBox leaflet-control leaflet-control-custom');
        // this._div.style.width = "100 px";
        this._div.style.marginBottom = "0px";
        this._div.style.marginRight = "10px";
        this._div.style.display = 'none';
        this._div.style.zIndex = "1000";

        // this.container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
        this.saveIcon = L.DomUtil.create('div', 'saveIcon imgButton');
        this.saveIcon.style.float = "right";
        this.saveIcon.margin = "0 auto";
        this.saveIcon.style.backgroundColor = 'transparent';
        this.saveIcon.style.backgroundImage = "url(http://icons.iconarchive.com/icons/custom-icon-design/flatastic-9/32/Save-icon.png)";
        this.saveIcon.style.backgroundSize = "25px 25px";
        this.saveIcon.style.width = '25px';
        this.saveIcon.style.height = '25px';
        this.saveIcon.style.fontSize = '22px';
        this.saveIcon.style.fontWeight = 'bold';
        this.saveIcon.style.display = 'none';
        this.saveIcon.style.lineHeight = '0px';
        this.saveIcon.style.padding = '13px 4px';
        this.saveIcon.style.cursor = 'pointer';
        this.saveIcon.style.marginBottom = '-12px';
        this.saveIcon.style.marginRight = '5px';
        this.saveIcon.style.zIndex = '1000';
        // this.saveIcon.innerHTML='O';

        this.saveIcon.onclick = function(){
            {% if this.datatype == "MODIS" or this.datatype == "MODIS-ET/PET/LE/PLE" %}
                lines = "year,day,ET,LE,PET,PLE\n";
                for(i = 0; i < dateList.length; i++)
                {
                    tmp = dateList[i].split("-");
                    year = parseInt(tmp[0]);
                    day = parseInt(tmp[1]);
                    lines += year + "," + day + ",";

                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["ET"] + ",";
                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["LE"] + ",";
                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["PET"]+ ",";
                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["PLE"]+ "\n";
                }
            {% elif this.datatype == "MODIS-LAI" or this.datatype == "MODIS-LAI/FPAR" %}
                lines = "year,day,LAI,FPAR\n";
                for(i = 0; i < dateList.length; i++)
                {
                    tmp = dateList[i].split("-");
                    year = parseInt(tmp[0]);
                    day = parseInt(tmp[1]);
                    lines += year + "," + day + ",";

                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["LAI"] + ",";
                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["FPAR"]+ "\n";
                }
            {% elif this.datatype == "SMAP" %}
                lines = "date,time,surface,rootzone\n";
                for(i = 0; i < dateList.length; i++)
                {
                    tmp = dateList[i].split("-");
                    year = parseInt(tmp[0]);
                    date = parseInt(tmp[1]);
                    time = parseInt(tmp[2]);
                    lines += year + "-" + date + "," + time + ",";

                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["surface"] + ",";
                    lines += idToValuesInDays[dateList[i]][currentSubbasin]["rootzone"]+ "\n";
                }
              {% elif this.datatype == "GPM" %}
                  lines = "date,start_time,end_time,PRECIP\n";
                  for(i = 0; i < dateList.length; i++)
                  {
                      tmp = dateList[i].split("-");
                      date = parseInt(tmp[0]);
                      start_time = parseInt(tmp[1]);
                      end_time = parseInt(tmp[2]);
                      lines += date + "," + start_time + "," + end_time + ",";

                      lines += idToValuesInDays[dateList[i]][currentSubbasin]["PRECIP"]+ "\n";
                  }
            {% endif %}

            var file = new File([lines], currentSubbasin + ".csv", {type: "text/csv;charset=utf-8"});
            saveAs(file);
        };

        // this.closeIcon = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
        this.closeIcon = L.DomUtil.create('div', 'closeIcon imgButton');
        this.closeIcon.style.float = "right";
        this.closeIcon.style.backgroundColor = 'transparent';
        this.closeIcon.style.backgroundImage = "url(http://icons.iconarchive.com/icons/hopstarter/soft-scraps/32/Button-Close-icon.png)";
        this.closeIcon.style.backgroundSize = "25px 25px";
        this.closeIcon.style.width = '25px';
        this.closeIcon.style.height = '25px';
        this.closeIcon.style.fontSize = '22px';
        this.closeIcon.style.fontWeight = 'bold';
        this.closeIcon.style.display = 'none';
        this.closeIcon.style.lineHeight = '0px';
        this.closeIcon.style.padding = '13px 5px';
        this.closeIcon.style.cursor = 'pointer';
        this.closeIcon.style.marginBottom = '-12px';
        this.closeIcon.style.marginRight = '0px';
        this.closeIcon.style.zIndex = '1000';
        // this.closeIcon.innerHTML='X';
        this.closeIcon._parent = this;

        this.closeIcon.onclick = function(){
            if(chartVar != null)
            {
              chartVar.destroy();
              chartVar = null;
              console.log("destroyed");
            }
            this.style.display = 'none';
            this._parent.saveIcon.style.display = 'none';
            this._parent._div.style.display = 'none';
            if(highlighted_area != null){
                highlighted_area.setStyle(MAP_STYLE_NORMAL);
                highlighted_area = null;
            }
        }

        this._div.append(this.closeIcon)
        this._div.append(this.saveIcon);

        return this._div;
      }
    });
    var chartCloseButton = new chartCloseControl();
    chartCloseButton.addTo({{this._parent.get_name()}});

    var chartVar = null;
    function drawMyChart(id)
    {
        {% if this.datatype == "MODIS" or this.datatype == "MODIS-ET/PET/LE/PLE" %}
            ets = []
            les = []
            pets = []
            ples = []
            for(i = 0; i < dateList.length; i++)
            {
                ets.push(idToValuesInDays[dateList[i]][id]["ET"]);
                les.push(idToValuesInDays[dateList[i]][id]["LE"]);
                pets.push(idToValuesInDays[dateList[i]][id]["PET"]);
                ples.push(idToValuesInDays[dateList[i]][id]["PLE"]);
            }
            chartVar = new Highcharts.chart('myChart', {
                title: {text: "Time-series on subbasin: " + id},
                subtitle: {text: 'Bands: ET, LE, PET and PLE'},
                xAxis: {categories: dateList},
                yAxis: {title: {text: 'Weighted Avg.'}},
                        legend: {layout: 'vertical',align: 'right',verticalAlign: 'middle'},
                plotOptions: {series: {pointStart: 0}},
                series: [{name: 'ET',data: ets},{name: 'LE',data: les},{name: 'PET',data: pets},{name: 'PLE',data: ples}]
            });
        {% elif this.datatype == "MODIS-LAI" or this.datatype == "MODIS-LAI/FPAR" %}
            lais = []
            fpars = []
            for(i = 0; i < dateList.length; i++)
            {
                lais.push(idToValuesInDays[dateList[i]][id]["LAI"]);
                fpars.push(idToValuesInDays[dateList[i]][id]["FPAR"]);
            }
            chartVar = new Highcharts.chart('myChart', {
                title: {text: "Time-series on subbasin: " + id},
                subtitle: {text: 'Bands: LAI and FPAR'},
                xAxis: {categories: dateList},
                yAxis: {title: {text: 'Weighted Avg.'}},
                        legend: {layout: 'vertical',align: 'right',verticalAlign: 'middle'},
                plotOptions: {series: {pointStart: 0}},
                series: [{name: 'LAI',data: lais},{name: 'FPAR',data: fpars}]
            });
        {% elif this.datatype == "SMAP" %}
            surfaces = []
            rootzones = []
            for(i = 0; i < dateList.length; i++)
            {
                surfaces.push(idToValuesInDays[dateList[i]][id]["surface"]);
                rootzones.push(idToValuesInDays[dateList[i]][id]["rootzone"]);
            }
            chartVar = new Highcharts.chart('myChart', {
                title: {text: "Time-series on subbasin: " + id},
                subtitle: {text: 'Bands: Surface and Rootzone Moisture'},
                xAxis: {categories: dateList},
                yAxis: {title: {text: 'Weighted Avg.'}},
                        legend: {layout: 'vertical',align: 'right',verticalAlign: 'middle'},
                plotOptions: {series: {pointStart: 0}},
                series: [{name: 'Surface',data: surfaces},{name: 'Rootzone',data: rootzones}]
            });
        {% elif this.datatype == "GPM" %}
            PRECIPs = []
            for(i = 0; i < dateList.length; i++)
            {
                PRECIPs.push(idToValuesInDays[dateList[i]][id]["PRECIP"]);
            }
            chartVar = new Highcharts.chart('myChart', {
                title: {text: "Time-series on subbasin: " + id},
                subtitle: {text: 'Bands: Precipitation'},
                xAxis: {categories: dateList},
                yAxis: {title: {text: 'Weighted Avg.'}},
                        legend: {layout: 'vertical',align: 'right',verticalAlign: 'middle'},
                plotOptions: {series: {pointStart: 0}},
                series: [{name: 'Precipitation',data: PRECIPs}]
            });
        {% endif %}

        chartCloseButton.update();
        console.log("created");
    }

    // remove dummy layer
    window.{{this.get_name()}}.clearLayers();
}

{% endmacro %}
