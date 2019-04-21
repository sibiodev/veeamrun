#!/usr/bin/env python3

import argparse
import subprocess
from time import sleep
import logging
from logging.handlers import RotatingFileHandler
import platform
import re

import smtplib
from email.message import EmailMessage

VEEAM_RUN_PATTERN=r"Session ID: \[\{(.+)\}\]"
veeam_run_pattern = re.compile(VEEAM_RUN_PATTERN)

VEEAM_STATUS_PATTERN=r"State: (.+)"
veeam_status_pattern = re.compile(VEEAM_STATUS_PATTERN)

VEEAM_JOB_WAIT = 300

SMTP_SERVER = 127.0.0.1
SMTP_PORT = 25

if platform.system()=='Linux':
    IS_LINUX=True
    LOG='/var/log/veeamrun/veeamrun.log'
else:
    IS_LINUX=False
    VEEAMPS1 = r'C:\veeamrun\run.ps1'
    LOG = r'C:\veeamrun\veeamrun.log'

log = logging.getLogger('veeamrun')
log.setLevel(logging.DEBUG)
handler = RotatingFileHandler(LOG, maxBytes=1000000, backupCount=10)
handler.setFormatter( logging.Formatter(fmt='%(asctime)s %(message)s',
                                    datefmt='%Y-%m-%d %I:%M:%S %p') )
log.addHandler(handler)

class VeeamRunException(Exception):
    pass

def find_job_id(output):
    match=veeam_run_pattern.search(output)
    if match:
        job_id = match.groups()[0]
        log.info('Found job ID: {}'.format(job_id))
        return job_id
    else:
        log.error('Could not find job ID in the output : {}'.format(output))
        raise VeeamRunException('Could not find job ID in the output : {}'.format(output))

def get_job_status(job_id):
    command = subprocess.Popen(['veeamconfig','session','info','--id',job_id],stdout=subprocess.PIPE)
    output, error = command.communicate()
    match = veeam_status_pattern.search(output.decode('utf8'))
    if match:
        status = match.groups()[0]
        log.info('Job ID {} status is {}'.format(job_id,status))
        return status
    else:
        log.warning('Could not find job ID {} status in output {}'.format(job_id,output))
        return 'Unknown'

def run_veeam(jobname):
    log.info('launch job {}'.format(jobname))
    if IS_LINUX:
        log.debug('... we are under linux')
        veeam = subprocess.Popen(['veeamconfig','job','start','--name',jobname],stdout=subprocess.PIPE)
        output, error = veeam.communicate()
        log.info('Job {} launched'.format(jobname))
        job_id = find_job_id(output.decode('utf8'))
        status = get_job_status(job_id)
        while status=='Running':
            log.info('Job {} is running, waiting {}s'.format(jobname,VEEAM_JOB_WAIT))
            sleep(VEEAM_JOB_WAIT)
            status = get_job_status(job_id)
        if status=='Failed':
            job_status = False
        else:
            job_status = True
    else:
        log.debug('... we are under windows (or we assume to be)')
        if jobname == 'VEEAM':
            log.info('this is a Configuration Backup')
            ps_script = open(VEEAMPS1,'w+')
            ps_script.write('Add-PsSnapin -Name VeeamPSSnapIn\r\nStart-VBRConfigurationBackupJob\r\n')
            ps_script.close()
            veeam = subprocess.Popen(['powershell','-command', "&", "{&'Add-PsSnapin' -Name VeeamPSSnapIn}", ';', "&",
                                      "{&'Start-VBRConfigurationBackupJob'}"])   
        else:
            veeam = subprocess.Popen([r"C:\Program Files\Veeam\Endpoint Backup\Veeam.EndPoint.Manager.exe",'/backup'])
        answer = veeam.wait()
        log.info('job {} finished with answer code {}'.format(jobname,answer))
        if answer!=0:
            job_status = False
        else:
            job_status = True
    
    if job_status:
        log.info('Job was successful')
    else:
        log.error('Job failed...')
    
    return job_status

def mail_zabbix(hostname,jobname,status):
    if status:
        status_msg='Success'
    else:
        status_msg='Failed'
    msg = EmailMessage()
    msg.set_content("""Job {} on host {} has terminated with status {}.
""".format(jobname,hostname,status_msg))

    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = '[{}] {} (standalone agent)'.format(status_msg,jobname)
    msg['From'] = 'veeamrun@sibio.fr'
    msg['To'] = '{}@supervision.sibio.fr'.format(hostname)

    # Send the message via our own SMTP server.
    s = smtplib.SMTP(SMTP_SERVER,port=SMTP_PORT)
    s.send_message(msg)
    s.quit()
        

def run():
    log.info('Starting')
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname", help="Hostname for Zabbix reporting")
    parser.add_argument("jobname", help="VEEAM job name")
    args = parser.parse_args()
    jobname = args.jobname
    hostname = args.hostname

    
    
    log.debug('...got jobname {}'.format(jobname))
    
    if run_veeam(jobname):
        mail_zabbix(hostname,jobname,status=True)
    else:
        mail_zabbix(hostname,jobname,status=False)

if __name__=='__main__':
    run()



