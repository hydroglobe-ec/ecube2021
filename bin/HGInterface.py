import ipywidgets as ipyw
from IPython.display import HTML, display, clear_output, Javascript
from hublib.ui import FileUpload
import qgrid
import pandas as pd
import json
import copy
import folium
from HGUtil import HGUtil
import base64
from jinja2 import Template, Environment, PackageLoader
from branca.element import Element, JavascriptLink, CssLink
import os, sys
import json


class HGInterface:

    filePickerAndDatePicker = False
    modelInfo = None

    dataType = None
    fetchDataButton = None
    dateFrom = None
    dateTo = None
    file_widget = None
    visData = None
    btn_vis_del = None
    btn_vis_vis = None
    visTextArea = None
    logCheckBox = None
    sortCheckBox = None
    tab = None

    btn_joblist_visualize = None
    btn_joblist_download = None
    btn_joblist_delete = None
    btn_joblist_refresh = None
    txt_joboutput = None
    grid_joblist = None
    html_visinfo = None
    txt_vis_inst = None

    lb_newjob_fileupload = None
    btn_newjob_reupload = None
    txt_newjob_jobname = None

    txt_joboutout_title = None

    loading_selector = None

    form_map_preview = None

    lb_gpm_label = None
    dbox_gpm = None




    TOOL_WIDTH = 1200

    SELECT_DATA = "Select a result data.."
    JOBLIST_COLS = ['jobid','jobname','shapeName','dataType','dateFrom','dateTo','submitTime','jobstatus']
    JOBLIST_COLS_DB = ['jobid','submitId', 'fileName','shapeName','dataType','dateFrom','dateTo','submitTime','jobstatus','jobname']

    GRID_CONFIG_JS='''
     var col = [{"name":"ID","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":70,"field":"jobid","id":"jobid","cssClass":"integer idx-col","previousWidth":70},{"name":"Name","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":242,"field":"jobname","id":"jobname","cssClass":"string","previousWidth":242},{"name":"Shape Name","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":240,"field":"shapeName","id":"shapeName","cssClass":"string","previousWidth":240},{"name":"Product  Type","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":170,"field":"dataType","id":"dataType","cssClass":"string","previousWidth":170},{"name":"Date Start ","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":102,"field":"dateFrom","id":"dateFrom","cssClass":"string","previousWidth":102},{"name":"Date End","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":94,"field":"dateTo","id":"dateTo","cssClass":"string","previousWidth":94},{"name":"Requested Time","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":125,"field":"submitTime","id":"submitTime","cssClass":"string","previousWidth":145},{"name":"Status","resizable":true,"sortable":false,"minWidth":30,"rerenderOnResize":false,"headerCssClass":null,"defaultSortAsc":true,"focusable":true,"selectable":true,"width":88,"field":"jobstatus","id":"jobstatus","cssClass":"string","previousWidth":88}];
     window.slick_grid.setColumns(col);
    '''

    hydroglobeJS = ""
    loadingCSS = ""
    fileSaverJS = ""
    jszipJS = ""
    leafletHeatJS = ""
    map = None  
    vis_geojson = ''  

    def init(self):

        self.loadJS()
        self.insertJS()



        self.disableOutputScroll()

        form = self.create_newjob_tab()

        # create each tabs
        form = self.create_newjob_tab()
        vis = self.create_vis_tab()
        setting = self.create_setting_tab()
        joblist = self.create_joblist_tab()

        tab = ipyw.Tab()
        #tab.children = [joblist, form, vis, setting]
        tab.children = [form, joblist, vis]
        tab.set_title(0, "Data Request")
        tab.set_title(1, "Status")
        tab.set_title(2, "Visualization")
        #tab.set_title(3, "Settings")

        display(tab)
        self.initCustomView()

        self.tab = tab

        self.showVisTab(False)

        #self.logCheckBox.observe(self.toggleLogArea, "value")
        #tab.observe(self.tabChanged, "selected_index")

    """
    def override_qgrid(self):
        qgrid.QgridWidget.update_table_cb = None
        qgrid.QgridWidget._old_update_table = qgrid.QgridWidget._update_table

        def new_update_table(self, update_columns=False, triggered_by=None):
            self._old_update_table(update_columns = update_columns, triggered_by = triggered_by)
            #print 'table update callback'
            if self.update_table_cb != None:
                self.update_table_cb()

        qgrid.QgridWidget._update_table = new_update_table

    """


    def create_setting_tab(self):
        self.sortCheckBox = self.makeSortCheckBox()

        setting_items = [self.sortCheckBox]

        setting = ipyw.Box(setting_items, layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            border='1px solid #ddd',
            width=str(self.TOOL_WIDTH) + 'px',
            padding='10px 10px 10px 10px'
        ))

        setting.add_class('hg_tab_content')

        return setting

    def create_vis_tab(self):
        # visualization
        self.visData = self.visDataSelection()
        #self.updateVisData()
        self.btn_vis_del = self.makeDelButton()
        self.btn_vis_vis = self.makeVisButton()


        self.visTextArea = self.makeVisTextArea()
        self.visTextArea.layout.display = 'none'

        form_item_layout = ipyw.Layout(
            display='flex',
            flex_flow='row',
        #     justify_content='space-between'
            justify_content='flex-start',
            align_items='center'
        )
        """
        vis_items = [ipyw.Box([self.visData, ipyw.Label(value='',layout=ipyw.Layout(height='32px', margin="0px 12px")), self.btn_vis_del,
                            ipyw.Label(value='', layout=ipyw.Layout(height='32px', margin="0px 22px")), self.btn_vis_vis], layout=form_item_layout),
                    ipyw.Box([self.visTextArea], layout=form_item_layout)]
        """
        vis_items = []
        self.txt_vis_inst = ipyw.Label('Please select a data request history on the [Status] tab, then click the [Visualize] button.')
        vis_items.append(self.txt_vis_inst)
        self.html_visinfo = ipyw.HTML()
        vis_items.append(self.html_visinfo)


        # map area
        #vis_items.append(ipyw.HTML(value = '<div id="map_area"></div>'))

        html_map_vis = ipyw.HTML('<iframe id="iframe_map_vis" style="width:100%;height:600px;border:1px solid silver;"></iframe>')
        vis_items.append(html_map_vis)

        vis = ipyw.Box(vis_items, layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            border='1px solid #ddd',
            width='100%',
            padding='10px 10px 10px 10px'
        ))

        vis.add_class('hg_tab_content')

        return vis

    def create_newjob_tab(self):
        self.dataType = self.datatypeSelection()
        #self.modelInfo = self.modelInfoSelection()
        # yearInCells = yearTextLine()

        if self.filePickerAndDatePicker == True:
            self.dateFrom = self.getDateFrom()
            self.dateTo = self.getDateTo()
        else:
            self.dateFrom = self.dateFromText()
            self.dateTo = self.dateToText()
            # dateFrom.on_submit(test)


        self.fetchDataButton = self.fetchButton()
        #self.geohubFileLoader()
        self.file_widget = FileUpload("","", dir='fileupload_tmpdir', maxsize='500M', basic=True)
        #self.file_widget = ipyw.Checkbox(value=True)

        #self.logCheckBox = self.makeLogCheckBox()
        self.lb_newjob_fileupload = ipyw.Label()
        self.lb_newjob_fileupload.layout.display = 'none'
        self.btn_newjob_reupload = self.create_btn('Upload a different file')
        self.btn_newjob_reupload.layout.display = 'none'

        self.txt_newjob_jobname = ipyw.Text();



        form_item_layout = ipyw.Layout(
            display='flex',
            flex_flow='row',
        #     justify_content='space-between'
            justify_content='flex-start',
            align_items='center'
        )
        align_kw = dict(
            _css = (('.widget-label', 'min-width', '10px'),),
            margin = '0px 5px 5px 20px',
            width = '80px'
        )
        align_label = dict(
            _css = (('.widget-label', 'min-width', '10px'),),
            margin = '0px 5px 5px 20px',
            width = '400px',
            height = '20px'
        )
        align_line = dict(
            _css = (('.widget-label', 'min-width', '10px'),),
            margin = '0px 5px 5px 20px',
            width = '400px',
            height = '14px'
        )

        self.lb_gpm_label = ipyw.Label(value='Select a Temporal Resolution',**align_label)
        self.dbox_gpm = ipyw.Dropdown(
                options=['Daily', '30m', '30m Near Real Time (NRT)'],
                value='Daily',
                description='',
                disabled=False,
                layout=ipyw.Layout(width="220px"),
                button_style='')

        self.showGPMRes(False)

        html_jobname_info = ipyw.HTML(value='<i class="fa fa-info-circle text-info" style="font-size: 16px" title="Provide a concise logical name for your request so you can understand its purpose and also track its progress in the [status] tab"></i>')

        form_items = [
            ipyw.Box([ipyw.Label(value='Upload a shape file (a zip file having shp, dbf, prj and shx files)',**align_label)], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='',**align_kw), self.file_widget.w, self.lb_newjob_fileupload, self.btn_newjob_reupload, ipyw.Label(value='',layout=ipyw.Layout(width='10px'))], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='                                                 ',**align_line)], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='Select an Earth Observation product type',**align_label)], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='',**align_kw), self.dataType], layout=form_item_layout),
            ipyw.Box([self.lb_gpm_label], layout=form_item_layout), #for gpm only
            ipyw.Box([ipyw.Label(value='',**align_kw), self.dbox_gpm], layout=form_item_layout), #for gpm only
            ipyw.Box([ipyw.Label(value='                                                 ',**align_line)], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='Define time-period for extracting data (maximum of 1 year)',**align_label)], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='',**align_kw),
                      self.dateFrom, ipyw.Label(value='_',layout=ipyw.Layout(height='32px', margin="0px 15px")), self.dateTo], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='                                                 ',**align_line)], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='Enter name for this data request',**align_label), html_jobname_info], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='',**align_kw),self.txt_newjob_jobname], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='                                                 ',**align_line)], layout=form_item_layout),
            ipyw.Box([ipyw.Label(value='',**align_kw),self.fetchDataButton, ipyw.Label(value='',layout=ipyw.Layout(height='32px', margin="0px 19px"))
                    ], layout=form_item_layout)
            #        ,ipyw.Box([self.logCheckBox], layout=form_item_layout)], layout=form_item_layout)
            # ipyw.Box([ipyw.Label(value='',layout=ipyw.Layout(width='470px')),fetchDataButton], layout=form_item_layout)
        ]


        # map boundary preview

        html_map_preview = ipyw.HTML('<iframe id="iframpe_map_preview" width=480 height=300 border=0></iframe>')



        # log area
        form_bottom_items = []
        form_bottom_items.append(ipyw.HTML(value='<hr>'))
        self.txt_newjoblog = ipyw.Textarea(value='', layout=ipyw.Layout(width="100%", height="250px"))
        self.txt_newjoblog.disabled = True
        self.txt_newjoblog.add_class('hg_txt_newjoblog')
        ac_log = ipyw.Accordion(children=[self.txt_newjoblog])
        ac_log.set_title(0, 'Logs')
        # ac_log.selected_index = None
        form_bottom_items.append(ac_log)

        form_bottom = ipyw.Box(form_bottom_items, layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            width= '1000px',
            padding='10px 10px 10px 10px'
        ))

        form_right = ipyw.Box([ipyw.HTML('<b>Shape Boundary Preview</b>'),  html_map_preview] , layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            width= '500px',
            padding='10px 10px 10px 10px'
        ))
        form_right.layout.display = 'none'
        self.form_map_preview = form_right


        form_left = ipyw.Box(form_items, layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            width= '500px',
            padding='10px 10px 10px 10px'
        ))


        form_top = ipyw.HBox([form_left, form_right])
        form = ipyw.Box([form_top, form_bottom], layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            border='1px solid #ddd',
            width= '100%',
            padding='10px 10px 10px 10px'
        ))
        #form = ipyw.HBox([form_left, form_right] , layout=ipyw.Layout(border='1px solid #ddd', width= '100%'))

        """
        form = ipyw.Box(form_items, layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            border='1px solid #ddd',
            width= '100%',
            padding='10px 10px 10px 10px'
        ))
        """

        form.add_class('hg_tab_content')

        return form

    def create_joblist_tab(self):
        items = []
        self.btn_joblist_visualize = self.create_btn('Visualize', 'success')
        self.btn_joblist_download = self.create_btn('Download', 'warning')
        self.btn_joblist_delete = self.create_btn('Delete', 'danger')
        self.btn_joblist_refresh = self.create_btn('Refresh', 'info')

        # Buttons
        items.append(ipyw.Box([self.btn_joblist_visualize, self.btn_joblist_download, self.btn_joblist_delete, self.btn_joblist_refresh]))
        #items.append(ipyw.Box([self.btn_joblist_visualize, self.btn_joblist_delete, self.btn_joblist_refresh]))

        # Job list Grid
        qgrid.set_grid_option('maxVisibleRows', 10)
        df = pd.DataFrame(columns=self.JOBLIST_COLS).set_index('jobid')

        self.grid_joblist = qgrid.show_grid(df, grid_options={'editable': False, 'fullWidthRows':False,'forceFitColumns':False, 'defaultColumnWidth':144})
        self.grid_joblist.add_class('hg_grid_joblist')
        items.append(self.grid_joblist)

        # for grid click handler
        display(Javascript(
        '''
        document.addEventListener("DOMNodeInserted", function (ev) {
          var node = ev.target;
          if( $(node).hasClass('slick-row') ){
          	$(node).click(function(){
                if ($(this)[0].children.length > 0){
                    var jobid = $(this)[0].children[0].innerHTML;
                    //console.log("Init.hgmain.load_job_output(" + jobid+ ")");
                    IPython.notebook.kernel.execute("Init.hgmain.load_job_output(" + jobid+ ")");
                }
            });
          }
        });
        '''
        ))


        self.txt_joboutout_title = ipyw.Label(value = 'Output')
        items.append(self.txt_joboutout_title)
        self.txt_joboutput = ipyw.Textarea(value='',
                            layout=ipyw.Layout(height="250px", width="100%"),
                            disabled=True)

        self.txt_joboutput.add_class('hg_txt_joboutput')

        items.append(self.txt_joboutput)

        panel = ipyw.Box(items, layout=ipyw.Layout(
            display='flex',
            flex_flow='column',
            border='1px solid #ddd',
            width='100%',
            padding='10px 10px 10px 10px'
        ))

        panel.add_class('hg_tab_content')
        return panel

    """
    def setJobOutputText(self, text = ''):
        self.html_joboutput.value='<pre style="font-size:12px;line-height:13px">' + text + '</pre>'
    """

    def loadJS(self):
        with open('./hydroglobe.js', 'r') as f:
            self.hydroglobeJS = f.read()

        with open('./loading.css', 'r') as f:
            self.loadingCSS = f.read()


        with open('./FileSaver.min.js', 'r') as f:
            self.fileSaverJS = f.read()

        with open('./jszip.min.js', 'r') as f:
            self.jszipJS = f.read()

        with open('./leaflet-heat.js', 'r') as f:
            self.leafletHeatJS = f.read()

    def insertJS(self):
        # alert
        display(Javascript(url = 'https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.0/jquery-confirm.min.js'))
        display(Javascript('''
            $('head').append('<link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.0/jquery-confirm.min.css">');
        '''))
        # wait me loading
        display(Javascript(filename = 'waitMe.min.js'))
        display(Javascript('''
            $('head').append('<link rel="stylesheet" type="text/css" href="waitMe.min.css">');
        '''))


    def create_btn(self, description, button_style = '', tooltip = '', disabled = False):
        return ipyw.Button(
            description=description,
            disabled=disabled,
            button_style=button_style,
            tooltip=tooltip)


    def yearTextLine(self):
        return ipyw.Text(
                value='2014',
                placeholder='20xx',
                description='Year:',
                disabled=False)

    ###### ipywidgets 6.0.0 or more
    def getDateFrom(self):
        return ipyw.DatePicker(
                description='Date from',
                value=dt(2014, 1, 1))

    def getDateTo(self):
        return ipyw.DatePicker(
                description='Date to',
                value=dt(2014, 12, 5))

    ###### ipywidgets under 6.0.0
    def dateFromText(self):
        return ipyw.Text(
                # value='12/21/2013',
                value='01/01/2014',
                placeholder='',
                description='',
                layout=ipyw.Layout(width="150px"),
                disabled=False)

    def dateToText(self):
        return ipyw.Text(
                # value='01/21/2014',
                value='01/05/2014',
                placeholder='',
                description='',
                layout=ipyw.Layout(width="150px"),
                disabled=False)

    def datatypeSelection(self):
        # 'success', 'info', 'warning', 'danger' or ''
        return ipyw.Dropdown(
                # options=['MODIS', 'SMAP'],
                options=['MODIS-ET/PET/LE/PLE', 'MODIS-LAI/FPAR', 'SMAP', 'AMSR-E', 'GPM', 'NLDAS'],
                value='MODIS-ET/PET/LE/PLE',
                description='',
                disabled=False,
                layout=ipyw.Layout(width="220px"),
                button_style='')

    def modelInfoSelection(self):
        # 'success', 'info', 'warning', 'danger' or ''
        return ipyw.Dropdown(
                options=['SWAT', 'HEC-HMS', 'MODFLOW', 'Others'],
                value='SWAT',
                description='',
                layout=ipyw.Layout(width="150px"),
                disabled=False,
                button_style='')

    def fetchButton(self):
        return ipyw.Button(
                description='Get Data',
                disabled=False,
                button_style='success', # 'success', 'info', 'warning', 'danger' or ''
                icon='check')


    def visDataSelection(self):
        # 'success', 'info', 'warning', 'danger' or ''
        return ipyw.Dropdown(
                options=[self.SELECT_DATA],
                value=self.SELECT_DATA,
                description='',
                layout=ipyw.Layout(width="430px"),
                disabled=False,
                button_style='')

    def makeVisButton(self):
        return ipyw.Button(
                description='Show map',
                disabled=False,
                button_style='success', # 'success', 'info', 'warning', 'danger' or ''
                tooltip='Visualize on the map area',
                icon='check')

    def makeDelButton(self):
        return ipyw.Button(
                description='Delete',
                disabled=False,
                button_style='', # 'success', 'info(blue)', 'warning(yellow)', 'danger(red)' or ''
                # tooltip='Visualize on the map area',
                layout=ipyw.Layout(width="100px"),
                icon='check')

    def makeVisTextArea(self):
        return ipyw.Textarea(
                value='',
                layout=ipyw.Layout(width="100%", height="300px"),
                disabled=True)

    def makeLogCheckBox(self):
        return ipyw.Checkbox(
                value=False,
                description='Show log area',
                layout=ipyw.Layout(width="200px"),
                disabled=False)

    def makeSortCheckBox(self):
        return ipyw.Checkbox(
                value=True,
                description='Results sorted by date / time',
                layout=ipyw.Layout(width="300px"),
                disabled=False)



    def initCustomView(self):
        display(HTML('''
        <style>
            .container { width:97% !important; }
            div#site { height: 100% !important; }
            .widget-hbox .widget-label { max-width:350ex; text-align:left; padding-left: 0.5em;}
            .form-control {text-align:center; font-family: monospace; overflow-y: hidden;}
            .widget-dropdown .dropdown-menu {width:100%; max-height:260px}
            .widget-textarea textarea {resize: none; text-align: left;}
        </style>

        <style>
        .ui-tooltip {
            background: #444;
            color: #FFF;
            overflow: hidden;
            -webkit-background-clip: padding-box;
            -moz-background-clip: padding;
            background-clip: padding-box;
            -webkit-border-radius: 6px;
            -moz-border-radius: 6px;
            -ms-border-radius: 6px;
            -o-border-radius: 6px;
            border-radius: 6px;
            -webkit-box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
            -moz-box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
            -ms-box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
            -o-box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
            box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
        }
        </style>
        <script>

            function showHgMap() {
                $('#hgMap').show();
            }

            function hideHgMap() {
                $('#hgMap').hide();
            }


            $( function() {
                $( document ).tooltip();
            });
        </script>'''))

    def print_joblog(self, *args, **kw):
        endline = '\n'
        if 'end' in kw:
            endline = kw['end']

        for msg in args:
            self.txt_newjoblog.value += str(msg) + endline
        # scroll to bottom
        self.set_textarea_scroll('hg_txt_newjoblog','bottom')
    
    def clear_joblog(self):
        self.txt_newjoblog.value = ''

    def get_joblog(self):
        return self.txt_newjoblog.value

    def enableButtons(self,tf):
        self.fetchDataButton.disabled = not tf
        self.btn_vis_del.disabled = not tf
        self.btn_vis_vis.disabled = not tf
        self.visData.disabled = not tf
        #self.logCheckBox.disabled = not tf
        self.sortCheckBox.disabled = not tf
        self.dataType.disabled = not tf
        #self.modelInfo.disabled = not tf
        self.dateFrom.disabled = not tf
        self.dateTo.disabled = not tf


    def enableGUIOnProcess(self,tf):
        if tf is True:
            self.fetchDataButton.description = "Get Data"
            self.fetchDataButton.button_style = 'success'

        else:
            self.fetchDataButton.description = "Submitting..."
            self.fetchDataButton.button_style = ''
            self.btn_vis_del.description = 'Delete'
            self.btn_vis_del.button_style = ''


        # toggle buttons
        self.enableButtons(tf)

    def enableGUIOnVis(self,tf):
        if tf is True:
            self.btn_vis_vis.description = "Show map"
            self.btn_vis_vis.button_style = 'success'
            # try to hideLoading in moveMapArea()

        else:
            self.btn_vis_vis.description = "Running..."
            self.btn_vis_vis.button_style = ''
            self.btn_vis_del.description = 'Delete'
            self.btn_vis_del.button_style = ''

        self.enableButtons(tf)

    def showFileUpload(self, visible, filename=''):
        self.lb_newjob_fileupload.value = filename
        self.lb_newjob_fileupload.layout.display = 'none' if visible else 'inline'
        self.btn_newjob_reupload.layout.display = 'none' if visible else 'inline'
        self.file_widget.w.layout.display = 'inline' if visible else 'none'




    def alert(self, msg, type = 'none', title = '', autoclose = None): #type = [warning, error, success, info]
        # display(HTML('<script class="scriptElem"> alert("'+ msg +'"); removeScriptElements(); </script>'))
        # escape
        title = title.replace("'", "\\'")
        autoclose_str = ''
        if autoclose != None:
            autoclose_str = ", autoClose: 'ok|%s'" % autoclose

        js = "$(function(){$.alert({title:'" + title +"',content: `"+ msg +"`,animationSpeed: 150 " + autoclose_str + ", animateFromElement: false, " + HGUtil.ALERT_TYPES[type] + " theme: 'modern'});});"
        display(Javascript(js))

    def confirm(self, msg, callback_ok, type = 'none'):
        js = '''
        $.confirm({
            title: '',
            content: '%s',
            theme: 'modern',
            %s
            buttons: {
                confirm: function () {
                    %s
                },
                cancel: function () {

                }
            }
        });
        ''' % (msg, HGUtil.ALERT_TYPES[type], 'IPython.notebook.kernel.execute("Init.hgmain.' + callback_ok + '")')

        display(Javascript(js))


    def disableOutputScroll(self):
        display(Javascript('''
        require(["notebook/js/outputarea"],
            function (oa) {
                oa.OutputArea.prototype._should_scroll = function(lines) { return false; }
        });

        '''))


    def hideLoading(self):
        #display(Javascript('hideLoading();'))
        loading_selector = self.loading_selector
        if loading_selector == None:
            loading_selector = '.hg_tab_content'
        display(Javascript('require(["waitMe.min.js"], function() { $("%s").waitMe("hide"); });' % (loading_selector)))
        self.loading_selector = None

    def showLoading(self, msg = '', selector = '.hg_tab_content'):
        self.loading_selector = selector
        js = ('$(function(){var msg = "%s";' % (msg)) + ('var selector = "%s";' % (selector)) +  '''
        require(["waitMe.min.js"], function() {
            $(selector).waitMe({
                effect: 'orbit',
                text: msg,
                color: 'black'
            });
        });
        });
        '''
        display(Javascript(js))

    def enableFileUpload(self, enable = True):
        if enable:
            display(Javascript('''$("input[type='file']").removeAttr("disabled");'''))
        else:
            display(Javascript('''$("input[type='file']").attr("disabled", "disabled");'''))


    def showHGMap(self, show = True):
        if show:
            display(Javascript('showHgMap();'))
        else:
            display(Javascript('hideHgMap();'))

    def setJobList(self, joblist): # joblist is a list
        # to config column order and size
        if len(joblist) == 0:
            self.grid_joblist.df = pd.DataFrame()
            display(Javascript(self.GRID_CONFIG_JS))
            return


        df = pd.DataFrame.from_records(joblist, columns=self.JOBLIST_COLS_DB)

        #df = pd.DataFrame.from_dict(data)
        #df = df.sort_values(by=['jobid'], ascending = False)
        df = df.set_index('jobid')

        #hide some fields
        #df.drop('submitId', 1)
        #order columns, remove other data
        df_new = df[self.JOBLIST_COLS[1:]]

        self.grid_joblist.df = df_new

        display(Javascript(self.GRID_CONFIG_JS))

        return df


    def set_textarea_scroll(self, class_name, loc): #top or bottom
        display(Javascript('''
            $(function(){
                var class_name = "''' + class_name + '''";
                var loc = "''' + loc + '''";
                var textarea = $("." + class_name + " > textarea");
                if(textarea.length != 0){
                    if(loc == "bottom")
                        textarea[0].scrollTop = textarea[0].scrollHeight;
                    else
                        textarea[0].scrollTop = 0;
                }

            });
        '''))


    def setVisInfo(self, info): # info is object(Series)
        self.html_visinfo.value = '''
        <table class = "rendered_html" width="100%">
          <thead>
            <tr style="text-align: left !important;">
              <th>ID</th>
              <th>Name</th>
              <th>Shape Name</th>
              <th>Product Type</th>
              <th>Date Start</th>
              <th>Date End</th>
              <th>Requested Time</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th>''' + str(info.name) + '''</th>
              <td>''' + info.jobname + '''</td>
              <td>''' + info.shapeName + '''</td>
              <td>''' + info.dataType + '''</td>
              <td>''' + info.dateFrom + '''</td>
              <td>''' + info.dateTo + '''</td>
              <td>''' + info.submitTime + '''</td>
            </tr>
          </tbody>
        </table>
        '''


    def draw_preview(self, bounds):

        # todo: handle projection error

        x1,y1,x2,y2 = bounds
        map_preview = folium.Map()
        map_preview.fit_bounds([[y1, x1], [y2, x2]])
        folium.Rectangle(bounds=[[y1, x1], [y2, x2]], fill_color='#31708f', fill_opacity=0.2, weight=1, color='#31708f').add_to(map_preview)

        html_map = map_preview.get_root().render()
        html_b64 = base64.b64encode(html_map.encode('utf-8'))
        #self.html_map_preview = ipyw.HTML('<iframe src="data:text/html;charset=utf-8;base64,' + html_b64 + '" width=480 height=300></iframe>')
        display(Javascript('''
            $(function(){
                var map_preview = document.getElementById("iframpe_map_preview");
                if(map_preview != null)
                    map_preview.src = "data:text/html;charset=utf-8;base64, %s";
            });
        '''%(html_b64.decode())))
        self.form_map_preview.layout.display = 'inline'


    def prepareMap(self):
        center = [40.8, -86]
        zoom = 8
        self.map = folium.Map(location=[40.8, -86])
        ##########################################################  scrollWheelZoom = false
        self.map._template = Template(u"""
            {% macro header(this, kwargs) %}
                <style> #{{this.get_name()}} {
                    position : {{this.position}};
                    width : {{this.width[0]}}{{this.width[1]}};
                    height: {{this.height[0]}}{{this.height[1]}};
                    left: {{this.left[0]}}{{this.left[1]}};
                    top: {{this.top[0]}}{{this.top[1]}};
                    }
                </style>
            {% endmacro %}
            {% macro html(this, kwargs) %}
                <div class="folium-map" id="{{this.get_name()}}" ></div>
            {% endmacro %}
            {% macro script(this, kwargs) %}
                {% if this.max_bounds %}
                    var southWest = L.latLng({{ this.min_lat }}, {{ this.min_lon }});
                    var northEast = L.latLng({{ this.max_lat }}, {{ this.max_lon }});
                    var bounds = L.latLngBounds(southWest, northEast);
                {% else %}
                    var bounds = null;
                {% endif %}
                var {{this.get_name()}} = L.map(
                                      '{{this.get_name()}}',
                                      {center: [{{this.location[0]}},{{this.location[1]}}],
                                      zoom: 8,
                                      maxBounds: bounds,
                                      scrollWheelZoom: false,
                                      layers: [],
                                      worldCopyJump: false,
                                      crs: L.CRS.{{this.crs}}
                                     });
                {% if this.control_scale %}L.control.scale().addTo({{this.get_name()}});{% endif %}
            {% endmacro %}
            """)  # noqa

        self.map.get_root().header.add_child(Element(
                ''' <style type=text/css>
                    .info {
                        padding: 6px 8px;
                        font: 14px/16px Arial, Helvetica, sans-serif;
                        background: white;
                        background: rgba(255,255,255,0.8);
                        box-shadow: 0 0 15px rgba(0,0,0,0.2);
                        border-radius: 5px;
                    }
                    .info h4 {
                        margin: 0 0 2px;
                        color: #777;
                    }
                    .imgButton {
                        padding: 6px 8px;
                        font: 14px/16px Arial, Helvetica, sans-serif;
                        background: transparent;
                        border-radius: 5px;
                    }
                    .legend {
                        line-height: 18px;
                        color: #555;
                    }
                    .legend i {
                        width: 22px;
                        height: 18px;
                        float: left;
                        margin-right: 8px;
                        opacity: 0.7;
                    }
                    .toggles {
                        width: 90px;
                    }
                    .radioLabel{
                        width: 60px;
                        padding-left: 5px;
                    }

                    #slider {
                        padding: 3px 180px;
                    }
                    ''' +self.loadingCSS+ '''
                    </style>'''), name='map')

        self.map.get_root().header.add_child(JavascriptLink("https://code.highcharts.com/highcharts.js"), name="highcharts")
        self.map.get_root().header.add_child(JavascriptLink("https://code.highcharts.com/modules/exporting.js"), name="exporting")
        self.map.get_root().header.add_child(JavascriptLink("https://code.highcharts.com/highcharts-more.js"), name="highcharts-more")
        self.map.get_root().header.add_child(JavascriptLink("https://code.jquery.com/jquery-1.12.4.js"), name="jquery")
        self.map.get_root().header.add_child(JavascriptLink("https://code.jquery.com/ui/1.12.1/jquery-ui.js"), name="jquery-ui")
        # self.map.get_root().header.add_child(JavascriptLink("https://raw.githubusercontent.com/eligrey/FileSaver.js/master/FileSaver.min.js"), name="file-saver")
        self.map.get_root().header.add_child(CssLink("https://code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css"), name="jquery-ui-css")
        self.map.get_root().header.add_child(Element("<script>" + self.fileSaverJS + "</script>"), name='file-saver')
        self.map.get_root().header.add_child(Element("<script>" + self.jszipJS + "</script>"), name='jszip')
        self.map.get_root().script.add_child(Element(self.leafletHeatJS), name='leaflet-heat')
        # self.map = resultPanel()
        # display(self.map)
        # return self.map

    def draw_map(self, jobid):
        infoPath = HGUtil.WORKING_DIR + "/job/" + jobid + "/results/vis_info.out"


        with open(infoPath, 'r') as f:
            visinfo = json.load(f)


        # set map center here
        #print [[visinfo['minY'], visinfo['minX']], [visinfo['maxY'], visinfo['maxX']]]
        self.map.fit_bounds([[visinfo['minY'], visinfo['minX']], [visinfo['maxY'], visinfo['maxX']]])
        #self.map.choropleth(geo_data='../out.geojson', fill_opacity=0.55, line_opacity=0.5, highlight=True, reset = True)
        #self.map.choropleth(geo_data='{}', fill_opacity=0.55, line_opacity=0.5, highlight=True, reset = True)
  
        # New folium does not allow creating map without data. So we need dummy
        # TODO: I think we can create map with jinja template directly, without creating dummy choropleth 
        dummy_data = '{"type":"FeatureCollection","features":[{"geometry":{"type":"Point","coordinates":[-76.9750541388,38.8410857803]},"type":"Feature"}]}'
        folium.Choropleth(geo_data=dummy_data, name="dummy").add_to(self.map)

        # # store geojson with jsonp wrap at temp location
        # os.system('rm -rf ' + HGUtil.WORK_DIR_LINK + '/vis_geojson.js')
        # # create soft link
        # os.system('ln -s ' + HGUtil.WORKING_DIR + "/job/" + jobid + "/results/vis_geojson.js " + HGUtil.WORK_DIR_LINK + '/vis_geojson.js')
        # now we send data via postmessage
        with open(HGUtil.WORKING_DIR + "/job/" + jobid + "/results/vis_geojson.js", 'r') as f:
            self.vis_geojson = f.read()[17:-2] # remove jsonp callback call

        geojsonKey = None
        for k,v in self.map._children.items():
            if str(k).startswith("choropleth"):
                geojsonKey = k

        geo = self.map._children.get(geojsonKey)
        # geo.dataUrl = HGUtil.NB_BASE_URL + '/vis_geojson.js'
        geo.idToValuesInDays = json.dumps(visinfo['idToValuesInDays'])
        geo.dateList = json.dumps(visinfo['dateList'])
        geo.highlight = True

        #  for hourly data
        if 'idToValuesInDaysTimes' not in visinfo:
            geo.idToValuesInDaysTimes = None
        else:
            if visinfo['idToValuesInDaysTimes'] is None:
                geo.idToValuesInDaysTimes = None
            else:
                geo.idToValuesInDaysTimes = json.dumps(visinfo['idToValuesInDaysTimes'])

        if 'dateTimeList' not in visinfo:
            geo.dateTimeList = None
        else:
            if visinfo['dateTimeList'] is None:
                geo.dateTimeList = None
            else:
                geo.dateTimeList = json.dumps(visinfo['dateTimeList'])

        geo.minMax = json.dumps(visinfo['minMax'])
        geo.subbasinList = json.dumps(visinfo['subbasinList'])
        geo.datatype = visinfo['datatype']
        geo.loadingCSS = self.loadingCSS

        temp = Template(self.hydroglobeJS)  # noqa
        geo._template = temp


        

            

    
    def display_vis_map(self):        
        html_map = self.map.get_root().render()
        html_b64 = base64.b64encode(html_map.encode('utf-8'))        
        display(Javascript('''
            $(function(){
                var map_vis = document.getElementById("iframe_map_vis");
                if(map_vis != null){
                    map_vis.src = "data:text/html;charset=utf-8;base64, %s";
                    // send Post Message
                    setTimeout(()=>{map_vis.contentWindow.postMessage(%s,'*');}, 1000);                    
                }
            });
        ''' % ( html_b64.decode(), self.vis_geojson  )))

    def show_init_loading(self):

        display(Javascript('''


        var sheet = window.document.styleSheets[0];
        sheet.insertRule(`
        .init_loading {
            position: absolute;
            margin: auto;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            width: 160px;
            height: 100px;
        }`, sheet.cssRules.length);

        sheet.insertRule(`
        .init_loading_loader {
          border: 5px solid #f3f3f3;
          -webkit-animation: spin 1s linear infinite;
          animation: spin 1s linear infinite;
          border-top: 5px solid #555;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          margin: auto;
          margin-top: 10px;
        }`, sheet.cssRules.length);



        sheet.insertRule(`
        /* Safari */
        @-webkit-keyframes spin {
          0% { -webkit-transform: rotate(0deg); }
          100% { -webkit-transform: rotate(360deg); }
        }`, sheet.cssRules.length);
        sheet.insertRule(`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }`, sheet.cssRules.length);

        var div_loading = document.createElement('div');
        div_loading.className = 'init_loading';
        div_loading.innerHTML = 'Loading HydroGlobe tool...';
        document.getElementsByTagName('body')[0].appendChild(div_loading);

        var loader = document.createElement('div');
        loader.className = 'init_loading_loader';
        div_loading.appendChild(loader);


        '''))

    def hide_init_loading(self):
        display(Javascript('''
            var div_loading = document.getElementsByClassName('init_loading')[0];
            div_loading.style.display = 'none';
        '''))

    def showVisTab(self, visibility = True):
        if visibility:
            display(Javascript('$("li.p-TabBar-tab:nth-child(3)").show();'))
        else:
            display(Javascript('$("li.p-TabBar-tab:nth-child(3)").hide();'))

    def showGPMRes(self, visible):
        self.lb_gpm_label.layout.display = 'none' if not visible else 'inline'
        self.dbox_gpm.layout.display = 'none' if not visible else 'inline'

    def hideEditAppBtn(self):
        display(Javascript('''
            $('#appmode-leave').remove();
        '''))
    
    def appMode(self):
        display(Javascript('''
            $('#toggle_codecells').click();
        '''))
        
