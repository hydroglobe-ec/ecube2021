from osgeo import gdal, ogr, osr
import  os, sys, glob
import datetime, time
import math
import collections
import logging
import re
from shapely.geometry import box, shape
import numpy as np
import sqlite3
import csv
from HGUtil import HGUtil

_print = print
def print(*args, **kw):
    HGUtil.JOBLOG_FUNC(*args, **kw)
    # _print(*args, **kw)

def remove_allfiles(folderroot):
    filelist=glob.glob(folderroot+'/*.*')
    #return filelist
    for f in filelist:
        os.remove(f)

def transform_shapes_ogr(infile,outfile,out_prj):
    (outfilepath, outfilename) = os.path.split(outfile)
    (outfileshortname, extension) = os.path.splitext(outfilename)
    driver = ogr.GetDriverByName('ESRI Shapefile')
    indataset = driver.Open(infile, 0)
    if indataset is None:
        print('Could not open file')
        sys.exit(1)
    inlayer = indataset.GetLayer()
    inSpatialRef = inlayer.GetSpatialRef()
    outSpatialRef = osr.SpatialReference()
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
    feature = inlayer.GetFeature(0)
    fieldDefn1 = feature.GetFieldDefnRef('Subbasin')
    outlayer.CreateField(fieldDefn1)
    outlayer.CreateField(ogr.FieldDefn('FPAR', ogr.OFTReal))
    outlayer.CreateField(ogr.FieldDefn('LAI', ogr.OFTReal))
    featureDefn = outlayer.GetLayerDefn()
    infeature = inlayer.GetNextFeature()
    while infeature:
        #get the input geometry
        geometry = infeature.GetGeometryRef()
        #reproject the geometry, each one has to be projected seperately
        geometry.Transform(coordTransform)
        #create a new output feature
        outfeature = ogr.Feature(featureDefn)
        #set the geometry and attribute
        outfeature.SetGeometry(geometry)
        outfeature.SetField('Subbasin', infeature.GetField('Subbasin'))
        #add the feature to the output shapefile
        outlayer.CreateFeature(outfeature)
        #destroy the features and get the next input features
        outfeature.Destroy
        infeature.Destroy
        infeature = inlayer.GetNextFeature()
    #close the shapefiles
    indataset.Destroy()
    outdataset.Destroy()
    #create the prj projection file
    outSpatialRef.MorphToESRI()
    file = open(outfilepath + '/'+ outfileshortname + '.prj', 'w')
    file.write(outSpatialRef.ExportToWkt())
    file.close()

def get_name(path):
    return os.path.basename(os.path.splitext(path)[0])

def extent_shp(shp):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.Open(shp, 0)
    layer = data_source.GetLayer()
    extent = layer.GetExtent()
    return extent[0],extent[2],extent[1],extent[3]

def extent_hdf(hdf):
    hdf_data = gdal.Open(hdf, gdal.GA_ReadOnly)
    metadata = hdf_data.GetMetadata()
    global_rows = int(metadata['GLOBALGRIDROWS500M']) # 18*2400
    global_columns = int(metadata['GLOBALGRIDCOLUMNS500M']) #36*2400
    earth_radius = 6371007.181 # TODO: Where can this be extracted?  [semi_major/minor in prj/6974.prj]
    earth_half_width = earth_radius*math.pi
    earth_half_height = earth_half_width/2 # Assuming a sphere
    row_size = int(metadata['DATACOLUMNS500M']) # 2400
    column_size = int(metadata['DATAROWS500M']) # 2400
    horizontal_tiles = global_columns / column_size # 36
    vertical_tiles = global_rows / row_size # 18
    tile_width = earth_half_width / (horizontal_tiles/2)
    tile_height = earth_half_height / (vertical_tiles/2)
    cell_width = tile_width / row_size
    cell_height = tile_height / column_size
    h_tile_number = int(metadata['HORIZONTALTILENUMBER'])
    v_tile_number = int(metadata['VERTICALTILENUMBER'])
    lowerLeftX = -earth_half_width + h_tile_number * tile_width
    lowerLeftY = -earth_half_height + (vertical_tiles  - v_tile_number - 1) * tile_height
    upperRightX = lowerLeftX + tile_width
    upperRightY = lowerLeftY + tile_height
    return lowerLeftX, lowerLeftY, upperRightX, upperRightY

def IsOverlap(shp,hdf):
    ext_shp= extent_shp(shp)
#    print 'Extent of ', get_name(shp), ': ', ext_shp
    box_shp= box(*ext_shp)
    ext_hdf =extent_hdf(hdf)
#    print 'Extent of ', get_name(hdf), ': ', ext_hdf
    box_hdf= box(*ext_hdf)
    return box_shp.intersects(box_hdf)

def time_info(modis_hdf_name):
    strpat='MCD\w+\.\w(\d{4})(\d{3})\.(\w+)\..+\.hdf'  #'MOD\w+\.\w(\d{4})(\d{3}).+\.(\d+)\.hdf'
    pattern=re.compile(strpat, re.MULTILINE)
    match=pattern.match(modis_hdf_name)
    if match:
        return match.group(1),match.group(2),match.group(3)

#---------------------------------------------------------------------------------------------------------------------------------
#if __name__=='__main__':
if True:

    #TODO:  use INI file and ConfigParser to define constants, like ROOT, folder names, file names, output/print options, MAX_CELLS,...
    # Change to your project root directory
#    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#    root = r"C:\Users\jsmith\OneDrive\Documents\XSEDE\WaterHUB\HydroGlobe-TimeSeries" # HEPC Office PC
    root = r"C:\Users\Smith\OneDrive\Documents\XSEDE\WaterHUB\HydroGlobe-TimeSeries" # Windows 10 laptop
#    root = "/Users/jacksmith/Desktop/OneDrive/Documents/XSEDE/WaterHUB/HydroGlobe-TimeSeries" # MacBook

    using_db = False
    saving_subbasin_csv_files = False
    max_cells = 0  # set to 0 (or less) to disable, -1 to suppress printing details
    if (max_cells < 0):
        print_details = False
    else:
        print_details = True

    # set up folders
    folder_shape = root + "/shape"
    folder_temp = root + "/temp"
    folder_output = root + "/output"
    folder_hdf = root + "/hdf4day-lai"
    folder_prj =root + "/prj"

    # clean up temp files
    try:
        remove_allfiles(folder_temp)
    except WindowsError:
        print('*** Trouble removing temp files ***')

    # set up logging
    logfile = folder_output + "/logfile.log"
    with open(logfile, 'w'):  # clear log file first
        pass
    logging.basicConfig(filename=logfile, level=logging.INFO)

    # get MODIS and basin shapefile file names
    list_of_hdfs = glob.glob(folder_hdf + "/*.hdf") #
    basin_shapefile = glob.glob(folder_shape + "/*.shp")[0]
    basin_shapefile_name = get_name(basin_shapefile)

    if using_db:
        # create/open SQLite DB to capture results
        #TODO:  make basin name unique (not the default 'subs1') - from extent or other metadata
        #            Make DB filename generic, not based on name of basin shapefile
        #            Check for entries in DB before performing  projection
        db_file_name = folder_output + "/" + basin_shapefile_name + "_lai_projection_results" + ".db"
    #    db_file_name = ":memory:"
        db_conn = sqlite3.connect(db_file_name)
        db_cursor = db_conn.cursor()
        db_cursor.execute('''CREATE TABLE IF NOT EXISTS basins
            (name text PRIMARY KEY, lat real, lon real, height real, width real, area real)''')
        db_cursor.execute('''CREATE TABLE IF NOT EXISTS subbasins
            (basin_name text, name text, lat real, lon real, height real, width real, area real,
            PRIMARY KEY (basin_name, name), FOREIGN KEY (basin_name) REFERENCES basins(name))''')
        #TODO:  extract year, day, H, V, etc., from dataset name into fields
        db_cursor.execute('''CREATE TABLE IF NOT EXISTS modis_datasets
            (name text PRIMARY KEY, metadata text)''')
        db_cursor.execute('''CREATE TABLE IF NOT EXISTS modis_subdatasets
            (dataset_name text, band text, description text,
            PRIMARY KEY (dataset_name, band), FOREIGN KEY (dataset_name) REFERENCES modis_datasets(name))''')
        db_cursor.execute('''CREATE TABLE IF NOT EXISTS subbasin_projections
            (modis_dataset_name text, basin_name text, subbasin_name text, year integer, day integer,
            FPAR real, LAI real,
            cells_total integer, cells_1 integer, cells_partial integer, cells_0 integer, cells_missing integer, process_time real,
            PRIMARY KEY (basin_name, subbasin_name, year, day),
            FOREIGN KEY (modis_dataset_name) REFERENCES modis_datasets(name),
            FOREIGN KEY (basin_name) REFERENCES basins(name),
            FOREIGN KEY (basin_name, subbasin_name) REFERENCES subbasins(basin_name, name))''')

    # create CSV file for all results;  subbasin summary CSV files will be created from DB
    csv_file_name = folder_output + "/" + basin_shapefile_name + "_lai_projection_results" + ".csv"
    csv_out = open(csv_file_name,'w')
    csv_out.truncate()
    csv_out.write('basin, subbasin, area, year, day, FPAR, LAI, cells_total, cells_1, cells_partial, cells_0, cells_missing, process_time\n')

    # get basin layer from shapefile
    esri_shapefile_driver = ogr.GetDriverByName("ESRI Shapefile")
    basin_data_source = esri_shapefile_driver.Open(basin_shapefile, 1)
    basin_layer = basin_data_source.GetLayer()

    if using_db:
        # add basin to DB
        #TODO: add lat, lon, height, width, area to basin entry
        db_str = "'" + basin_shapefile_name + "', 0.0, 0.0, 0.0, 0.0, 0.0"
        db_cursor.execute("INSERT OR REPLACE INTO basins VALUES ("+db_str+")")
        db_conn.commit()

    # get subbasin list
    print('Get feature (subbasin) list and add to DB')
    subbasins = []
    for subbasin_feature in basin_layer:  # loop over subbasins
        subbasin_id = subbasin_feature.GetField('Subbasin')
        subbasins.append(subbasin_id)
        if using_db:
            # add subbasin to DB
            #TODO: add lat, lon, height, width, area to subbasin entry
            db_str = "'" + str(subbasin_id) +"', '" + basin_shapefile_name + "', 0.0, 0.0, 0.0, 0.0, 0.0"
            db_cursor.execute("INSERT OR REPLACE INTO subbasins VALUES ("+db_str+")")
            db_conn.commit()

    num_subbasins = len(subbasins)
    print('Features (subbasins) found: ',num_subbasins)
    if (num_subbasins > 100):
        print_details = False

    # set up timing
    start_time = time.time()
    last_time = start_time
    current_time = datetime.datetime.now().strftime('%H%M%S')
    print('Begin processing of basin shapefile: ', basin_shapefile_name)

    # set up cell counting
    num_cells_total = 0

    class ExceededMaxCells(Exception):
        pass

    # start loop over MODIS HDF files
    for hdf in list_of_hdfs:
        try: # catch attribute exceptions
            modis_hdf_name = get_name(hdf)
            capture_year, capture_day, capture_ver = time_info(os.path.basename(hdf))
            capture_id = "{0}{1}{2}".format(capture_year[-1],capture_day,capture_ver)


            # transform shape file to ESPG 6974
            #TODO: can the projection # be extracted from the HDF file?
            projection_file = folder_prj + "/6974.prj"
            projected_basin_shapefile = folder_output + "/" + basin_shapefile_name + "_" + capture_year + "_" + capture_day + "_" + current_time + "_projected" + ".shp"
            transform_shapes_ogr(basin_shapefile, projected_basin_shapefile, projection_file)

            # test wether MODIS HDF region overlaps basin of interest
            if IsOverlap(projected_basin_shapefile, hdf):

                # begin processing grid from MODIS HDF raster file

                grid_start_time = time.time()
                print()
                print('***')
                print()
                print('Begin projection of ', modis_hdf_name, ' onto ', basin_shapefile_name)
                logging.info("Begin projection of " + modis_hdf_name + " onto " + basin_shapefile_name)
                print()

                # extract dataset (array of subdatasets)
                modis_hdf_dataset = gdal.Open(hdf, gdal.GA_ReadOnly)
                modis_hdf_metadata = modis_hdf_dataset.GetMetadata()
#                print(modis_hdf_metadata)

                if using_db:
                    # add MODIS HDF dataset to DB
                    db_str = "'" + modis_hdf_name + "', '" + "[metadata]" + "'"
                    db_cursor.execute("INSERT OR REPLACE INTO modis_datasets VALUES ("+db_str+")")
                    db_conn.commit()

                # extract subdataset 0, FPAR band
                FPAR_band_subdataset = gdal.Open(modis_hdf_dataset.GetSubDatasets()[0][0], gdal.GA_ReadOnly) # extract FPAR band [0]
                FPAR_band_description = modis_hdf_dataset.GetSubDatasets()[0][1]
                print('MODIS HDF subdataset [FPAR] description: ', FPAR_band_description)
                FPAR_band_metadata = FPAR_band_subdataset.GetMetadata()
                FPAR_band_array = FPAR_band_subdataset.ReadAsArray().astype(np.int16)
                FPAR_band_array[FPAR_band_array == 0] = 255 # suppress water areas
                FPAR_band_array[FPAR_band_array >= 249] = 255 # found missing or assigned values in range: 249-255
                FPAR_out_tif_name = folder_temp+"/"+basin_shapefile_name+"_FPAR_"+capture_id+".tif"
#                print 'FPAR TIF file name: ', FPAR_out_tif_name
                FPAR_out_tif = gdal.GetDriverByName('GTiff').Create(FPAR_out_tif_name, FPAR_band_subdataset.RasterXSize,
                    FPAR_band_subdataset.RasterYSize, 1,  gdal.GDT_Int16, ['COMPRESS=LZW', 'TILED=YES'])
                FPAR_out_tif.SetGeoTransform(FPAR_band_subdataset.GetGeoTransform())
                FPAR_out_tif.SetProjection(FPAR_band_subdataset.GetProjection())
                FPAR_out_tif.GetRasterBand(1).WriteArray(FPAR_band_array)
                FPAR_out_tif.GetRasterBand(1).SetNoDataValue(255)
                FPAR_out_tif = None

                if using_db:
                    # add MODIS HDF subdataset (FPAR band) to DB
                    db_str = "'" + modis_hdf_name + "', 'FPAR', '" + str(FPAR_band_description) + "'"
                    db_cursor.execute("INSERT OR REPLACE INTO modis_subdatasets VALUES ("+db_str+")")
                    db_conn.commit()

                # extract subdataset 1, LAI band
                LAI_band_subdataset = gdal.Open(modis_hdf_dataset.GetSubDatasets()[1][0], gdal.GA_ReadOnly) # extract LAI band [1]
                LAI_band_description = modis_hdf_dataset.GetSubDatasets()[1][1]
                print('MODIS HDF subdataset [LAI] description: ', LAI_band_description)
                LAI_band_metadata = LAI_band_subdataset.GetMetadata()
                LAI_band_array = LAI_band_subdataset.ReadAsArray().astype(np.int16)
                LAI_band_array[LAI_band_array == 0] = 255
                LAI_band_array[LAI_band_array >= 249] = 255 # found missing or assigned values in range: 249-255
                LAI_out_tif_name = folder_temp+"/"+basin_shapefile_name+"_LAI_"+capture_id+".tif"
#                print 'LAI TIF file name: ', LAI_out_tif_name
                LAI_out_tif = gdal.GetDriverByName('GTiff').Create(LAI_out_tif_name, LAI_band_subdataset.RasterXSize,
                    LAI_band_subdataset.RasterYSize, 1,  gdal.GDT_Int16, ['COMPRESS=LZW', 'TILED=YES'])
                LAI_out_tif.SetGeoTransform(LAI_band_subdataset.GetGeoTransform())
                LAI_out_tif.SetProjection(LAI_band_subdataset.GetProjection())
                LAI_out_tif.GetRasterBand(1).WriteArray(LAI_band_array)
                LAI_out_tif.GetRasterBand(1).SetNoDataValue(255)
                LAI_out_tif = None

                if using_db:
                    # add MODIS HDF subdataset (LAI band) to DB
                    db_str = "'" + modis_hdf_name + "', 'LAI', '"+ str(LAI_band_description) + "'"
                    db_cursor.execute("INSERT OR REPLACE INTO modis_subdatasets VALUES ("+db_str+")")
                    db_conn.commit()

                print()

                # define MODIS grid cell at origin (lower left corner)
                lowerLeftX, lowerLeftY, upperRightX, upperRightY = extent_hdf(hdf)
                grid_cell_width = (upperRightX-lowerLeftX)/FPAR_band_array.shape[1]
                grid_cell_height = (upperRightY-lowerLeftY)/FPAR_band_array.shape[0]
                grid_cell_rect = ogr.Geometry(ogr.wkbLinearRing)
                grid_cell_rect.AddPoint(lowerLeftX, lowerLeftY)
                grid_cell_rect.AddPoint(lowerLeftX+grid_cell_width, lowerLeftY)
                grid_cell_rect.AddPoint(lowerLeftX+grid_cell_width, lowerLeftY+grid_cell_height)
                grid_cell_rect.AddPoint(lowerLeftX, lowerLeftY+grid_cell_height)
                grid_cell_rect.AddPoint(lowerLeftX, lowerLeftY)
                grid_cell_geom = ogr.Geometry(ogr.wkbPolygon)
                grid_cell_geom.AddGeometry(grid_cell_rect)
                grid_cell_area = grid_cell_geom.Area()
#                print 'Grid cell area = ', grid_cell_area, '[',grid_cell_width,' x ', grid_cell_height, ']'

                # get layer (basin) and its extent from re-projected shapefile
                esri_shapefile_driver = ogr.GetDriverByName("ESRI Shapefile")
                projected_basin_data_source = esri_shapefile_driver.Open(projected_basin_shapefile, 1)
                projected_basin_layer = projected_basin_data_source.GetLayer()
                x_min, x_max, y_min, y_max = projected_basin_layer.GetExtent()
#                print 'Extent of layer (basin): ', x_min, x_max, y_min, y_max

                if using_db:
                    #TODO:  Need to include capture_year and capture_day in search
                    db_cursor.execute("SELECT * from subbasin_projections WHERE basin_name='"+basin_shapefile_name+"' AND modis_dataset_name='"+modis_hdf_name+"'")
                    already_exists = db_cursor.fetchone()
                    if already_exists:
                        print("Results for ", basin_shapefile_name, " and ", modis_hdf_name, " already in database")
#                       continue;

                # main loop over features (subbasins), and grid cells (raster array) to accumulate weighted values for intersections

                try: # use try-except to limit grid cells to be processed (primarily for testing)
                    for subbasin_feature in projected_basin_layer:  # loop over subbasins
                        subbasin_feature_start_time = time.time()
                        subbasin_feature_geom = subbasin_feature.GetGeometryRef()
                        subbasin_id = subbasin_feature.GetField('Subbasin')
                        subbasin_area = subbasin_feature_geom.Area()
                        if print_details:
                            print('=== Subbasin ', subbasin_id)
#                        print 'Area of feature (subbasin) = ', subbasin_area
                        subbasin_FPAR_weighted_value_sum = 0.0
                        subbasin_LAI_weighted_value_sum = 0.0
                        subbasin_weight_sum = 0.0
#                        print 'Geom of feature (subbasin): ', subbasin_feature_geom.ExportToWkt()
                        x_min, x_max, y_min, y_max = subbasin_feature_geom.GetEnvelope()
#                        print 'Extent (envelope) of feature (subbasin): ', x_min, x_max, y_min, y_max

                        # define 2D loop limits for basin within MODIS grid
                        i_low = max(0, int((x_min - lowerLeftX)/grid_cell_width) - 1)
                        i_high = min(FPAR_band_array.shape[1], int((x_max - lowerLeftX)/grid_cell_width) + 1)
                        j_low = max(0, int((y_min - lowerLeftY)/grid_cell_height) - 1)
                        j_high = min(FPAR_band_array.shape[0], int((y_max - lowerLeftY)/grid_cell_height) + 1)
                        num_columns = i_high - i_low+1
                        num_rows = j_high - j_low+1

                        # set up cell counting
                        num_cells = 0
                        num_cells_missing = 0
                        num_cells_0 = 0
                        num_cells_1 = 0
                        num_cells_partial = 0
#                        print 'Raster array bounds: ', i_low, i_high, j_low, j_high, ' (', num_columns, 'x', num_rows,')'

                        # loop over columns in raster array (West to East)
                        for i in range(i_low, i_high):
                            # predetermine rows overlapping with subbasin to speed up processing of column
                            col_rect = ogr.Geometry(ogr.wkbLinearRing)
                            col_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j_low*grid_cell_height)
                            col_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+j_low*grid_cell_height)
                            col_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+(j_high+1)*grid_cell_height)
                            col_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+(j_high+1)*grid_cell_height)
                            col_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j_low*grid_cell_height)
                            col_geom = ogr.Geometry(ogr.wkbPolygon)
                            col_geom.AddGeometry(col_rect)
                            col_intersection_geom = col_geom.Intersection(subbasin_feature_geom)
                            if col_intersection_geom != None:
                                col_x_min, col_x_max, col_y_min, col_y_max = col_intersection_geom.GetEnvelope()
                                new_j_low = max(0, int((col_y_min - lowerLeftY)/grid_cell_height) - 1)
                                new_j_high = min(FPAR_band_array.shape[0], int((col_y_max - lowerLeftY)/grid_cell_height) + 1)
                            else:
                                print('Column intersection ill-defined, switch to using all rows and whole subbasin for this column')
                                col_intersection_geom = subbasin_feature_geom
                                new_j_low = j_low
                                new_j_high = j_high
                            # loop over cells/rows in column within intersection (upward - South to North)
                            for j in range(new_j_low, new_j_high):
                                num_cells = num_cells + 1
                                num_cells_total = num_cells_total + 1

                                # check for cell limt
                                if (max_cells > 0 and num_cells_total  > max_cells):
                                    raise ExceededMaxCells

                                # check for missing values
                                cell_FPAR_value = FPAR_band_array[i][j]
                                cell_LAI_value = LAI_band_array[i][j]
                                if (cell_FPAR_value >= 249 or cell_LAI_value >= 249):
                                    num_cells_missing = num_cells_missing + 1
                                    continue
                                elif (cell_FPAR_value < -249 or cell_LAI_value <= -249):
                                    num_cells_missing = num_cells_missing + 1
                                    continue

                                cell_rect = ogr.Geometry(ogr.wkbLinearRing)
                                cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j*grid_cell_height)
                                cell_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+j*grid_cell_height)
                                cell_rect.AddPoint(lowerLeftX+(i+1)*grid_cell_width, lowerLeftY+(j+1)*grid_cell_height)
                                cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+(j+1)*grid_cell_height)
                                cell_rect.AddPoint(lowerLeftX+i*grid_cell_width, lowerLeftY+j*grid_cell_height)
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
#                                print 'Cell [', i, ',', j, ']: FPAR = ', cell_FPAR_value, ', LAI = ', cell_LAI_value, ', Intersection = ', cell_intersection_area/grid_cell_area, ', (at: ', lowerLeftX+i*grid_cell_width, ', ', lowerLeftY+j*grid_cell_height, ')'
                                if (cell_intersection_area <= 0.0):
                                    continue

                                subbasin_FPAR_weighted_value_sum = subbasin_FPAR_weighted_value_sum + cell_FPAR_value*cell_intersection_area/grid_cell_area
                                subbasin_LAI_weighted_value_sum = subbasin_LAI_weighted_value_sum + cell_LAI_value*cell_intersection_area/grid_cell_area
                                subbasin_weight_sum = subbasin_weight_sum + cell_intersection_area/grid_cell_area
                        # end loops over 2D grid

                        # subbasin statistics
                        if (subbasin_weight_sum > 0.0):
                            subbasin_FPAR_weighted_avg = subbasin_FPAR_weighted_value_sum/subbasin_weight_sum
                            subbasin_LAI_weighted_avg = subbasin_LAI_weighted_value_sum/subbasin_weight_sum
                        else:
                            subbasin_FPAR_weighted_avg = 0.0
                            subbasin_LAI_weighted_avg = 0.0
                        subbasin_feature.SetField('FPAR', subbasin_FPAR_weighted_avg)
                        subbasin_feature.SetField('LAI', subbasin_LAI_weighted_avg)
                        projected_basin_layer.SetFeature(subbasin_feature)
                        projected_basin_data_source.SyncToDisk()
                        if print_details:
                            print('  FPAR = ', subbasin_FPAR_weighted_avg)
                            print('  LAI = ', subbasin_LAI_weighted_avg)
                        subbasin_proc_time = time.time() - subbasin_feature_start_time
#                        print 'Cells processed for this feature (subbasin): ', num_cells, ' = ', num_cells_0, ' (0) +', num_cells_1, ' (1) +', num_cells_missing, ' (missing) +', num_cells_partial, ' (partial)'
#                        print 'Elapsed time for this feature (subbasin) = ', subbasin_proc_time
#                        print 'Avg time per cell for this feature (subbasin) = ', subbasin_proc_time/num_cells
                        # append to CSV file
                        csv_str = basin_shapefile_name + "," + ", ".join(map(str, [subbasin_id, subbasin_area, capture_year, capture_day, subbasin_FPAR_weighted_avg, subbasin_LAI_weighted_avg, num_cells, num_cells_1, num_cells_partial, num_cells_0, num_cells_missing, subbasin_proc_time]))
                        csv_out.write(csv_str + '\n')
                        logging.info(csv_str)

                        if using_db:
                            # update DB
                            db_str = "'" + modis_hdf_name +"', '" + basin_shapefile_name +"', " + ", ".join(map(str, [subbasin_id, capture_year, capture_day, subbasin_FPAR_weighted_avg, subbasin_LAI_weighted_avg, num_cells, num_cells_1, num_cells_partial, num_cells_0, num_cells_missing, subbasin_proc_time]))
                            db_cursor.execute("INSERT OR REPLACE INTO subbasin_projections VALUES ("+db_str+")")
                            db_conn.commit()

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
                print('End projection of ', modis_hdf_name, ' onto ', basin_shapefile_name)
                print('Elapsed time for projection = ', grid_proc_time)
                logging.info("Elapsed time to project " + modis_hdf_name + " onto " + basin_shapefile_name+" = " + str(grid_proc_time))
            else:
                print()
                print('*** No overlap with ', modis_hdf_name)
        # end current MODIS HDF processing

        except AttributeError as e:
            print(repr(e))
            continue
    # end loop over MODIS HDF files

    csv_out.close()

    # generate subbasin timeseries CSV files
    if using_db and saving_subbasin_csv_files:
        for subbasin_id in subbasins:
            subbasin_name = str(subbasin_id)
            db_cursor.execute("SELECT year, day, FPAR, LAI FROM subbasin_projections WHERE subbasin_name ='"+subbasin_name+"'")
            #TODO: add 'AND basin_name ='
            subbasin_csv_file_name = folder_output + "/" + basin_shapefile_name + "_" + subbasin_name + ".csv"
            with open(subbasin_csv_file_name, 'wb') as subbasin_csv_file:
                subbasin_csv_out = csv.writer(subbasin_csv_file)
                subbasin_csv_out.writerow([col_desc[0] for col_desc in db_cursor.description])
                for result in db_cursor:
                    subbasin_csv_out.writerow(result)

    if using_db:
        db_conn.close()
    total_proc_time = time.time() - start_time
    print()
    print('Total elapsed time: = ', total_proc_time)
    logging.info("Total elapsed time = " + str(total_proc_time))
    print()
    print('*** Done ***')
