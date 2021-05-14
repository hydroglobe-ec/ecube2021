import os
from IPython.display import HTML, display, Javascript
from notebook import notebookapp
from osgeo import ogr, osr
import urllib
import json
from enum import Enum


class HGLOG(Enum):
    LOAD = 0
    JOB_SUBMIT = 1
    VISUALIZATION = 2
    JOB_STATUS = 9

class HGUtil:    
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #/home/mygeohub/yirugi/notebooks/hydroglobe/trunk
    WORKING_DIR = APP_DIR + "/bin/workingdir"
    DATA_DIR = APP_DIR + "/bin/data"
    # APP_URL = 'https://proxy.mygeohub.org'
    # WORK_DIR_LINK = APP_DIR + '/bin/workingdir'
    # NB_BASE_URL = None

    GPM_FILE_EXT = '.nc'

    # /home/mygeohub/yirugi/data/results/20522/hydroglobetool -> for live app

    ALERT_TYPES = {}
    ALERT_TYPES['none'] = ""
    ALERT_TYPES['warning'] = "type: 'orange', icon: 'fa fa-warning',"
    ALERT_TYPES['error'] = "type: 'red', icon: 'fa fa-warning',"
    ALERT_TYPES['success'] = "type: 'green', icon: 'fa fa-check-circle',"
    ALERT_TYPES['info'] = "type: 'blue', icon: 'fa fa-info-circle',"

    JOBLOG_FUNC = None
    HG_INTERFACE = None

    @staticmethod
    def mkdir(dir):
        if not os.path.exists(dir):
            os.mkdir(dir)

    @staticmethod
    def rmdir(dir):
        os.system('rm -rf "' + dir + '"')


    @staticmethod
    def startDownloadToClient(url):
        html = '<iframe src="%s" style="display:none"></iframe>' % url
        display(HTML(html))
        #js_download = "window.location = '%s';" % url
        #display(Javascript(js_download))

    @staticmethod
    def downloadToClient(data, filename):
        js_download = """
        var csv = '%s';

        var filename = '%s';
        var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, filename);
        } else {
            var link = document.createElement("a");
            if (link.download !== undefined) { // feature detection
                // Browsers that support HTML5 download attribute
                var url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", filename);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        }
        """ % (data.replace('\n','\\n').replace("'","\'"), filename)

        display(Javascript(js_download))


    # @staticmethod
    # def createWorkLink():
    #     os.system('rm -rf ' + HGUtil.WORK_DIR_LINK)
    #     os.system('ln -s ' + HGUtil.WORKING_DIR + ' ' + HGUtil.WORK_DIR_LINK)
   

    @staticmethod
    def getShapeBound(shape_path):
        outRef ='GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]'

        driver = ogr.GetDriverByName("ESRI Shapefile")
        dataSource = driver.Open(shape_path, 0)

        layer = dataSource.GetLayer()
        minX, maxX, minY, maxY = layer.GetExtent()

        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(minX, minY), ring.AddPoint(maxX, minY), ring.AddPoint(maxX, maxY), ring.AddPoint(minX, maxY), ring.AddPoint(minX, minY)


        mbb = ogr.Geometry(ogr.wkbPolygon)
        mbb.AddGeometry(ring)

        inSpatialRef = layer.GetSpatialRef()
        outSpatialRef = osr.SpatialReference()
        # inSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        # outSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        outSpatialRef.ImportFromWkt(outRef)
        coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
        mbb.Transform(coordTransform)
        mbb.FlattenTo2D()

        extent = mbb.GetEnvelope()
        return extent[2], extent[0], extent[3], extent[1]



    @staticmethod
    def sendLog(activity, data='', additional = ''):
        return
        
