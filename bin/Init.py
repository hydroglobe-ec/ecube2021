#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from __future__ import print_function
# from ipywidgets import *
import sys, os, io, glob, zipfile, subprocess, time
import ipywidgets as ipyw
from IPython.display import HTML, display, clear_output, Javascript
from datetime import datetime as dt
from dateutil import relativedelta
from DataFetch import Fetch
from modisProcess import timeSeries8day, timeSeries4day_lai
import traceback
import HGInterface, JobManager
from HGUtil import HGUtil, HGLOG
from DBManager import DBManager
from VisManager import VisManager
import pandas as pd
import geojson
import numpy as np
import csv
import warnings


class HGMain:
    supportedType = ['MODIS-ET/PET/LE/PLE', 'MODIS-LAI/FPAR', 'SMAP', 'GPM']
    WORKING_DIR = HGUtil.WORKING_DIR

    dataFetch = Fetch()
    modisRun = timeSeries8day()
    modisRunLAI = timeSeries4day_lai()
    hginterface = HGInterface.HGInterface()
    visManager = VisManager()


    sortBy = "date"
    uploaded_filename = None

    joblist_df = None

    initialized = False
    is_first_refresh = True




    def main(self):

        warnings.filterwarnings('ignore')

        #self.hginterface.show_init_loading()

        start_t = time.time()
        #return
        # HGUtil.getNBBaseUrl()

        # disable Jupyter autosave
        display(Javascript('Jupyter.notebook.set_autosave_interval(0);'))

        # create base folders
        HGUtil.mkdir(self.WORKING_DIR)
        HGUtil.mkdir(self.WORKING_DIR + "/upload") # for user-uploaded zip file
        HGUtil.mkdir(self.WORKING_DIR + "/job")    # for job submission and results

        # create link to working dir
        # HGUtil.createWorkLink()
        # create interfaces
        self.hginterface.init()
        self.hginterface.file_widget.cb = self.file_loaded

        self.hginterface.fetchDataButton.on_click(self.on_fetch_button_clicked)

        self.hginterface.visData.observe(self.showVisDataInformation, "value")
        self.hginterface.btn_vis_del.on_click(self.on_vis_del_button_clicked)
        self.hginterface.btn_vis_vis.on_click(self.on_vis_vis_button_clicked)
        self.updateVisData()

        self.hginterface.sortCheckBox.observe(self.toggleSort, "value")


        self.hginterface.btn_joblist_download.on_click(self.on_btn_joblist_download_clicked)
        self.hginterface.btn_joblist_delete.on_click(self.on_btn_joblist_delete_clicked)
        self.hginterface.btn_joblist_refresh.on_click(self.on_btn_joblist_refresh_clicked)
        self.hginterface.btn_joblist_visualize.on_click(self.on_btn_joblist_vis_clicked)

        self.hginterface.btn_newjob_reupload.on_click(self.on_btn_newjob_reupload_clicked)

        self.hginterface.dataType.observe(self.onDataTypeChanged)


        self.hginterface.tab.observe(self.tabChanged, "selected_index")

        HGUtil.JOBLOG_FUNC = self.hginterface.print_joblog
        HGUtil.HG_INTERFACE = self.hginterface

        self.hginterface.hideEditAppBtn()
        self.initialized = True
        

    def on_btn_joblist_download_clicked(self, b):
        index = self.hginterface.grid_joblist.get_selected_rows()
        if len(index) == 0:
            return

        index = index[0]
        jobid = self.hginterface.grid_joblist.df.iloc[[index]].index[0]
        item = self.joblist_df.loc[jobid]

        if item.jobstatus != 'Done':
            return

        filename = "Result" + str(jobid) + '(' + item.shapeName + ',' + item.dateFrom + '~' + item.dateTo + ').csv'
        filename = filename.replace('/', '-')
        jobid = str(jobid)
        ret_path = self.WORKING_DIR + '/job/' + jobid + '/results/'

        csv_filename = ''
        if item.dataType == 'SMAP':
            csv_filename = str(os.path.basename(glob.glob(ret_path + '*.zip')[0]))
        else:
            csv_filename = str(os.path.basename(glob.glob(ret_path + '*.csv')[0]))

        # with open(csv_filename, 'r') as f:
        #     data = f.read()
        #     HGUtil.downloadToClient(data, csv_filename)
        HGUtil.startDownloadToClient('./workingdir/job/' + jobid + '/results/' + csv_filename)



    def on_btn_joblist_delete_clicked(self, b):
        rows = self.hginterface.grid_joblist.get_selected_rows()
        if len(rows) == 0:
            return

        self.delete_jobs()




    def on_btn_joblist_refresh_clicked(self, b):
        self.load_joblist(True)

    def delete_jobs(self):
        self.hginterface.showLoading('Deleting data(s)...')

        rows = self.hginterface.grid_joblist.get_selected_rows()

        job = JobManager.JobManager()

        for row in rows:
            jobid = self.hginterface.grid_joblist.df.iloc[[row]].index[0]
            job.deleteJob(jobid)


        self.load_joblist()

        self.hginterface.hideLoading()


    def tabChanged(self,change):

        if change['new'] == 1: # job list
            if self.is_first_refresh:
                self.load_joblist(True)
                self.is_first_refresh = False
            else:
                self.load_joblist()



        # handle map view
        if change["new"] == 2: # vis
            self.hginterface.showHGMap()
        else:
            self.hginterface.showHGMap(False)


    def load_joblist(self, refresh_jobstatus = False):

        if refresh_jobstatus:
            self.hginterface.showLoading(msg='Refreshing data fetch list...')

            job = JobManager.JobManager()
            job.updateAllJobStatus()
            time.sleep(0.5) 
            self.hginterface.hideLoading()

        db = DBManager()
        joblist = db.getJobList()
        joblist = [x[:10] for x in joblist]

        self.joblist_df = self.hginterface.setJobList(joblist)
        self.hginterface.txt_joboutput.value = ''
        self.hginterface.txt_joboutout_title.value = 'Data fetch output'

        self.hginterface.grid_joblist._selected_rows = []


    def load_job_output(self, jobid = None):
        if jobid == None:
            # get selected row index from grid
            index = self.hginterface.grid_joblist.get_selected_rows()
            if len(index) == 0:
                return

            index = index[0]
            jobid = self.hginterface.grid_joblist.df.iloc[[index]].index[0]


        # df = self.joblist_df
        # submit_id = str(df.loc[jobid].submitId)

        # jobid = str(jobid)

        # # check files first
        # file_basename = self.WORKING_DIR + '/job/' + jobid + '/' + submit_id
        # if not os.path.isfile(file_basename + '.stdout') and not os.path.isfile(file_basename + '.stderr'):
        #     self.hginterface.txt_joboutput.value = 'Data fetch output file is not available.'
        #     return

        # stdout = "[Output]\n"
        # with open(file_basename + '.stdout', 'r') as f:
        #     stdout += f.read()

        # self.hginterface.txt_joboutput.value = stdout
        # self.hginterface.txt_joboutout_title.value = 'Data fetch output < jobid : %s >' % (jobid)


        # # if there is error outputs
        # if os.path.isfile(file_basename + '.stderr'):
        #     with open(file_basename + '.stderr') as f:
        #         self.hginterface.txt_joboutput.value += '\n\n[Error output]\n' + f.read()

        
        db = DBManager()
        jobInfo = db.getJobInfo(jobid)
        self.hginterface.txt_joboutput.value = jobInfo[10]

        self.hginterface.set_textarea_scroll('hg_txt_joboutput','top')


    def on_btn_newjob_reupload_clicked(self, b):
        self.hginterface.showFileUpload(True)
        self.uploaded_filename = None

        self.hginterface.file_widget.reset()


    def file_loading(self,change):
        #print 'loading';
        if self.hginterface.file_widget.filename == '':
            return

        self.hginterface.print_joblog("Loading %s" % self.hginterface.file_widget.filename)

    def file_loaded(self, w, name):
        file_widget = self.hginterface.file_widget
        if len(file_widget.list()) != 1:
            return

        filename = os.path.basename(file_widget.list()[0])
        # handle spaces
        new_fname = filename

        # copies uploaded file to upload folder
        upload_path = self.WORKING_DIR + '/upload/'
        os.system('rm -rf ' + upload_path + new_fname) #remove existing file with the same name. for now.
        os.system('mv ' + file_widget.list()[0] + ' ' + upload_path + new_fname)
        # check if uploaded file has shp file, and also mv all files to top-most folder
        shape_name = self.unzip_and_checkfiles(upload_path, new_fname)

        if shape_name == None:
            self.hginterface.alert('Please upload a zip file including shp, dbf, prj and shx files', 'error')
            self.hginterface.hideLoading()
            return


        self.hginterface.alert('File ' + filename + ' is loaded!', 'success')
        self.hginterface.hideLoading()

        self.uploaded_filename = os.path.splitext(new_fname)[0]
        self.hginterface.print_joblog("File uploaded!")
        self.hginterface.print_joblog('Shape name : ' + shape_name)

        self.hginterface.showFileUpload(False, filename)

    def unzip_and_checkfiles(self, path, file_name):
        mandatory = ['shp', 'dbf', 'prj', 'shx']
        shape_name = None
        #fname_only = os.path.splitext(file_name)[0]
        fname_only = file_name.split('.zip')[0]
        os.system('rm -rf ' + path + fname_only)
        HGUtil.mkdir(path + fname_only)
        HGUtil.mkdir(path + fname_only + '/temp')
        os.system('unzip ' + path + file_name + ' -d ' + path + fname_only + '/temp')

        for files in os.walk(path + fname_only + '/temp'):
            check_cnt = 0
            for file in files[2]:
                if file[0] == '.':
                    continue
                filename, file_extension = os.path.splitext(file)
                #print filename, file_extension

                if file_extension[1:] in mandatory:
                    shape_name = filename
                    check_cnt += 1

            if check_cnt == len(mandatory):
                HGUtil.mkdir(path + fname_only + '/shape')
                os.system('mv ' + files[0] + '/* ' + path + fname_only + '/shape/.')
                os.system('rm -rf ' + path + fname_only + '/temp')

                # get shape information
                shape_bound = HGUtil.getShapeBound(path + fname_only + '/shape/' + shape_name + '.shp')
                self.hginterface.draw_preview(shape_bound)

                return shape_name

        # failed. Delete temp folders
        os.system('rm -rf ' + path + fname_only)
        return None


    def file_failed(self):
        self.hginterface.hideLoading()
        self.hginterface.alert('Could not load file contents of %s' % self.hginterface.file_widget.filename, 'error')
        print("Could not load file contents of %s" % self.hginterface.file_widget.filename)


    def on_fetch_button_clicked(self,b):
        # error checking ===========================================================

        if self.uploaded_filename == None:
            self.hginterface.alert('Please upload a shape file first.', type = 'warning')
            return
        #print("get data!")

        # check date values
        if self.hginterface.filePickerAndDatePicker == False:
            try:
                dt.strptime(str(self.hginterface.dateFrom.value), "%m/%d/%Y")
                dt.strptime(str(self.hginterface.dateTo.value), "%m/%d/%Y")
            except ValueError as err:
                self.hginterface.alert('Date format needs to be mm/dd/yyyy', 'warning')
                return
            # return

        # check date from/to
        f = dt.strptime(str(self.hginterface.dateFrom.value), "%m/%d/%Y")
        t = dt.strptime(str(self.hginterface.dateTo.value), "%m/%d/%Y")
        if f > t:
            self.hginterface.alert('Please check the time-period from/to', 'warning')
            return

        # check valid data range for each data type
        if str(self.hginterface.dataType.value) == "SMAP":
            smapStart = dt.strptime("03/31/2015", "%m/%d/%Y")
            if f < smapStart:
                self.hginterface.alert('Please check the date for SMAP is starting from 03/31/2015', 'warning')
                return
        elif str(self.hginterface.dataType.value) == "MODIS-ET/PET/LE/PLE":
            data_limit_start = dt.strptime("01/01/2000", "%m/%d/%Y")
            data_limit_end = dt.strptime("12/31/2014", "%m/%d/%Y")
            if f < data_limit_start or t > data_limit_end:
                self.hginterface.alert('Supported date range for MODIS-ET/PET/LE/PLE is 01/01/2000 ~ 12/31/2014', 'warning')
                return
        # TODO: valid for 17years??
        elif str(self.hginterface.dataType.value) == "MODIS-LAI/FPAR":
            data_limit_start = dt.strptime("01/01/2002", "%m/%d/%Y")
            if f < data_limit_start:
                self.hginterface.alert('Supported date range for MODIS-LAI/FPAR is from 01/01/2002', 'warning')
                return
        elif str(self.hginterface.dataType.value) == "GPM":
            smapStart = dt.strptime("05/01/2014", "%m/%d/%Y")
            if f < smapStart:
                self.hginterface.alert('Please check the date for GPM is starting from 05/01/2014', 'warning')
                return


        # check date 1 year range
        r = relativedelta.relativedelta(f, t)
        if r.years != 0:
            self.hginterface.alert('Date range needs to be maximum of 1 year', 'warning')
            return

        # check data type
        # data type
        if self.hginterface.dataType.value not in self.supportedType:
            self.hginterface.alert('Current version supports following data type(s):\\n  - MODIS, SMAP, GPM', 'warning')
            return

        # job name
        if self.hginterface.txt_newjob_jobname.value == '':
            self.hginterface.alert('Please provide a name for data fetch request', 'warning')
            return

        # error checking done =======================================================================================


        self.hginterface.showLoading(msg='Running data fetch...')

        self.hginterface.clear_joblog()

        self.hginterface.enableFileUpload(False)
        self.hginterface.enableGUIOnProcess(False)


        params = {}
        params['jobname'] = self.hginterface.txt_newjob_jobname.value
        params['data_type']= self.hginterface.dataType.value
        params['data_from'] = self.hginterface.dateFrom.value
        params['data_to'] = self.hginterface.dateTo.value
        params['input_fname'] = self.uploaded_filename
        if params['data_type'] == 'GPM':
            if self.hginterface.dbox_gpm.index == 2: #30m nrt
                params['temporal_res'] = '30m_NRT'
            else:
                params['temporal_res'] = self.hginterface.dbox_gpm.value


        job = JobManager.JobManager(params, self.hginterface.print_joblog)
        ret, msg = job.submitJob()

        # after job submission
        self.hginterface.enableGUIOnProcess(True)
        self.hginterface.enableFileUpload(True)

        if ret == False:
            self.hginterface.alert(msg)
            self.hginterface.hideLoading()
            return

    
        self.hginterface.alert('Requested Job Finished.','success')
        self.hginterface.hideLoading()


    def on_btn_joblist_vis_clicked(self, b):

        index = self.hginterface.grid_joblist.get_selected_rows()
        if len(index) == 0:
            return

        index = index[0]
        jobid = self.hginterface.grid_joblist.df.iloc[[index]].index[0]
        item = self.joblist_df.loc[jobid]

        if item.jobstatus != 'Done':
            return


        self.hginterface.showVisTab()


        self.hginterface.tab.selected_index = 2
        self.hginterface.txt_vis_inst.layout.display= 'none'

        self.hginterface.showLoading('Creating visualization...')
        self.hginterface.setVisInfo(item)
        try:
            #self.hginterface.enableGUIOnVis(False)

            self.removeMap()
            self.prepareMap()
            self.visualization(item)
            #self.visualization(selected)
            #print ('\n*** Done ***')
        except:
            #self.hginterface.txt_vis_inst.layout.display= 'block'
            self.hginterface.alert(traceback.format_exc(),'error','Error occured in visualization')

        #self.hginterface.enableGUIOnVis(True)
        self.hginterface.hideLoading()




    def visualization(self,selectedItem):
        jobid = str(selectedItem.name)

        ret_dir = HGUtil.WORKING_DIR + '/job/' + jobid + '/results/'
        infoPath = ret_dir + "vis_info.out"
        # if not exist, create it
        if not os.path.exists(infoPath):
            datatype = selectedItem.dataType
            sf = sorted(glob.glob(ret_dir + '*.shp'))[0]
            csvFilePath = sorted(glob.glob(ret_dir + "/*.csv"))[-1] # for last one

            self.visManager.create_vis_data(datatype, sf, csvFilePath, ret_dir)


        self.hginterface.draw_map(jobid)
        self.hginterface.display_vis_map()
        # display(self.hginterface.map)
        self.moveMapArea()


    def on_vis_vis_button_clicked(self,b):

        # check
        selected = self.hginterface.visData.value
        if selected == self.hginterface.SELECT_DATA:
            self.hginterface.alert('Select a data to be visualized','warning')
            return

        #print ('\n*** Start visualization ***')
        self.hginterface.showLoading('Creating visualization...')

        try:
            self.hginterface.enableGUIOnVis(False)
            self.removeMap()
            self.prepareMap()
            #self.visualization(selected)
            #print ('\n*** Done ***')
        except:

            self.hginterface.alert(traceback.format_exc(),'error','Error occured in visualization')

        self.hginterface.enableGUIOnVis(True)
        self.hginterface.hideLoading()

    def on_vis_del_button_clicked(self,b):
        target = self.hginterface.visData.value
        if target == self.hginterface.SELECT_DATA:
            return
        else:
            if self.hginterface.btn_vis_del.button_style == '':
                self.hginterface.btn_vis_del.button_style = 'danger'
                self.hginterface.btn_vis_del.description = 'Sure?'
            elif self.hginterface.btn_vis_del.button_style == 'danger':
                # print ("Delete selected directory and set the visData to default")
                target = target.replace("/", ",")
                os.system('rm -rf %s/%s/%s' %(self.WORKING_DIR,"results",target))
                self.hginterface.btn_vis_del.description = 'Delete'
                self.updateVisData()
                print ("\n*** Result " + target + " is deleted ***")
                display(Javascript('''refreshLog();'''))




    # def fileLoader(self):
    #     display(HTML(fileLoaderScript))

    def prepareMap(self):
        self.hginterface.prepareMap()




    def showVisDataInformation(self,change):
        if not change["new"] == self.hginterface.SELECT_DATA:
            #show things
            lines = "** Result information **\n"
            dirPath = self.WORKING_DIR + "/results/" + change["new"].replace("/", ",")
            with open(dirPath + "/info.dat", "r") as f:
                for line in f:
                    items = line.split("|")
                    lines += "   - " + items[0] + " :  "
                    lines += items[1]

            self.hginterface.visTextArea.value = lines
            self.hginterface.visTextArea.layout.display = 'block'

            self.hginterface.btn_vis_del.disabled = False

        else:
            self.hginterface.visTextArea.layout.display = 'none'
            self.hginterface.btn_vis_del.disabled = True

        self.hginterface.btn_vis_del.button_style = ''
        self.hginterface.btn_vis_del.description = 'Delete'

    def updateVisData(self):
        dirs = []
        if self.sortBy == "date":
            dirs = sorted(glob.glob(self.WORKING_DIR + "/results/*/"), key=lambda x: x.split("_")[-2] + x.split("_")[-1], reverse=True)
        else:
            dirs = sorted(glob.glob(self.WORKING_DIR + "/results/*/"))

        arr = [self.hginterface.SELECT_DATA]
        for d in dirs:
            tmp = d.split("/")[-2]
            tmp = tmp.replace(",", "/")
            arr.append(tmp)

        self.hginterface.visData.options = arr
        self.hginterface.visData.value = self.hginterface.SELECT_DATA


    def toggleSort(self,change):
        if change["new"] is True:
            self.sortBy = "date"
        else:
            self.sortBy = "name"

        self.updateVisData()



    def moveMapArea(self):
        display(Javascript('''
        var map = $('div.output_subarea > div > div > iframe').parent().parent().parent().parent();
        map.attr('id','hgMap');

        '''))



        return
        display(HTML('''<script class='scriptElem'>
            map = document.getElementsByClassName("output_subarea");
            for(var i = 0; i < map.length; i++)
            {
            	if(map[i].getElementsByTagName("div").length > 0)
                {
                    target = document.getElementsByClassName("code_cell");
                    $(map[i]).css("max-width","1800px");
                    $(map[i]).attr("id", "hgMap");
                    //$(map[i]).css("padding-left","88px");
                    $(target[0]).append($(map[i]));
                    break;
                }
            }
            hideScriptElements();
        </script>'''))

    def removeMap(self):
        display(Javascript('''
            $('#hgMap').remove();
        '''))
        return
        display(HTML('''<script class='scriptElem'>
            map = document.getElementsByClassName("output_subarea");
            for(var i = 0; i < map.length; i++)
            {
            	if(map[i].getElementsByTagName("div").length > 0)
                {
                    map[i].parentNode.removeChild(map[i]);
                    i--;
                }
            }
            hideScriptElements();
            </script>'''))


    def onDataTypeChanged(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            if change['new'] not in self.supportedType:
                self.hginterface.alert('Current version supports following data type(s):\\n  - MODIS, SMAP, GPM', 'warning')
                self.hginterface.dataType.value = change['old']
                return

            if change['new'] == 'GPM':
                self.hginterface.showGPMRes(True)
            else:
                self.hginterface.showGPMRes(False)





# // end of class HGMain

hgmain = HGMain()

def interface():
    hgmain.main()
