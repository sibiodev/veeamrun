# VeeamRUN

This little script can be used to run a job for a free agent. It can send an email to an SMTP server (please modify the constants within the script).

It can be used together with zbxsmtptotrap (https://github.com/sibiodev/zbxsmtptrap) for integration within Zabbix.

You may also use it without Zabbix simply to receive a positive or negative email for each run of a Free Agent (without a Veeam server).

## Install

### On Windows
On windows, create a `C:\veeamrun` directory, install the script inside. Install python.

Install Python3.

Create a scheduled task, running the script with the hostname and the name of the job as arguments.

### On Linux
On Linux, install the script in /usr/local/bin/, create /var/log/veeamrun, and create a cron job with the script and two arguments (try ./veeamrun.py --help): hostname and job name.

 
