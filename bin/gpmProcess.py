from osgeo import gdal, ogr, osr
import  os, sys, glob
import time
from datetime import datetime as dt
from datetime import timedelta
import math
import collections
import logging
import re
from shapely.geometry import box, shape
import numpy as np
import sqlite3
import csv
from HGUtil import HGUtil

from DataFetch import Fetch
dataFetch = Fetch()

_print = print
def print(*args, **kw):
    HGUtil.JOBLOG_FUNC(*args, **kw)
    # _print(*args, **kw)
    
def has_field(layer, name):
    ldefn = layer.GetLayerDefn()
    for i in range(ldefn.GetFieldCount()):
        fdefn = ldefn.GetFieldDefn(i)
        if fdefn.name == name:
            return True
    return False


def remove_allfiles(folderroot):
    filelist=glob.glob(folderroot+'/*.*')
    #return filelist
    for f in filelist:
        os.remove(f)

def get_name(path):
    return os.path.basename(os.path.splitext(path)[0])

class timeSeriesGPM:

    def transform_shapes_ogr(self, infile,outfile,out_prj):
        (outfilepath, outfilename) = os.path.split(outfile)
        (outfileshortname, extension) = os.path.splitext(outfilename)
        driver = ogr.GetDriverByName('ESRI Shapefile')
        indataset = driver.Open(infile, 0)
        if indataset is None:
            print('Could not open file')
            sys.exit(1)
        inlayer = indataset.GetLayer()
        inSpatialRef = inlayer.GetSpatialRef()
        inSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        outSpatialRef = osr.SpatialReference()
        outSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        
        prj_file = open(out_prj, 'r')
        prj_txt = prj_file.read()
        outSpatialRef.ImportFromESRI([prj_txt]) # MODIS SINUSOIDAL GRID
        # create Coordinate Transformation
        coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
        # Create the output shapefile but check first if file exists
        if os.path.exists(outfile):
            print(outfile, ' file already exists. Will try to delete')
            driver.DeleteDataSource(outfile)   #TODO:  This apparently does not work!
        outdataset = driver.CreateDataSource(outfile)
        if outdataset is None:
            print('Could not create file: ', outfile)
            sys.exit(1)
        outlayer = outdataset.CreateLayer(outfileshortname, geom_type=ogr.wkbPolygon)
        #iluk
        has_subbasin = False
        if has_field(inlayer, 'Subbasin'):
            feature = inlayer.GetFeature(0)
            fieldDefn1 = feature.GetFieldDefnRef('Subbasin')
            outlayer.CreateField(fieldDefn1)
            has_subbasin = True
        else:
            outlayer.CreateField(ogr.FieldDefn('Subbasin', ogr.OFTInteger))
        outlayer.CreateField(ogr.FieldDefn('PRECIP', ogr.OFTReal))
        featureDefn = outlayer.GetLayerDefn()
        infeature = inlayer.GetNextFeature()
        index=1
        while infeature:
            #get the input geometry
            geometry = infeature.GetGeometryRef()
            #reproject the geometry, each one has to be projected seperately
            geometry.Transform(coordTransform)
            #create a new output feature
            outfeature = ogr.Feature(featureDefn)
            #set the geometry and attribute
            outfeature.SetGeometry(geometry)
            if has_subbasin:
                outfeature.SetField('Subbasin', infeature.GetField('Subbasin'))
            else:
                outfeature.SetField('Subbasin', index)
            #add the feature to the output shapefile
            outlayer.CreateFeature(outfeature)
            #destroy the features and get the next input features
            outfeature.Destroy
            infeature.Destroy
            infeature = inlayer.GetNextFeature()
            index += 1
        #close the shapefiles
        indataset.Destroy()
        outdataset.Destroy()
        #create the prj projection file
        outSpatialRef.MorphToESRI()
        file = open(outfilepath + '/'+ outfileshortname + '.prj', 'w')
        file.write(outSpatialRef.ExportToWkt())
        file.close()


    def time_info(self, hdf_name):
        timeinfo = hdf_name.split('.')[4].split('-')
        return timeinfo[0], timeinfo[1][1:], timeinfo[2][1:]


    def dateGenerator(self, start, end):
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    #---------------------------------------------------------------------------------------------------------------------------------
    #if __name__=='__main__':
    # if True:
    def run(self, repo="GPM (Daily)", dateFrom = "05/01/2016", dateTo = "05/01/2016", shapeFileName="subs1_projected_171936.shp", currentDir = None):
        #TODO:  use INI file and ConfigParser to define constants, like ROOT, folder names, file names, output/print options, MAX_CELLS,...
        # Change to your project root directory
        # root= os.path.expanduser("~") + "/hydroglobeRun" # for Jaewoo

        if currentDir == None:
            root = os.path.expanduser("~") + "/hydroglobeRun" # for Jaewoo
            # set up folders
            folder_shape = root + "/shape"
            folder_temp = root + "/temp"
            folder_output = root + "/output"
            folder_hdf = root + "/inputs"
            folder_prj = root + "/prj"
        else:
            root = currentDir
            fileName = os.path.abspath(__file__)
            pathName = os.path.dirname(fileName)
            appDir = os.path.dirname(pathName) + '/bin'
            # set up folders
            folder_shape = root + "/shape"
            folder_temp = root + "/temp"
            folder_output = root + "/output"
            folder_hdf = root + "/inputs"
            folder_prj = appDir + "/data"

        saving_subbasin_csv_files = False
        makeTempTIFF = False
        max_cells = -1  # set to 0 (or less) to disable, -1 to suppress printing details
        if (max_cells < 0):
            print_details = False
        else:
            print_details = True
        # clean up temp files
        try:
            remove_allfiles(folder_temp)
            remove_allfiles(folder_output)
        except OSError:
            print('*** Trouble removing temp files ***')

        # set up logging
        logfile = folder_output + "/logfile.log"
        with open(logfile, 'w'):  # clear log file first
            pass
        logging.basicConfig(filename=logfile, level=logging.INFO)


        basin_shapefile = glob.glob(folder_shape + "/*.shp")[0]
        basin_shapefile_name = get_name(basin_shapefile)

        # create CSV file for all results;  subbasin summary CSV files will be created from DB
        csv_file_name = folder_output + "/" + basin_shapefile_name + "_gpm_projection_results" + ".csv"
        csv_out = open(csv_file_name,'w')
        csv_out.truncate()
        csv_out.write('basin, subbasin, area, date, start_time, end_time, PRECIP, cells_total, cells_1, cells_partial, cells_0, cells_missing, process_time\n')

        # get basin layer from shapefile
        esri_shapefile_driver = ogr.GetDriverByName("ESRI Shapefile")
        basin_data_source = esri_shapefile_driver.Open(basin_shapefile, 1)
        basin_layer = basin_data_source.GetLayer()

        # get subbasin list
        print('Get feature (subbasin) list and add to DB')

        subbasins = []
        # iluk: Some shape file don't have 'Subbasin'
        if has_field(basin_layer, 'Subbasin'):
            for subbasin_feature in basin_layer:  # loop over subbasins
                subbasin_id = subbasin_feature.GetField('Subbasin')
                subbasins.append(subbasin_id)
        else:
            print ('Use index order as an ID')
            subbasins = range(1, basin_layer.GetFeatureCount() +1)

       # set up timing
        start_time = time.time()
        last_time = start_time
        current_time = dt.now().strftime('%H%M%S')
        print('Begin processing of basin shapefile: ', basin_shapefile_name)

        # set up cell counting
        num_cells_total = 0

        class ExceededMaxCells(Exception):
            pass



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
        outputPeriod = []
        for item in self.dateGenerator(fDT, tDT):
            arr.append(item.strftime("%m/%d/%Y"))

        isFirstHDF = True
        firstHDFName = ""

        for oneDay in arr:
            print("\n*** Processing " + oneDay + " data files  ***")
            period = dataFetch.getData(repo, oneDay, oneDay, shapeFileName, currentDir)
            for t in period:
                outputPeriod.append(t)


            # get GPM and basin shapefile file names
            list_of_hdfs = sorted(glob.glob(folder_hdf + "/*" + HGUtil.GPM_FILE_EXT))

            ##############################################################################################################
            if len(list_of_hdfs) == 0:
                # raise RuntimeError("\n*** Selected data may not exist in target repository ***")
                print("\n*** Selected data may not exist in target repository ***")
                continue

            # start loop over GPM HDF files
            for hdf in list_of_hdfs:
                try: # catch attribute exceptions
                    hdf_name = get_name(hdf)
                    capture_date, capture_stime, capture_etime = self.time_info(os.path.basename(hdf))
                    capture_id = "{0}S{1}E{2}".format(capture_date,capture_stime,capture_etime)

                    # transform shape file to ESPG 4326
                    projection_file = folder_prj + "/4326.prj"
                    projected_basin_shapefile = folder_output + "/" + basin_shapefile_name + "_" + capture_date + "_" + capture_stime + "_" + capture_etime + "_" + current_time + "_projected" + ".shp"
                    self.transform_shapes_ogr(basin_shapefile, projected_basin_shapefile, projection_file)

                    if isFirstHDF:
                        firstHDFName = basin_shapefile_name + "_" + capture_date + "_" + capture_stime + "_" + capture_etime+ "_" + current_time + "_projected"
                        isFirstHDF = False

                    # test wether HDF region overlaps basin of interest
                    # if IsOverlap(projected_basin_shapefile, hdf):
                    if True: #  has world shape.. so always be true
                        # begin processing grid from HDF raster file
                        grid_start_time = time.time()
                        print()
                        print('***')
                        print()
                        print('Begin projection of ', hdf_name, ' onto ', basin_shapefile_name)
                        logging.info("Begin projection of " + hdf_name + " onto " + basin_shapefile_name)
                        print('')

                        # extract dataset (array of subdatasets)
                        hdf_dataset = gdal.Open(hdf, gdal.GA_ReadOnly)
                        hdf_metadata = hdf_dataset.GetMetadata()

                        # extract subdataset, precipitationCal
                        precip_band_subdataset = gdal.Open(hdf_dataset.GetSubDatasets()[0][0], gdal.GA_ReadOnly) # extract precipationCal
                        precip_description = hdf_dataset.GetSubDatasets()[0][1]
                        print('GPM subdataset [precipitationCal] description: ', precip_description)
                        precip_band_metadata = precip_band_subdataset.GetMetadata()
                        precip_band_array = precip_band_subdataset.ReadAsArray().astype(np.float32)
                        # GPM dataset is needed to be rotated
                        precip_band_array = np.rot90(precip_band_array, 1)
                        precip_band_array = np.fliplr(precip_band_array)

                        # temp tiff.. do not need for results..
                        #
                        # if False: # change below two params to one prec.
                        #     precip_out_tif_name = folder_temp+"/"+basin_shapefile_name+"_precip_"+capture_id+".tif"
                        #     # print 'surface TIF file name: ', surface_out_tif_name
                        #     precip_out_tif = gdal.GetDriverByName('GTiff').Create(precip_out_tif_name, precip_band_subdataset.RasterXSize,
                        #         precip_band_subdataset.RasterYSize, 1,  gdal.GDT_Float32, ['COMPRESS=LZW', 'TILED=YES'])
                        #     gt = precip_band_subdataset.GetGeoTransform()
                        #     import math
                        #     rotation = (math.pi/180) * 90
                        #     new_geotransform = (gt[3], math.cos(rotation) * gt[1], -math.sin(rotation) * gt[1], -gt[0], math.sin(rotation) * gt[5], math.cos(rotation) * gt[5])
                        #     precip_out_tif.SetGeoTransform(new_geotransform)
                        #     # surface_out_tif.SetGeoTransform([0.0, 9003.050735029, 0.0, 0.0, 0, 9019.931728601])
                        #     precip_out_tif.SetProjection('PROJCS["unnamed",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9108"]],AUTHORITY["EPSG","4326"]],PROJECTION["Cylindrical_Equal_Area"],PARAMETER["standard_parallel_1",30],PARAMETER["central_meridian",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["Meter",1],AUTHORITY["epsg","6933"]]')
                        #     precip_out_tif.GetRasterBand(1).WriteArray(precip_band_array)
                        #     precip_out_tif.GetRasterBand(1).SetNoDataValue(0)
                        #     precip_out_tif = None


                        # define a grid cell
                        #lowerLeftX, lowerLeftY, upperRightX, upperRightY = -17357881.81713629,-7324184.56362408,17357881.81713629,7324184.56362408
                        # ESPG 4326, world size
                        lowerLeftX, lowerLeftY = -180.0, -90.0
                        upperRightX, upperRightY =  -lowerLeftX, -lowerLeftY

                        grid_cell_width = (upperRightX-lowerLeftX)/precip_band_array.shape[1]
                        grid_cell_height = (upperRightY-lowerLeftY)/precip_band_array.shape[0]
                        grid_cell_rect = ogr.Geometry(ogr.wkbLinearRing)
                        grid_cell_rect.AddPoint(lowerLeftX, lowerLeftY)
                        grid_cell_rect.AddPoint(lowerLeftX+grid_cell_width, lowerLeftY)
                        grid_cell_rect.AddPoint(lowerLeftX+grid_cell_width, lowerLeftY+grid_cell_height)
                        grid_cell_rect.AddPoint(lowerLeftX, lowerLeftY+grid_cell_height)
                        grid_cell_rect.AddPoint(lowerLeftX, lowerLeftY)
                        grid_cell_geom = ogr.Geometry(ogr.wkbPolygon)
                        grid_cell_geom.AddGeometry(grid_cell_rect)
                        grid_cell_area = grid_cell_geom.Area()
                        # print 'Grid cell area = ', grid_cell_area, '[',grid_cell_width,' x ', grid_cell_height, ']'

                        # get layer (basin) and its extent from re-projected shapefile
                        esri_shapefile_driver = ogr.GetDriverByName("ESRI Shapefile")
                        projected_basin_data_source = esri_shapefile_driver.Open(projected_basin_shapefile, 1)
                        projected_basin_layer = projected_basin_data_source.GetLayer()
                        x_min, x_max, y_min, y_max = projected_basin_layer.GetExtent()
                        # print 'Extent of layer (basin): ', x_min, x_max, y_min, y_max


                        # main loop over features (subbasins), and grid cells (raster array) to accumulate weighted values for intersections
                        cnt = 0
                        try: # use try-except to limit grid cells to be processed (primarily for testing)
                            for i, subbasin_feature in enumerate(projected_basin_layer):  # loop over subbasins
                                subbasin_feature_start_time = time.time()
                                subbasin_feature_geom = subbasin_feature.GetGeometryRef()
                                #subbasin_id = subbasin_feature.GetField('Subbasin')
                                subbasin_id = subbasins[i]
                                subbasin_area = subbasin_feature_geom.Area()
                                # if print_details:
                                    # print '=== Subbasin ', subbasin_id
                                # print 'Area of feature (subbasin) = ', subbasin_area
                                subbasin_precip_weighted_value_sum = 0.0
                                subbasin_weight_sum = 0.0
                                #print 'Geom of feature (subbasin): ', subbasin_feature_geom.ExportToWkt()
                                x_min, x_max, y_min, y_max = subbasin_feature_geom.GetEnvelope()
                                #x_min, x_max, y_min, y_max = transformToSMAP(subbasin_feature_geom, projected_basin_layer).GetEnvelope()
                                # if False==19:
                                #     print 'Extent (envelope) of feature (subbasin): ', x_min, x_max, y_min, y_max

                                # define 2D loop limits for basin within MODIS grid
                                i_low = max(0, int((x_min - lowerLeftX)/grid_cell_width) - 1)
                                i_high = min(precip_band_array.shape[1], int((x_max - lowerLeftX)/grid_cell_width) + 1)
                                j_high = max(0, int(( upperRightY - y_min)/grid_cell_height) + 1)
                                j_low = min(precip_band_array.shape[0], int((upperRightY - y_max)/grid_cell_height) - 1)
                                num_columns = i_high - i_low+1
                                num_rows = j_high - j_low+1

                                # set up cell counting
                                num_cells = 0
                                num_cells_missing = 0
                                num_cells_0 = 0
                                num_cells_1 = 0
                                num_cells_partial = 0
                                # if False==19:
                                #     print 'Raster array bounds: ', i_low, i_high, j_low, j_high, ' (', num_columns, 'x', num_rows,')', subbasin_id

                                # loop over columns in raster array (West to East)
                                for i in range(i_low, i_high):
                                    # predetermine rows overlapping with subbasin to speed up processing of column
                                    col_rect = ogr.Geometry(ogr.wkbLinearRing)
                                    #col_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j_low*grid_cell_height)
                                    #col_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+j_low*grid_cell_height)
                                    #col_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+(j_high+1)*grid_cell_height)
                                    #col_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+(j_high+1)*grid_cell_height)
                                    #col_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j_low*grid_cell_height)
                                    col_rect.AddPoint(lowerLeftX+i*grid_cell_width, upperRightY-j_low*grid_cell_height)
                                    col_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, upperRightY-j_low*grid_cell_height)
                                    col_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, upperRightY-(j_high+1)*grid_cell_height)
                                    col_rect.AddPoint(lowerLeftX+i*grid_cell_width, upperRightY-(j_high+1)*grid_cell_height)
                                    col_rect.AddPoint(lowerLeftX+i*grid_cell_width, upperRightY-j_low*grid_cell_height)
                                    col_geom = ogr.Geometry(ogr.wkbPolygon)
                                    col_geom.AddGeometry(col_rect)
                                    col_intersection_geom = col_geom.Intersection(subbasin_feature_geom)
                                    if col_intersection_geom != None:
                                        col_x_min, col_x_max, col_y_min, col_y_max = col_intersection_geom.GetEnvelope()
                                        if col_intersection_geom.Area() == 0.0:
                                            continue
                                        new_j_high = max(0, int((upperRightY-col_y_min)/grid_cell_height) + 1)
                                        new_j_low = min(precip_band_array.shape[0], int((upperRightY-col_y_max)/grid_cell_height) - 1)
                                    else:
                                        if print_details:
                                            print('Column intersection ill-defined, switch to using all rows and whole subbasin for this column')
                                        col_intersection_geom = subbasin_feature_geom
                                        new_j_low = j_low
                                        new_j_high = j_high
                                    # if False==19:
                                    #     print 'new_j_low, new_j_high', new_j_low, new_j_high

                                    # loop over cells/rows in column within intersection (upward - South to North)
                                    for j in range(new_j_low, new_j_high):
                                        num_cells = num_cells + 1
                                        num_cells_total = num_cells_total + 1

                                        # check for cell limt
                                        if (max_cells > 0 and num_cells_total  > max_cells):
                                            raise ExceededMaxCells

                                        # check for missing values
                                        cell_precip_value = precip_band_array[j][i]

                                        if (cell_precip_value == -9999.0):
                                            num_cells_missing = num_cells_missing + 1
                                            continue

                                        cell_rect = ogr.Geometry(ogr.wkbLinearRing)
                                        #cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j*grid_cell_height)
                                        #cell_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+j*grid_cell_height)
                                        #cell_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+(j+1)*grid_cell_height)
                                        #cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+(j+1)*grid_cell_height)
                                        #cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j*grid_cell_height)
                                        cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, upperRightY-j*grid_cell_height)
                                        cell_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, upperRightY-j*grid_cell_height)
                                        cell_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, upperRightY-(j+1)*grid_cell_height)
                                        cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, upperRightY-(j+1)*grid_cell_height)
                                        cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, upperRightY-j*grid_cell_height)
                                        cell_geom = ogr.Geometry(ogr.wkbPolygon)
                                        cell_geom.AddGeometry(cell_rect)
        #                                print 'Geom of cell [', i, ',' , j, ']: ', cell_geom.ExportToWkt()
                                        if (cell_geom.Disjoint(col_intersection_geom)):
                                            num_cells_0 = num_cells_0 + 1
                                            cell_intersection_area = 0.0
                                        elif (cell_geom.Within(col_intersection_geom)):
                                            num_cells_1 = num_cells_1 + 1
                                            cell_intersection_area = grid_cell_area
                                        else:
                                            num_cells_partial = num_cells_partial + 1
                                            cell_intersection_geom = cell_geom.Intersection(col_intersection_geom)
        #                                   print 'Geom of intersection = ', cell_intersection_geom.ExportToWkt()
                                            if (cell_intersection_geom != None):
                                                cell_intersection_area = cell_intersection_geom.Area()
                                            else:
                                                cell_intersection_area = 0.0
                                        if False==19:
                                            print('Cell [', i, ',', j, ']: precip = ', cell_precip_value, ', Intersection = ', cell_intersection_area/grid_cell_area, ', (at: ', lowerLeftX+i*grid_cell_width, ', ', upperRightY-j*grid_cell_height, ')')
                                        if (cell_intersection_area <= 0.0):
                                            continue

                                        subbasin_precip_weighted_value_sum = subbasin_precip_weighted_value_sum + cell_precip_value*cell_intersection_area/grid_cell_area
                                        subbasin_weight_sum = subbasin_weight_sum + cell_intersection_area/grid_cell_area
                                # end loops over 2D grid

                                # subbasin statistics
                                if (subbasin_weight_sum > 0.0):
                                    subbasin_precip_weighted_avg = subbasin_precip_weighted_value_sum/subbasin_weight_sum
                                else:
                                    subbasin_precip_weighted_avg = 0.0
                                subbasin_feature.SetField('PRECIP', subbasin_precip_weighted_avg)
                                projected_basin_layer.SetFeature(subbasin_feature)
                                projected_basin_data_source.SyncToDisk()
                                if print_details:
                                    print('  precipitation = ', subbasin_precip_weighted_avg)
                                else:
                                    if cnt % 5000 == 4999:
                                        print(" processed " + str(cnt+1) + " features")
                                cnt += 1
                                subbasin_proc_time = time.time() - subbasin_feature_start_time
        #                        print 'Cells processed for this feature (subbasin): ', num_cells, ' = ', num_cells_0, ' (0) +', num_cells_1, ' (1) +', num_cells_missing, ' (missing) +', num_cells_partial, ' (partial)'
        #                        print 'Elapsed time for this feature (subbasin) = ', subbasin_proc_time
        #                        print 'Avg time per cell for this feature (subbasin) = ', subbasin_proc_time/num_cells
                                # append to CSV file
                                csv_str = basin_shapefile_name + "," + ", ".join(map(str, [subbasin_id, subbasin_area, capture_date, capture_stime, capture_etime, subbasin_precip_weighted_avg, num_cells, num_cells_1, num_cells_partial, num_cells_0, num_cells_missing, subbasin_proc_time]))
                                csv_out.write(csv_str + '\n')
                                logging.info(csv_str)


                                # running statistics
        #                        total_proc_time = time.time() - start_time
        #                        print 'Total cells processed so far = ', num_cells_total
        #                        print 'Total elapsed time so far = ', total_proc_time
        #                        print 'Avg time per cell overall = ', total_proc_time/num_cells_total
                            # end loop over features (subbasins)

                        except ExceededMaxCells:
                            print('Exceeded Max Cells [',max_cells, '] - exiting')
                            pass

                        # end of layer (basin) processing

                        projected_basin_layer = None
                        projected_basin_data_source.SyncToDisk()
                        projected_basin_data_source = None

                        grid_proc_time = time.time() - grid_start_time
                        print()
                        print('End projection of ', hdf_name, ' onto ', basin_shapefile_name)
                        print('Elapsed time for projection = ', grid_proc_time)
                        logging.info("Elapsed time to project " + hdf_name + " onto " + basin_shapefile_name+" = " + str(grid_proc_time))
                    else:
                        print('')
                        print('*** No overlap with ', hdf_name)
                # end current MODIS HDF processing

                except AttributeError as e:
                    print(repr(e))
                    continue
            # end loop over MODIS HDF files
            # remove temp files
            folder = folder_output
            for the_file in os.listdir(folder):
                if the_file.startswith(firstHDFName) == False and the_file.split(".")[-1] not in ["csv", "log"]:
                    file_path = os.path.join(folder, the_file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        #elif os.path.isdir(file_path): shutil.rmtree(file_path)
                    except Exception as e:
                        print(e)

        csv_out.close()


        total_proc_time = time.time() - start_time
        print()
        print('Total elapsed time: = ', total_proc_time)
        logging.info("Total elapsed time = " + str(total_proc_time))
        print()
        print('*** Done ***')

        return [csv_file_name], outputPeriod

if __name__=='__main__':
    ts = timeSeriesGPM()
    print(ts.run())
