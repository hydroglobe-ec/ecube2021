import os, glob, pprint, subprocess
from HGUtil import HGUtil, HGLOG
from DBManager import DBManager
import time
import submitHydroglobe

_print = print
def print(*args, **kw):
    HGUtil.JOBLOG_FUNC(*args, **kw)
    # _print(*args, **kw)

class JobManager:

    db = DBManager()
    WORKING_DIR = HGUtil.WORKING_DIR
    INPUT_BASEDIR =  HGUtil.WORKING_DIR + "/upload/"
    JOB_BASEDIR =  HGUtil.WORKING_DIR + "/job/"
    params = {}

    print_joblog = None

    DEFAULT_WALTIME = 2880 #minute
    TOOL_REV = 'hydroglobetool_r361'


    #######################################
    # params: ['jobname','data_type', 'data_from', 'data_to', 'input_fname', 'working_dir']
    ################################################
    def __init__(self, params = None, func_joblog = None):
        if params == None and func_joblog == None: #job manage mode
            return

        self.params = params

        self.print_joblog = func_joblog

        # self.print_joblog("===== Job submission to halstead cluster =====")
        self.print_joblog("> JOB submission parameters : ")
        self.print_joblog(pprint.pformat(params))


    ###########################################################
    # job submission. Returns status(True,False), errormsg
    ###########################################################
    def submitJob(self):
        # get new job id form DB

        jobid = self.db.createNewJob()
        if jobid == None:
            return False, 'Job creation failure'

        #jobid = '1'
        # create job folders
        jobdir = self.JOB_BASEDIR + jobid
        HGUtil.rmdir(jobdir)
        HGUtil.mkdir(jobdir)

        # cd to job dir since 'submit' script returns job result here
        os.chdir(jobdir)

        waltime = self.DEFAULT_WALTIME

        HGUtil.mkdir('shape')
        upload_dir = self.INPUT_BASEDIR + self.params['input_fname'] + '/shape/'
        input_dir = self.JOB_BASEDIR + jobid + '/shape'

        # print('cp "' + upload_dir + '"* "' + input_dir + '".')
        os.system('cp "' + upload_dir + '"* "' + input_dir + '/".')

        shape_filename = str(os.path.basename(glob.glob(input_dir + '/*.shp')[0]))


        # update db
        params = {}
        params['jobname'] = self.params['jobname']
        params['fileName'] = self.params['input_fname']
        params['shapeName'] = shape_filename[:-4]
        if self.params['data_type'] == 'GPM':
            self.params['data_type'] = 'GPM (' + self.params['temporal_res'] + ')'

        params['dataType'] = self.params['data_type']

        params['dateFrom'] = self.params['data_from']
        params['dateTo'] = self.params['data_to']

        ret = self.db.updateJobInfo(jobid, params)


        # submit job
        jobcmd = 'submit -w ' + str(waltime) + \
            ' -v ssg-workq@halstead --detach' + \
            ' --inputfile ' + input_dir + \
            ' ' + self.TOOL_REV + \
            ' -r "' + self.params['data_type'] + '"'\
            ' -df ' + self.params['data_from'] + \
            ' -dt ' + self.params['data_to'] + \
            ' -f ' + shape_filename

        # self.print_joblog('\n> Job submission command : ')
        # self.print_joblog(jobcmd)

        # return True, ''

        submitHydroglobe.run(repo = self.params['data_type'], dateFrom = self.params['data_from']
        , dateTo = self.params['data_to'], shapeFileName = shape_filename, currentDir=jobdir)


        #return True, ''

        # get job submission id
        submit_id = '1234'        
        # self.print_joblog('\n> Job has been submitted successfully. Cluster job submission id : ' + submit_id)

        params = {}
        params['submitId'] = submit_id

        if len(glob.glob(HGUtil.WORKING_DIR + '/job/' + str(jobid) + '/results/*.csv')) > 0:
            params['jobstatus'] = 'Done'
        else:
            params['jobstatus'] = 'Failed'

        params['joblog'] = HGUtil.HG_INTERFACE.get_joblog()

        self.db.updateJobInfo(jobid, params)

        return True, ''


    def updateAllJobStatus(self):
        return

        job_list = self.db.getJobList()
        jobs_to_check = []
        for job in job_list:
            if job[8] in ['Pending', 'Queued', 'Running', 'Completing']:
                jobs_to_check.append(job)

        if len(jobs_to_check) == 0:
            return

        # get job status at one time
        trial = 2
        cmd = 'submit --status'
        while True:
            trial-=1
            new_job_status = {}
            ret = subprocess.check_output(cmd.split()).decode('utf-8')
            if ret != '':
                ret = ret.split('\n')[1:] # remove header
                for line in ret:
                    line = line.split() # ['00110637', '110637', '1', 'Running', 'ssg-workq@halstead']
                    if len(line) != 5:
                        continue

                    status = line[3]
                    if status in ['Registered', 'Submitted']:
                        status = 'Pending'
                    elif status == 'Complete':
                        status = 'Completing'
                    new_job_status[line[0]] = status

            if len(new_job_status) == len(jobs_to_check) or trial == 0:
                for job in jobs_to_check:
                    if job[1] not in new_job_status: # no status result => check if succeed
                        # print(job, new_job_status)
                        status = self.check_job_success(job[0], job[1])
                    self.db.updateJobStatus(job[0], status, job[1])
                break

            time.sleep(3)


    def getJobStatus(self, job_info): #[Registered, Submitted, Queued, Running, Completed ]
        return
        submit_id = job_info[1]
        jobid = job_info[0]
        cmd = 'submit --status ' + submit_id

        trial = 0
        while True: # status command sometimes returns nothing
            # print cmd
            ret = subprocess.check_output(cmd.split()).decode()
            ret = ret.split()
            # print ret

            if len(ret) > 5:
                break

            if trial > 2:
                return self.check_job_success(jobid, submit_id)

            trial += 1

        if ret[8] in ['Registered', 'Submitted']:
            return 'Pending'

        if ret[8] == 'Complete':
            return 'Completing'
            # print 'complete'
            # return self.check_job_success(jobid, submit_id)

        return ret[8]


    def check_job_success(self, jobid, submit_id):
        return
        # check stdout file
        files = glob.glob(HGUtil.WORKING_DIR + '/job/' + str(jobid) + '/*.stdout')
        if len(files) == 0:
            return 'Failed'

        stdout_filepath = files[0]

        with open(stdout_filepath, 'r') as f:
            data = f.read().split('\n')

        if len(data) > 2 and 'Cluster job is done' in data[-2]:
            if len(glob.glob(HGUtil.WORKING_DIR + '/job/' + str(jobid) + '/results/*.csv')) > 0:
                return 'Done'
            else:
                return 'Completing'

        return 'Failed'


    def deleteJob(self, jobid):
        #get submit id
        job_info = self.db.getJobInfo(jobid)
        if job_info == None:
            return
        
        # delete job files
        HGUtil.rmdir(self.JOB_BASEDIR + '/' + str(jobid))
        # delete job from DB
        self.db.deleteJob(jobid)
