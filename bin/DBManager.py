from HGUtil import HGUtil, HGLOG
import json
import sqlite3
import requests
import os, datetime

class DBManager:
    DB_FILE = HGUtil.WORKING_DIR + '/job/job.db'

    def __init__(self):
        # check if db file exists
        if not os.path.isfile(self.DB_FILE):
            self.initTable()

        # check if a user uses old db
        conn = sqlite3.connect(self.DB_FILE)
        sql = 'PRAGMA table_info(HGJobs);'
        cur = conn.execute(sql)
        ret = cur.fetchall()
        for col in ret:
            if col[1] == 'jobname':
                return

        # no jobname
        sql = 'alter table HGJobs add column jobname TEXT'
        cur = conn.execute(sql)
        conn.close()



    def initTable(self):
        sql = '''
        CREATE TABLE HGJobs (
            jobid INTEGER PRIMARY KEY AUTOINCREMENT,
            submitId TEXT,
            fileName TEXT,
            shapeName TEXT,
            dataType TEXT,
            dateFrom TEXT,
            dateTo TEXT,
            submitTime TEXT,
            jobstatus TEXT,
            jobname TEXT,
            joblog TEXT
        );
        '''

        #create job folder first
        HGUtil.mkdir(HGUtil.WORKING_DIR)
        HGUtil.mkdir(HGUtil.WORKING_DIR + '/job')

        conn = sqlite3.connect(self.DB_FILE)
        conn.execute(sql)
        conn.close()


    def createNewJob(self):
        now = datetime.datetime.now()
        submit_time = now.strftime('%m/%d/%Y %H:%M')

        conn = sqlite3.connect(self.DB_FILE)
        sql = 'insert into HGJobs(submitTime,jobstatus) values (?,?);'
        conn.execute(sql, (submit_time ,'None'))
        conn.commit()

        sql = 'select jobid from HGJobs order by jobid desc limit 1;'
        cur = conn.execute(sql)
        jobid = cur.fetchone()[0]

        conn.close()

        return str(jobid)

    def updateJobInfo(self, jobid, params):

        sql = 'update HGJobs set '
        for key in params:
            params[key] = params[key].replace('"','\'')
            sql += key + ' = "' + params[key]  + '",'

        sql = sql[:-1] + ' where jobid = "'+ jobid +'";'

        conn = sqlite3.connect(self.DB_FILE)
        conn.execute(sql)
        conn.commit()
        conn.close()

        return True

    def updateJobStatus(self, jobid, status, submit_id):
        sql = 'update HGJobs set jobstatus = "%s" where jobid = "%s";' % (status, str(jobid))

        conn = sqlite3.connect(self.DB_FILE)
        conn.execute(sql)
        conn.commit()
        conn.close()
        param = {}
        param['submitId'] = submit_id
        HGUtil.sendLog(HGLOG.JOB_STATUS, param, status)

        return True
    
    def updateJobLog(self, jobid, log):
        sql = 'update HGJobs set joblog = "%s" where jobid = "%s";' % (log, str(jobid))

        conn = sqlite3.connect(self.DB_FILE)
        conn.execute(sql)
        conn.commit()
        conn.close()

        return True


    def deleteJob(self, jobid):
        conn = sqlite3.connect(self.DB_FILE)
        sql = 'delete from HGJobs where jobid = "' + str(jobid) + '"'
        conn.execute(sql)
        conn.commit()
        conn.close()

        return True

    def getJobList(self):
        conn = sqlite3.connect(self.DB_FILE)
        sql = 'select * from HGJobs order by jobid desc;'
        cur = conn.execute(sql)
        return cur.fetchall()

    def getJobInfo(self, jobid):
        conn = sqlite3.connect(self.DB_FILE)
        sql = 'select * from HGJobs where jobid = "%s";' % str(jobid)
        #print sql
        cur = conn.execute(sql)
        return cur.fetchone()



""" #component

    def createNewJob(self):
        r = requests.get(HGUtil.HG_COMPONENT_URL + 'createNewJob')
        if r.status_code != 200:
            return None

        return r.text

    def updateJobInfo(self, jobid, params):
        data = {}
        data['jobid'] = jobid
        data['params'] = json.dumps(params)
        print data
        r = request.post(HGUtil.HG_COMPONENT_URL + 'createNewJob', data)

        if r.status_code != 200:
            return False

        return True

    def deleteJob(self, jobid):
        data = {'jobid':jobid}
        r = request.post(HGUtil.HG_COMPONENT_URL + 'deleteJob', data)

        if r.status_code != 200:
            return False

        return True

    def getJobList(self):
        r = requests.get(HGUtil.HG_COMPONENT_URL + 'getJobList')
        if r.status_code != 200:
            return None

        return r.json()

"""
