#!/usr/bin/env python

import sys, os, glob
from datetime import datetime as dt
import traceback
import argparse
from zipfile import ZipFile
from HGUtil import HGUtil

# this line is for testing cluster, put all codes under the path below for the TEST...
# sys.path.insert(0, '/depot/ssg/gabbs/apps/hydroglobe/run/bin')

from DataFetch import Fetch
from modisProcess import timeSeries8day, timeSeries4day_lai
from smapProcess import timeSeriesSMAP
from gpmProcess import timeSeriesGPM

# comment below line and all related lines for the cluster TEST
from VisManager import VisManager

dataFetch = Fetch()
modisRun = timeSeries8day()
modisRunLAI = timeSeries4day_lai()
smapRun = timeSeriesSMAP()
gpmRun = timeSeriesGPM()

_print = print
def print(*args, **kw):
    HGUtil.JOBLOG_FUNC(*args, **kw)
    # _print(*args, **kw)

def run(repo, dateFrom, dateTo, shapeFileName, currentDir):

    dirs = ["temp", "output", "inputs", "results"]
    for d in dirs:
        if not os.path.exists(currentDir + "/" + d):
            os.mkdir(currentDir + "/" + d)

    # when error happens, delete some folders
    def delete_workdirs():
        for d in ['temp','inputs','results']:
            if os.path.exists(currentDir + "/" + d):
                os.system('rm -rf ' + currentDir + "/" + d)


    #####################################################
    # Fetch data from repository, dataFetch is from the DataFetch.py
    #####################################################
    try:
        if repo == "SMAP" or repo[:3] == "GPM":
            period = []
        else:
            period = dataFetch.getData(repo, dateFrom, dateTo, shapeFileName, currentDir)
    except:
        print (traceback.format_exc())
        print ("\n*** Error occured in data fetching (00) ***")
        delete_workdirs()
        return

    # print period

    #####################################################
    # Run a processing unit. modisRun and modisRunLAI is from modisProcess.py
    #####################################################
    csv_outs = []
    try:
        if repo == "MODIS-ET/PET/LE/PLE":
            csv_outs = [modisRun.run(currentDir = currentDir)]
        elif repo == "MODIS-LAI/FPAR":
            csv_outs = [modisRunLAI.run(currentDir = currentDir)]
        elif repo == "SMAP":
            csv_outs, period = smapRun.run(repo, dateFrom, dateTo, shapeFileName, currentDir = currentDir)
        elif repo[:3] == "GPM":
            csv_outs, period = gpmRun.run(repo, dateFrom, dateTo, shapeFileName, currentDir)
        else:
            raise RuntimeError('Unsupported data type')
    except RuntimeError:
        print (traceback.format_exc())
        print ("\n*** Error occured in data processing (01) ***")
        delete_workdirs()
        return
    except:
        print (traceback.format_exc())
        print ("\n*** Error occured in data processing (02) ***")
        delete_workdirs()
        return

    #####################################################
    # copy csv file and shape file to results directory
    #####################################################
    try:
        # set dir name
        ct = dt.now()
        time = ct.strftime('%Y%m%d_%H%M%S')

        fName = shapeFileName

        # dtTemp = repo.replace("/", ",")
        # dirName = fName[:-4] + "_" + dtTemp + "_" + time
        dirPath = currentDir + "/results"

        if not os.path.exists(dirPath):
            os.mkdir(dirPath)

        # copy csv file and shape file to results directory
        for csv_out in csv_outs:
            os.system('cp "%s" "%s"' %(csv_out, dirPath))

        for ext in ["dbf", "prj", "shp", "shx", "cpg", "sbn", "sbx", "xml"]:
            if len(glob.glob(currentDir + "/output/*." + ext)) > 0:
                path = sorted(glob.glob(currentDir + "/output/*." + ext))[0]
                os.system('cp "%s" "%s"' %(path, dirPath))

        # zip for two or more csv files..
        if repo == "SMAP":
            zipName = csv_outs[0].split("/")[-1][:-4]
            myzip = ZipFile(dirPath + '/' + zipName + '.zip', 'w')
            for csv_out in csv_outs:
                myzip.write(dirPath + "/" + csv_out.split("/")[-1],
                            os.path.basename(dirPath + "/" + csv_out.split("/")[-1]))
            myzip.close()

        # write info.dat in the directory
        with open(dirPath + "/info.dat", "w") as f:
            f.write("Processed time      |" + ct.strftime('%m/%d/%Y  %H:%M:%S') + "\n")
            f.write("Shapefile name      |" + fName[:-4] + "\n")
            f.write("Data type           |" + repo + "\n")
            f.write("Selected time-period|" + period[0] + " to " + period[-1] + "\n")

        # create visualization data files
        vis = VisManager()
        # TODO ILUK: please note that csv_outs is now array for file names !!!!!!!!!!
        # use csv_outs[0] for original csv output
        vis.create_vis_data(repo, glob.glob(currentDir + "/output/*.shp")[0], csv_outs[-1], dirPath)

    except:
        print (traceback.format_exc())
        delete_workdirs()

        print ("\n*** Selected data may not exist in target repository ***")
        print ("\n*** Error occured in data processing (03) ***")

        return

    # remove data
    # dirs = ["shape", "temp", "output", "inputs", "results"]
    dirs = ["temp", "output", "inputs",'shape']
    for item in dirs:
        os.system('rm -rf %s' %(currentDir + "/" + item + "/"))

    print(">> Job is done.")

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Set args for cluster run.')
    parser.add_argument('-r', '--repo', help='repo name in geohub app')
    parser.add_argument('-df', '--datefrom', help='datefrom (e.g. 01/01/2016)')
    parser.add_argument('-dt', '--dateto', help='dateto (e.g. 01/15/2016)')
    parser.add_argument('-f', '--file', help='shape file name (e.g. xxx.shp)')

    args = parser.parse_args()
    # python submitHydroglobe.py -r MODIS-LAI/FPAR -df 01/01/2016 -dt 01/06/2016 -f subs1_projected_171936.shp
    # print args.repo,
    # print args.datefrom,
    # print args.dateto,
    # print args.file
    # print(args.accumulate(args.integers))
    run(repo = args.repo, dateFrom = args.datefrom, dateTo = args.dateto, shapeFileName = args.file, currentDir=os.getcwd())
