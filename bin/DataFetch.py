#!/usr/bin/env python

import os, sys
import shutil
import fnmatch
import subprocess as sp
import time
from osgeo import ogr, osr
from datetime import datetime as dt
from datetime import timedelta
from shapely.geometry import box
import requests, re
from HGUtil import HGUtil

_print = print
def print(*args, **kw):
    HGUtil.JOBLOG_FUNC(*args, **kw)
    # _print(*args, **kw)

class Fetch:
    def __init__(self):
        self.WORKING_DIR = ''

    def getAllDayDataWithGeocodeMODIS(self, rootDir, targetDir, ext, geocodes = ["h00v08"], year = "2013", dayNumber = "001" ):

        # wgetCommand = "wget -w 0.2 -l 0 -r -nH -np -I"
        dataPath  = "/data/NTSG_Products/MOD16/MOD16A2.105_MERRAGMAO/Y" + str(year) + "/D" + str(dayNumber) + "/*,"
        dataPath2 = "/data/NTSG_Products/MOD16/MOD16A2.105_MERRAGMAO/Y" + str(year) + "/D" + str(dayNumber)
        serverAddress = "files.ntsg.umt.edu/data/NTSG_Products/MOD16/MOD16A2.105_MERRAGMAO/Y" + str(year) + "/D" + str(dayNumber)

        # start = time.time()
        gcString = ""
        for gc in geocodes:
            gcString += "*" + gc + "*,"
        gcString = gcString[:-1]

        cmd = ["wget", "-w", "0.05", "-l", "0", "-r", "-nH", "-np", "-I", dataPath+dataPath2, "-R", "*.htm,*.html", '-e', 'robots=off', "-A", gcString, serverAddress]

        p = sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)

        status = 0
        for line in iter(p.stdout.readline, b''):
            line = line.decode()
            # print "> " + line.rstrip()
            if status == 0:
                print("> " + line.rstrip())
                if line.rstrip().startswith("Saving to:"):
                    status = 1

            elif status == 1:
                if line.rstrip().startswith("FINISHED"):
                    status = 2
                    print( "> " + line.rstrip())

                elif line.rstrip().startswith("Saving to:"):
                    items = line.rstrip().split("/")
                    print( "> " + items[0] + "/.../" + items[-3] + "/" + items[-2] + "/" + items[-1])

            else:
                print( "> " + line.rstrip())

    def getAllDayDataWithGeocodeLAI(self, rootDir, targetDir, ext, geocodes = ["h00v08"], year = "2013", dayNumber = "001", dayString = "2013.01.01"):

        # wgetCommand = "wget -w 0.2 -l 0 -r -nH -np -I"
        dataPath  = "/MOTA/MCD15A3H.006/" + str(dayString) + "/*,"
        dataPath2 = "/MOTA/MCD15A3H.006/" + str(dayString)
        #  e4ftl01.cr.usgs.gov/MOTA/MCD15A3H.006/
        serverAddress = "e4ftl01.cr.usgs.gov/MOTA/MCD15A3H.006/" + str(dayString)

        # start = time.time()
        gcString = ""
        for gc in geocodes:
            gcString += "*" + gc + "*,"
        gcString = gcString[:-1]

       
        cmd = ["wget",  "--http-user=waterhub", "--http-password==4SrN*nn", "--no-check-certificate", "--auth-no-challenge",
                "-w", "0.05", "-l", "0", "-r", "-nH", "-np", "-I", dataPath+dataPath2, "-R", "*.htm,*.html*,*.jpg,*.xml",
                "-e", "robots=off", "-A", gcString, serverAddress]

        p = sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)

        status = 0
        for line in iter(p.stdout.readline, b''):
            line = line.decode()
            # print "> " + line.rstrip()
            if status == 0:
                print( "> " + line.rstrip())
                if line.rstrip().startswith("Saving to:"):
                    status = 1

            elif status == 1:
                if line.rstrip().startswith("FINISHED"):
                    status = 2
                    print( "> " + line.rstrip())

                elif line.rstrip().startswith("Saving to:"):
                    items = line.rstrip().split("/")
                    print( "> " + items[0] + "/.../" + items[-3] + "/" + items[-2] + "/" + items[-1])

            else:
                print( "> " + line.rstrip())

    def getDataWithGeocodeAndPeriodFromMODIS(self, rootDir, targetDir, ext, geocodes = ["h00v08"], period = ['2014-361', '2015-001']):
        # needs to check exsiting data...

        start = time.time()

        for pr in period:
            tmps = pr.split("-")
            self.getAllDayDataWithGeocodeMODIS(rootDir, targetDir, ext, geocodes, tmps[0], tmps[1])

        # copy all into one target place
        print("> Copying to: \"" + targetDir + "\"")
        fileList = []
        for root, dirnames, filenames in os.walk(rootDir):
            for filename in fnmatch.filter(filenames, '*'+ext):
                fileList.append(os.path.join(root, filename))

        for item in fileList:
            shutil.copy2(item, targetDir)
        print( "> Copied " + str(len(fileList)) + " " + ext + " files")
        print(rootDir)
        print(fileList)
        print(targetDir)
        done = time.time()
        elapsed = done - start

        print( "> Processing time: " + ("%.1f" % elapsed) + " s")

    def getDataWithGeocodeAndPeriodFromLAI(self, rootDir, targetDir, ext, geocodes = ["h00v08"], period = ['2014-365', '2015-001'], period2 = ['2014.12.31', '2015.01.01']):
        # needs to check exsiting data...

        start = time.time()

        for i in range(len(period)):
            tmps = period[i].split("-")
            self.getAllDayDataWithGeocodeLAI(rootDir, targetDir, ext, geocodes, tmps[0], tmps[1], period2[i])

        # copy all into one target place
        print("> Copying to: \"" + targetDir + "\"")
        fileList = []
        for root, dirnames, filenames in os.walk(rootDir):
            for filename in fnmatch.filter(filenames, '*'+ext):
                fileList.append(os.path.join(root, filename))

        for item in fileList:
            shutil.copy2(item, targetDir)
        print("> Copied " + str(len(fileList)) + " " + ext + " files")

        done = time.time()
        elapsed = done - start

        print("> Processing time: " + ("%.1f" % elapsed) + " s")

    def getGeocodes(self, shapeFile, projectionFile, gridFile, gridShape):
        outRef ='GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]'
        inRef2 = 'PROJCS["Sinusoidal",GEOGCS["GCS_Undefined",DATUM["Undefined",SPHEROID["User_Defined_Spheroid",6371007.181,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Sinusoidal"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],UNIT["Meter",1.0]]'
        
        driver = ogr.GetDriverByName("ESRI Shapefile")
        dataSource = driver.Open(shapeFile, 0)

        if dataSource == None:
            print("> No shx file in the shape zip. Try to restore shx.")
            cmd = ["ogrinfo", shapeFile, "--config", "SHAPE_RESTORE_SHX", "YES"]
            p = sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)
            for line in iter(p.stdout.readline, b''):
                print("> " + line.decode().rstrip())
            dataSource = driver.Open(shapeFile, 0)

        layer = dataSource.GetLayer()
        minX, maxX, minY, maxY = layer.GetExtent()

        # minY, max, minY, maxY = layer.GetExtent()


        # Create ring
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(minX, minY), ring.AddPoint(maxX, minY), ring.AddPoint(maxX, maxY), ring.AddPoint(minX, maxY), ring.AddPoint(minX, minY)

        # Create polygon
        mbb = ogr.Geometry(ogr.wkbPolygon)
        mbb.AddGeometry(ring)
        # # Transform
        inSpatialRef = layer.GetSpatialRef()
        inSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        # print inSpatialRef
        outSpatialRef = osr.SpatialReference()
        # outSpatialRef.ImportFromEPSG(4326)
        outSpatialRef.ImportFromWkt(outRef)
        outSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
        mbb.Transform(coordTransform)
        mbb.FlattenTo2D()

        print(mbb.GetEnvelope())

        # check from grid shapefile
        list1 = []
        driver2 = ogr.GetDriverByName("ESRI Shapefile")
        dataSource2 = driver2.Open(gridShape, 0)
        layer2 = dataSource2.GetLayer()
        # inSpatialRef2 = layer2.GetSpatialRef()
        inSpatialRef2 = osr.SpatialReference()
        inSpatialRef2.ImportFromWkt(inRef2)
        inSpatialRef2.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        outSpatialRef2 = osr.SpatialReference()
        outSpatialRef2.ImportFromWkt(outRef)
        outSpatialRef2.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        coordTransform2 = osr.CoordinateTransformation(inSpatialRef2, outSpatialRef2)
        # print((inSpatialRef2, outSpatialRef2))


        for feature in layer2:
            geom = feature.GetGeometryRef()
            geom.Transform(coordTransform2)
            if(geom.Contains(mbb)):
                if geom.IsValid() and geom.IsSimple():
                    print('contains', geom.GetEnvelope())
                    list1.append("h" + str(int(feature.GetField("h"))).zfill(2) + "v" + str(int(feature.GetField("v"))).zfill(2))


        if len(list1) == 0:
            for i in range(layer2.GetFeatureCount()):
                feature = layer2.GetFeature(i)
                geom = feature.GetGeometryRef()
                geom.Transform(coordTransform2)

                if(geom.Intersects(mbb)):
                    if geom.IsValid() and geom.IsSimple():
                        print('intersect', geom.GetEnvelope())
                        list1.append("h" + str(int(feature.GetField("h"))).zfill(2) + "v" + str(int(feature.GetField("v"))).zfill(2))

        # final check with grid.txt
        list2 = []
        f = open(gridFile, 'rU')
        f.readline()
        for line in f:
            l = line.strip()
            items = l.split()

            minx = float(items[2])            
            maxx = float(items[3])
            miny = float(items[4])
            maxy = float(items[5])            

            tempRing = ogr.Geometry(ogr.wkbLinearRing)
            tempRing.AddPoint(minx, miny), tempRing.AddPoint(maxx, miny), tempRing.AddPoint(maxx, maxy), tempRing.AddPoint(minx, maxy), tempRing.AddPoint(minx, miny)

            tempMbb = ogr.Geometry(ogr.wkbPolygon)
            tempMbb.AddGeometry(tempRing)

            ivihPolygon = [items[0], items[1], tempMbb]

            # print(tempMbb.GetEnvelope())

            if(tempMbb.Contains(mbb)):
                list2.append("h" + items[1].zfill(2) + "v" + items[0].zfill(2))
            elif(tempMbb.Intersects(mbb)):
                list2.append("h" + items[1].zfill(2) + "v" + items[0].zfill(2))

        geocodes = list(set(list1).intersection(list2))

        # print(list1, list2)


        if len(geocodes) == 0:
            print("Getting intersect geocode failed")
            raise Exception('')

        print(geocodes, end='')
        print("is (are) extracted!")        

        return geocodes

    def getDateCntMODIS(self, dateFromString, dateToString):
        items = dateFromString.split("/")
        fyear = int(items[2])
        fmonth = int(items[0])
        fdate = int(items[1])
        fdelta = dt(fyear, fmonth, fdate) - dt(fyear, 1, 1)

        items = dateToString.split("/")
        tyear = int(items[2])
        tmonth = int(items[0])
        tdate = int(items[1])
        tdelta = dt(tyear, tmonth, tdate) - dt(tyear, 1, 1)

        arr = []

        if fyear == tyear:
            start8day = ( (fdelta.days) / 8 ) * 8 + 1
            end8day = ( (tdelta.days) / 8 ) * 8 + 1
            while (start8day <= end8day):
                arr.append(str(fyear) + "-" + str(int(start8day)).zfill(3))
                start8day += 8

        else:
            start8day = ( (fdelta.days) / 8 ) * 8 + 1
            interEnd8day = 361
            interStart8day = 1
            end8day = ( (tdelta.days) / 8 ) * 8 + 1

            while (start8day <= interEnd8day):
                arr.append(str(fyear) + "-" + str(int(start8day)).zfill(3))
                start8day += 8

            while (interStart8day <= end8day):
                arr.append(str(tyear) + "-" + str(int(interStart8day)).zfill(3))
                interStart8day += 8

        print("Time period: ", end='')
        print(arr)

        return arr

    def getDateCntLAI(self, dateFromString, dateToString):
        items = dateFromString.split("/")
        fyear = int(items[2])
        fmonth = int(items[0])
        fdate = int(items[1])
        fdelta = dt(fyear, fmonth, fdate) - dt(fyear, 1, 1)

        items = dateToString.split("/")
        tyear = int(items[2])
        tmonth = int(items[0])
        tdate = int(items[1])
        tdelta = dt(tyear, tmonth, tdate) - dt(tyear, 1, 1)

        arr = []
        arr2 = []

        if fyear == tyear:
            start8day = ( (fdelta.days) / 4 ) * 4 + 1
            end8day = ( (tdelta.days) / 4 ) * 4 + 1
            while (start8day <= end8day):
                arr.append(str(fyear) + "-" + str(int(start8day)).zfill(3))
                thatDay = dt(fyear, 1, 1) + timedelta(days=start8day - 1)
                arr2.append(str(fyear) + "." + str(thatDay.month).zfill(2) + "." + str(thatDay.day).zfill(2))
                start8day += 4

        else:
            start8day = ( (fdelta.days) / 4 ) * 4 + 1
            interEnd8day = 365
            interStart8day = 1
            end8day = ( (tdelta.days) / 4 ) * 4 + 1

            while (start8day <= interEnd8day):
                arr.append(str(fyear) + "-" + str(int(start8day)).zfill(3))
                thatDay = dt(fyear, 1, 1) + timedelta(days=start8day - 1)
                arr2.append(str(fyear) + "." + str(thatDay.month).zfill(2) + "." + str(thatDay.day).zfill(2))
                start8day += 4

            while (interStart8day <= end8day):
                arr.append(str(tyear) + "-" + str(int(interStart8day)).zfill(3))
                thatDay = dt(tyear, 1, 1) + timedelta(days=interStart8day - 1)
                arr2.append(str(tyear) + "." + str(thatDay.month).zfill(2) + "." + str(thatDay.day).zfill(2))
                interStart8day += 4

        print("Time period: ", end='')
        print(arr)
        print(arr2)

        return arr, arr2

    def dateGenerator(self, start, end):
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    def getDataFromSMAP(self, rootDir, targetDir, ext, dateFrom, dateTo):

        start = time.time()

        items = dateFrom.split("/")
        fyear = int(items[2])
        fmonth = int(items[0])
        fdate = int(items[1])
        fDT = dt(fyear, fmonth, fdate)

        items = dateTo.split("/")
        tyear = int(items[2])
        tmonth = int(items[0])
        tdate = int(items[1])
        tDT = dt(tyear, tmonth, tdate)

        arr = []

        for item in self.dateGenerator(fDT, tDT):

            arr.append(item.strftime("%Y.%m.%d"))

            dataPath  = "/SMAP/SPL4SMGP.005/" + item.strftime("%Y.%m.%d") + "/*,"
            dataPath2 = "/SMAP/SPL4SMGP.005/" + item.strftime("%Y.%m.%d")
            serverAddress = "https://n5eil01u.ecs.nsidc.org/SMAP/SPL4SMGP.005/" + item.strftime("%Y.%m.%d")

            print("Data Fetching URL : " + serverAddress)

            cmd = ["wget", "--http-user=waterhub", "--http-password==4SrN*nn", "--load-cookies=" + os.path.expanduser("~") + "/.urs_cookies",
                    "--save-cookies=" + os.path.expanduser("~") + "/.urs_cookies", "--keep-session-cookies",
                    "--no-check-certificate", "--auth-no-challenge", "-w", "0.05", "-l", "0", "-r", "-nH", "-np",
                    "-I", dataPath+dataPath2, "-R", "*.htm,*.html", "-e", "robots=off", "-A", "*"+ext, serverAddress]

            # print ' '.join(cmd)

            p = sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)

            status = 0
            for line in iter(p.stdout.readline, b''):
                line = line.decode()
                # print "> " + line.rstrip()
                if status == 0:
                    print("> " + line.rstrip())
                    if line.rstrip().startswith("Saving to:"):
                        status = 1

                elif status == 1:
                    if line.rstrip().startswith("FINISHED"):
                        status = 2
                        print("> " + line.rstrip())

                    elif line.rstrip().startswith("Saving to:"):
                        print("> " + line.rstrip())

                else:
                    print("> " + line.rstrip())

        # copy all into one target place
        print("> Copying to: \"" + targetDir + "\"")
        fileList = []
        for root, dirnames, filenames in os.walk(rootDir):
            for filename in fnmatch.filter(filenames, '*'+ext):
                fileList.append(os.path.join(root, filename))

        for item in fileList:
            shutil.copy2(item, targetDir)
        print("> Copied " + str(len(fileList)) + " " + ext + " files")

        done = time.time()
        elapsed = done - start

        print("> Processing time: " + ("%.1f" % elapsed) + " s")

        return arr

    def getDataFromGPM(self, rootDir, targetDir, ext, dateFrom, dateTo, temporal_res):

        def getFileListForGPM(xml_url):
            req = requests.get(xml_url)
            data = req.text.split('\n')
            urls = [x.split('"')[1] for x in data if re.search('urlPath', x)]
            urls = [x for x in urls if x.split('.')[-1] == 'HDF5'] # to filter out .xml files
            return urls



        # https://gpm1.gesdisc.eosdis.nasa.gov/opendap/hyrax/GPM_L3/GPM_3IMERGHHE.05/2015/001/3B-HHR-E.MS.MRG.3IMERG.20150101-S000000-E002959.0000.V05B.HDF5
        # https://gpm1.gesdisc.eosdis.nasa.gov/opendap/hyrax/GPM_L3/GPM_3IMERGHH.05/2015/001/3B-HHR.MS.MRG.3IMERG.20150101-S000000-E002959.0000.V05B.HDF5
        # https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.05/2015/01/3B-DAY.MS.MRG.3IMERG.20150101-S000000-E235959.V05.nc4
        BASE_URL = 'https://gpm1.gesdisc.eosdis.nasa.gov/opendap/'
        VERSION = '06'

        # curl -s 'https://gpm1.gesdisc.eosdis.nasa.gov/opendap/hyrax/GPM_L3/GPM_3IMERGHHE.05/2015/001/catalog.xml' | grep urlPath | cut -d\" -f2

        start = time.time()

        items = dateFrom.split("/")
        fyear = int(items[2])
        fmonth = int(items[0])
        fdate = int(items[1])
        fDT = dt(fyear, fmonth, fdate)

        items = dateTo.split("/")
        tyear = int(items[2])
        tmonth = int(items[0])
        tdate = int(items[1])
        tDT = dt(tyear, tmonth, tdate)

        arr = []

        for item in self.dateGenerator(fDT, tDT):
            arr.append(item.strftime("%Y.%m.%d"))

            # generate data url list to download
            data_urls = []
            if temporal_res == 'Daily':
                data_url = (BASE_URL + 'GPM_L3/GPM_3IMERGDF.' + VERSION + '/%s/3B-DAY.MS.MRG.3IMERG.%s-S000000-E235959.V' + VERSION + '.nc4' + ext)%(item.strftime('%Y/%m'), item.strftime('%Y%m%d'))
                data_urls = [data_url]

            elif temporal_res == '30m':
                xml_url = (BASE_URL + 'hyrax/GPM_L3/GPM_3IMERGHH.' + VERSION + '/%s/%s/catalog.xml') % (item.strftime('%Y'), item.strftime('%j'))
                data_urls = getFileListForGPM(xml_url)
                data_urls = [BASE_URL + 'hyrax' + x + ext for x in data_urls]

            elif temporal_res == '30m_NRT':
                xml_url = (BASE_URL + 'hyrax/GPM_L3/GPM_3IMERGHHE.' + VERSION + '/%s/%s/catalog.xml') % (item.strftime('%Y'), item.strftime('%j'))
                data_urls = getFileListForGPM(xml_url)
                data_urls = [BASE_URL + 'hyrax' + x + ext for x in data_urls]

            print(data_urls)

            # prepare Downloading
            os.system('rm -rf ~/.netrc ~/.urs_cookies')
            os.system('echo "machine urs.earthdata.nasa.gov login waterhub password =4SrN*nn" > ~/.netrc')
            os.system('chmod 0600 ~/.netrc')
            os.system('touch ~/.urs_cookies')

            # download files

            for i, data_url in enumerate(data_urls):
                cmd = 'curl -n -c ~/.urs_cookies -b ~/.urs_cookies -LJO --url'.split(' ')
                cmd.append(data_url)

                print('Downloading data files (' + str(i+1) + '/' + str(len(data_urls)) + ')')

                print(' '.join(cmd))
                p = sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=rootDir)

                status = 0
                for line in iter(p.stdout.readline, b''):
                    line = line.decode()
                    if 'Saved to' in line or 'Warning' in line:
                        print("> " + line)


        # copy all into one target place
        print("> Copying to: \"" + targetDir + "\"")
        fileList = []
        print(rootDir)
        for root, dirnames, filenames in os.walk(rootDir):
            for filename in fnmatch.filter(filenames, '*'+ext):
                fileList.append(os.path.join(root, filename))

        for item in fileList:
            shutil.copy2(item, targetDir)
        print("> Copied " + str(len(fileList)) + " " + ext + " files")

        done = time.time()
        elapsed = done - start

        print("> Processing time: " + ("%.1f" % elapsed) + " s")

        return arr

# wrapper
    # def getData(self, repo="MODIS-LAI/FPAR", dateFrom = "01/01/2017", dateTo = "01/04/2017", shapeFileName="subs1_projected_171936.shp", currentDir=None):
    # #####
    # ##### NOTE THAT currentDir == None is for "local executions" and else is for "cluster executions"
    # #####
    def getData(self, repo="MODIS-ET/PET/LE/PLE", dateFrom = "01/01/2014", dateTo = "01/09/2014", shapeFileName="subs1_projected_171936.shp", currentDir=None):

        
        self.WORKING_DIR = currentDir
        fileName = os.path.abspath(__file__)
        pathName = os.path.dirname(fileName)
        appDir = os.path.dirname(pathName)

        shapeDir = self.WORKING_DIR + "/shape"

        prjFilePath = HGUtil.DATA_DIR + "/6974.prj"   
        gridFilePath = HGUtil.DATA_DIR + "/grid.txt"  
        gridShapePath = HGUtil.DATA_DIR + "/modis_grid.shp" 
        shpFilePath = shapeDir + "/" + shapeFileName

        rootDir = self.WORKING_DIR + "/"
        targetDir = self.WORKING_DIR + "/inputs"
        ext = ""

        # make /inputs dir
        if os.path.exists(targetDir):
            folder = targetDir
            for the_file in os.listdir(folder):
                file_path = os.path.join(folder, the_file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(e)
        else:
            os.makedirs(targetDir)

        if repo[:3] == "GPM":
            # delete downloaded dir
            rootDir = self.WORKING_DIR + "/GPM"
            self.removeAndMakeDir(rootDir)

            # execute
            #ext = '.nc4'
            ext = HGUtil.GPM_FILE_EXT
            period = self.getDataFromGPM(rootDir, targetDir, ext, dateFrom, dateTo, repo[5:-1])

            # delete downloaded dir
            rmcmd = ["rm", "-rf", rootDir]
            p = sp.Popen(rmcmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)
            for line in iter(p.stdout.readline, b''):
                print("> " + line.decode().rstrip())

        elif repo == "SMAP":

            # delete downloaded dir
            rootDir = self.WORKING_DIR + "/SMAP"
            self.removeAndMakeDir(rootDir)

            # execute
            ext = ".h5"
            period = self.getDataFromSMAP(rootDir, targetDir, ext, dateFrom, dateTo)

            # delete downloaded dir
            rmcmd = ["rm", "-rf", rootDir]
            p = sp.Popen(rmcmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)
            for line in iter(p.stdout.readline, b''):
                print("> " + line.decode().rstrip())

        elif repo == "MODIS-ET/PET/LE/PLE":
            ### MODIS DATA
            # del downloaded data
            rootDir = self.WORKING_DIR + "/data"
            self.removeAndMakeDir(rootDir)

            # execute
            period = self.getDateCntMODIS(dateFrom, dateTo)
            geocodes = self.getGeocodes(shpFilePath, prjFilePath, gridFilePath, gridShapePath)
            ext = ".hdf"
            self.getDataWithGeocodeAndPeriodFromMODIS(rootDir, targetDir, ext, geocodes, period)

            # delete downloaded data
            rmcmd = ["rm", "-rf", rootDir]
            p = sp.Popen(rmcmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)
            for line in iter(p.stdout.readline, b''):
                print("> " + line.decode().rstrip())


        elif repo == "MODIS-LAI/FPAR":

            rootDir = self.WORKING_DIR + "/MOTA"
            self.removeAndMakeDir(rootDir)

            # execute
            period, period2 = self.getDateCntLAI(dateFrom, dateTo)
            geocodes = self.getGeocodes(shpFilePath, prjFilePath, gridFilePath, gridShapePath)
            ext = ".hdf"
            self.getDataWithGeocodeAndPeriodFromLAI(rootDir, targetDir, ext, geocodes, period, period2)

            # delete downloaded data
            rmcmd = ["rm", "-rf", rootDir]
            p = sp.Popen(rmcmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)
            for line in iter(p.stdout.readline, b''):
                print("> " + line.decode().rstrip())
        else:
            print("Unknown repository " + repo)
            period = []


        # getAllDayData(rootDir, targetDir, ext, "2013", "033")
        # self.getAllYearDataWithGeocode(rootDir, targetDir, ext, geocodes, "2013")
        print("> Done: Data fetching")

        return period

    def removeAndMakeDir(self, dir):
        if os.path.exists(dir):
            print("> Clear " + dir + "!!")
            rmcmd = ["rm", "-rf", dir]
            p = sp.Popen(rmcmd,stdout=sp.PIPE,stderr=sp.STDOUT,cwd=self.WORKING_DIR)
            for line in iter(p.stdout.readline, b''):
                print("> " + line.decode().rstrip())
        os.makedirs(dir)

if __name__ == "__main__":
	Fetch().getData()
