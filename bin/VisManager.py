from osgeo import ogr, osr
import os, sys
import json
import shapely.wkt
import geojson
import csv

class VisManager:

    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/bin'

    def create_vis_data(self, datatype, shapeFilePath, csvFilePath, outputPath):

        driver = ogr.GetDriverByName("ESRI Shapefile")
        dataSource = driver.Open(shapeFilePath, 0)
        layer = dataSource.GetLayer()

        gs = []
        dateList = []
        minMax = {}
        idToValuesInDays = {}

        idToValuesInDaysTimes = None
        dateTimeList = None

        subbasinList = []
        collection = None

        minX = sys.float_info.max
        maxX = -sys.float_info.max
        minY = sys.float_info.max
        maxY = -sys.float_info.max

        maxNumberOfSubbasin = 900000
        cnt = 0

        if datatype == "MODIS" or datatype == "MODIS-ET/PET/LE/PLE":
            #####################################################
            # Iterate shp file to extract each geometry
            #####################################################
            #6974
            source = osr.SpatialReference()
            source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            # sourceFile = open("/home/nujwoo/jupyter/hydroglobe/timeSeries/prj/6974.prj", 'r')
            sourceFile = open(self.APP_DIR + "/data/6974.prj", 'r')
            sourceInfo = sourceFile.read()
            source.ImportFromESRI([sourceInfo])
            sourceFile.close()
            #4326
            target = osr.SpatialReference()
            target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            # target.ImportFromEPSG(4326)
            target.ImportFromWkt('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
            #transform
            transform = osr.CoordinateTransformation(source, target)

            for feature in layer:
                sid = str(feature.GetField("Subbasin"))
                et = float(feature.GetField("ET")) #TODO: here
                le = float(feature.GetField("LE"))
                pet = float(feature.GetField("PET"))
                ple = float(feature.GetField("PLE"))

                subbasinList.append(sid)

                if cnt < maxNumberOfSubbasin:
                    geom = feature.GetGeometryRef()
                    geom.Transform(transform)
                    (minXtemp, maxXtemp, minYtemp, maxYtemp) = geom.GetEnvelope()
                    # print geom.GetEnvelope()
                    if minXtemp < minX:
                        minX = minXtemp
                    if maxXtemp > maxX:
                        maxX = maxXtemp
                    if minYtemp < minY:
                        minY = minYtemp
                    if maxYtemp > maxY:
                        maxY = maxYtemp

                    polygon = shapely.wkt.loads(geom.ExportToWkt())
                    geoJSON = geojson.Feature(geometry=polygon, properties={
                                    'subbasin': sid,
                                    'ET': et,
                                    'LE': le,
                                    'PET': pet,
                                    'PLE': ple})

                    gs.append(geoJSON)
                cnt+=1

            collection = geojson.FeatureCollection(gs)

            #####################################################
            # Read output csv file, make dics for [date][id][bandName] = value
            #####################################################
            with open(csvFilePath, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',', quotechar='|',skipinitialspace=True)
                for row in reader:
                    date = str(row["year"]) + "-" + str(row["day"])
                    if date not in idToValuesInDays:
                        idToValuesInDays[date] = {}
                        dateList.append(date)

                    if str(row["subbasin"]) not in idToValuesInDays[date]:
                        idToValuesInDays[date][str(row["subbasin"])] = {}

                    idToValuesInDays[date][str(row["subbasin"])]["ET"] = float(row["ET"])
                    idToValuesInDays[date][str(row["subbasin"])]["LE"] = float(row["LE"])
                    idToValuesInDays[date][str(row["subbasin"])]["PET"] = float(row["PET"])
                    idToValuesInDays[date][str(row["subbasin"])]["PLE"] = float(row["PLE"])

            #####################################################
            # Get each band's min/max
            #####################################################
            dateList = sorted(dateList)
            etMin = 9999999
            etMax = -9999999
            leMin = 9999999
            leMax = -9999999
            petMin = 9999999
            petMax = -9999999
            pleMin = 9999999
            pleMax = -9999999
            for date in dateList:
            #     values = idToValuesInDays[date[0]]
                for k,v in iter(idToValuesInDays[date].items()):
                    if v["ET"] < etMin:
                        etMin = v["ET"]
                    if v["ET"] > etMax:
                        etMax = v["ET"]
                    if v["LE"] < leMin:
                        leMin = v["LE"]
                    if v["LE"] > leMax:
                        leMax = v["LE"]
                    if v["PET"] < petMin:
                        petMin = v["PET"]
                    if v["PET"] > petMax:
                        petMax = v["PET"]
                    if v["PLE"] < pleMin:
                        pleMin = v["PLE"]
                    if v["PLE"] > pleMax:
                        pleMax = v["PLE"]
                # date.append(min)
                # date.append(max)

            minMax["ET"] = [etMin, etMax]
            minMax["LE"] = [leMin, leMax]
            minMax["PET"] = [petMin, petMax]
            minMax["PLE"] = [pleMin, pleMax]

        elif datatype == "MODIS-LAI" or datatype == "MODIS-LAI/FPAR":
            #####################################################
            # Iterate shp file to extract each geometry
            #####################################################
            #6974
            source = osr.SpatialReference()
            source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            sourceFile = open(self.APP_DIR + "/data/6974.prj", 'r')
            sourceInfo = sourceFile.read()
            source.ImportFromESRI([sourceInfo])
            sourceFile.close()
            #4326
            target = osr.SpatialReference()
            target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            # target.ImportFromEPSG(4326)
            target.ImportFromWkt('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
            #transform
            transform = osr.CoordinateTransformation(source, target)

            for feature in layer:
                sid = str(feature.GetField("Subbasin"))
                fpar = float(feature.GetField("FPAR"))
                lai = float(feature.GetField("LAI"))

                subbasinList.append(sid)

                if cnt < maxNumberOfSubbasin:
                    geom = feature.GetGeometryRef()
                    geom.Transform(transform)
                    (minXtemp, maxXtemp, minYtemp, maxYtemp) = geom.GetEnvelope()

                    if minXtemp < minX:
                        minX = minXtemp
                    if maxXtemp > maxX:
                        maxX = maxXtemp
                    if minYtemp < minY:
                        minY = minYtemp
                    if maxYtemp > maxY:
                        maxY = maxYtemp

                    polygon = shapely.wkt.loads(geom.ExportToWkt())
                    geoJSON = geojson.Feature(geometry=polygon, properties={
                                    'subbasin': sid,
                                    'FPAR': fpar,
                                    'LAI': lai})

                    gs.append(geoJSON)

                cnt+=1

            collection = geojson.FeatureCollection(gs)

            #####################################################
            # Read output csv file, make dics for [date][id][bandName] = value
            #####################################################
            with open(csvFilePath, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',', quotechar='|',skipinitialspace=True)
                for row in reader:
                    date = str(row["year"]) + "-" + str(row["day"])
                    if date not in idToValuesInDays:
                        idToValuesInDays[date] = {}
                        dateList.append(date)

                    if str(row["subbasin"]) not in idToValuesInDays[date]:
                        idToValuesInDays[date][str(row["subbasin"])] = {}

                    idToValuesInDays[date][str(row["subbasin"])]["FPAR"] = float(row["FPAR"])
                    idToValuesInDays[date][str(row["subbasin"])]["LAI"] = float(row["LAI"])

            #####################################################
            # copy csv file and shape file to results directory
            #####################################################
            dateList = sorted(dateList)
            fparMin = 9999999
            fparMax = -9999999
            laiMin = 9999999
            laiMax = -9999999
            for date in dateList:
            #     values = idToValuesInDays[date[0]]
                for k,v in iter(idToValuesInDays[date].items()):
                    if v["FPAR"] < fparMin:
                        fparMin = v["FPAR"]
                    if v["FPAR"] > fparMax:
                        fparMax = v["FPAR"]
                    if v["LAI"] < laiMin:
                        laiMin = v["LAI"]
                    if v["LAI"] > laiMax:
                        laiMax = v["LAI"]

                # date.append(min)
                # date.append(max)

            minMax["FPAR"] = [fparMin, fparMax]
            minMax["LAI"] = [laiMin, laiMax]

        elif datatype == "SMAP":
            #####################################################
            # Iterate shp file to extract each geometry
            #####################################################
            #6933
            source = osr.SpatialReference()
            source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            sourceFile = open(self.APP_DIR + "/data/6933.prj", 'r')
            sourceInfo = sourceFile.read()
            source.ImportFromESRI([sourceInfo])
            sourceFile.close()
            #4326
            target = osr.SpatialReference()
            target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            # target.ImportFromEPSG(4326)
            target.ImportFromWkt('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
            #transform
            transform = osr.CoordinateTransformation(source, target)

            for feature in layer:
                sid = str(feature.GetField("Subbasin"))
                surface = float(feature.GetField("surface"))
                rootzone = float(feature.GetField("rootzone"))

                subbasinList.append(sid)

                if cnt < maxNumberOfSubbasin:
                    geom = feature.GetGeometryRef()
                    geom.Transform(transform)
                    (minXtemp, maxXtemp, minYtemp, maxYtemp) = geom.GetEnvelope()

                    if minXtemp < minX:
                        minX = minXtemp
                    if maxXtemp > maxX:
                        maxX = maxXtemp
                    if minYtemp < minY:
                        minY = minYtemp
                    if maxYtemp > maxY:
                        maxY = maxYtemp

                    polygon = shapely.wkt.loads(geom.ExportToWkt())
                    geoJSON = geojson.Feature(geometry=polygon, properties={
                                    'subbasin': sid,
                                    'surface': surface,
                                    'rootzone': rootzone})

                    gs.append(geoJSON)

                cnt+=1

            collection = geojson.FeatureCollection(gs)

            #####################################################
            # Read output csv file, make dics for [date][id][bandName] = value
            #####################################################
            # THIS IS DAILYDATA
            with open(csvFilePath, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',', quotechar='|',skipinitialspace=True)
                for row in reader:
                    date = str(row["year"]) + "-" + str(row["date"])
                    if date not in idToValuesInDays:
                        idToValuesInDays[date] = {}
                        dateList.append(date)

                    if str(row["subbasin"]) not in idToValuesInDays[date]:
                        idToValuesInDays[date][str(row["subbasin"])] = {}

                    idToValuesInDays[date][str(row["subbasin"])]["surface"] = float(row["surface"])
                    idToValuesInDays[date][str(row["subbasin"])]["rootzone"] = float(row["rootzone"])

            # THIS IS HOURLYDATA
            idToValuesInDaysTimes = {}
            dateTimeList = []
            csvFilePath_hours = csvFilePath[0:-10] + ".csv"
            with open(csvFilePath_hours, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',', quotechar='|',skipinitialspace=True)
                for row in reader:
                    date = str(row["year"]) + "-" + str(row["date"]) + "-" + str(row["time"])
                    if date not in idToValuesInDaysTimes:
                        idToValuesInDaysTimes[date] = {}
                        dateTimeList.append(date)

                    if str(row["subbasin"]) not in idToValuesInDaysTimes[date]:
                        idToValuesInDaysTimes[date][str(row["subbasin"])] = {}

                    idToValuesInDaysTimes[date][str(row["subbasin"])]["surface"] = float(row["surface"])
                    idToValuesInDaysTimes[date][str(row["subbasin"])]["rootzone"] = float(row["rootzone"])


            #####################################################
            # copy csv file and shape file to results directory
            #####################################################
            dateList = sorted(dateList)
            surfaceMin = 9999999
            surfaceMax = -9999999
            rootzoneMin = 9999999
            rootzoneMax = -9999999
            for date in dateList:
            #     values = idToValuesInDays[date[0]]
                for k,v in iter(idToValuesInDays[date].items()):
                    if v["surface"] < surfaceMin:
                        surfaceMin = v["surface"]
                    if v["surface"] > surfaceMax:
                        surfaceMax = v["surface"]
                    if v["rootzone"] < rootzoneMin:
                        rootzoneMin = v["rootzone"]
                    if v["rootzone"] > rootzoneMax:
                        rootzoneMax = v["rootzone"]

                # date.append(min)
                # date.append(max)

            minMax["surface"] = [surfaceMin, surfaceMax]
            minMax["rootzone"] = [rootzoneMin, rootzoneMax]

        elif "GPM" in datatype:
            #####################################################
            # Iterate shp file to extract each geometry
            #####################################################
            #6933
            source = osr.SpatialReference()
            source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            sourceFile = open(self.APP_DIR + "/data/4326.prj", 'r')
            sourceInfo = sourceFile.read()
            source.ImportFromESRI([sourceInfo])
            sourceFile.close()
            #4326
            target = osr.SpatialReference()
            target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            # target.ImportFromEPSG(4326)
            target.ImportFromWkt('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
            #transform
            transform = osr.CoordinateTransformation(source, target)

            for feature in layer:
                sid = str(feature.GetField("Subbasin"))
                precip = float(feature.GetField("PRECIP"))

                subbasinList.append(sid)

                if cnt < maxNumberOfSubbasin:
                    geom = feature.GetGeometryRef()
                    geom.Transform(transform)
                    (minXtemp, maxXtemp, minYtemp, maxYtemp) = geom.GetEnvelope()

                    if minXtemp < minX:
                        minX = minXtemp
                    if maxXtemp > maxX:
                        maxX = maxXtemp
                    if minYtemp < minY:
                        minY = minYtemp
                    if maxYtemp > maxY:
                        maxY = maxYtemp

                    polygon = shapely.wkt.loads(geom.ExportToWkt())
                    geoJSON = geojson.Feature(geometry=polygon, properties={
                                    'subbasin': sid,
                                    'PRECIP': precip})

                    gs.append(geoJSON)

                cnt+=1

            collection = geojson.FeatureCollection(gs)

            #####################################################
            # Read output csv file, make dics for [date][id][bandName] = value
            #####################################################

            with open(csvFilePath, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',', quotechar='|',skipinitialspace=True)
                for row in reader:
                    date = str(row["date"]) + "-" + str(row["start_time"]) + "-" + str(row["end_time"])
                    if date not in idToValuesInDays:
                        idToValuesInDays[date] = {}
                        dateList.append(date)

                    if str(row["subbasin"]) not in idToValuesInDays[date]:
                        idToValuesInDays[date][str(row["subbasin"])] = {}

                    idToValuesInDays[date][str(row["subbasin"])]["PRECIP"] = float(row["PRECIP"])



            #####################################################
            # copy csv file and shape file to results directory
            #####################################################
            dateList = sorted(dateList)
            precipMin = 9999999
            precipMax = -9999999
            for date in dateList:
            #     values = idToValuesInDays[date[0]]
                for k,v in iter(idToValuesInDays[date].items()):
                    if v["PRECIP"] < precipMin:
                        precipMin = v["PRECIP"]
                    if v["PRECIP"] > precipMax:
                        precipMax = v["PRECIP"]

                # date.append(min)
                # date.append(max)

            minMax["PRECIP"] = [precipMin, precipMax]


        with open(outputPath + '/vis_geojson.js', 'w') as f:
            f.write("visJsonpCallback(" + geojson.dumps(collection) + ");")


        visinfo = dict()
        visinfo['minX'] = minX
        visinfo['minY'] = minY
        visinfo['maxX'] = maxX
        visinfo['maxY'] = maxY

        visinfo['idToValuesInDays'] = idToValuesInDays
        visinfo['dateList'] = dateList
        visinfo['minMax'] = minMax
        visinfo['subbasinList'] = subbasinList
        if 'GPM' in datatype:
            visinfo['datatype'] = 'GPM'
            visinfo['temporal_res'] = datatype[5:-1]
        else:
            visinfo['datatype'] = datatype

        visinfo['idToValuesInDaysTimes'] = idToValuesInDaysTimes
        visinfo['dateTimeList'] = dateTimeList

        with open(outputPath + '/vis_info.out', 'w') as f:
            json.dump(visinfo, f)
