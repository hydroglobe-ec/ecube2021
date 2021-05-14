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
    outlayer.CreateField(ogr.FieldDefn('ET', ogr.OFTReal))
    outlayer.CreateField(ogr.FieldDefn('LE', ogr.OFTReal))
    outlayer.CreateField(ogr.FieldDefn('PET', ogr.OFTReal))
    outlayer.CreateField(ogr.FieldDefn('PLE', ogr.OFTReal))
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
    global_rows = int(metadata['GLOBALGRIDROWS']) # 18*1200
    global_columns = int(metadata['GLOBALGRIDCOLUMNS']) #36*1200
    earth_radius = 6371007.181 # TODO: Where can this be extracted?  [semi_major/minor in prj/6974.prj]
    earth_half_width = earth_radius*math.pi
    earth_half_height = earth_half_width/2 # Assuming a sphere
    row_size = int(metadata['DATACOLUMNS']) # 1200
    column_size = int(metadata['DATAROWS']) # 1200
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
    strpat='MOD\w+\.\w(\d{4})(\d{3})\.(\w+)\..+\.hdf'  #'MOD\w+\.\w(\d{4})(\d{3}).+\.(\d+)\.hdf'
    pattern=re.compile(strpat, re.MULTILINE)
    match=pattern.match(modis_hdf_name)
    if match:
        return match.group(1),match.group(2),match.group(3)
