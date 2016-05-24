import argparse
import time
import sys
import os


from subprocess import Popen
from subprocess import PIPE


'''
This code file was developed originally  by Randy Yang.
Abel Guzman is supposed to make it work with his help
and make improvements in:
-Coding standards
-Decopling code
-Bug fixes
-Binary independence.
-Command independence from script (Exclude)
-bing log not active should not make backup fiale, just warn.
'''

class mydump:
    def __init__(self):
        self.args_list = self.__get_parameters()
        if self.args_list.PREFIX_FOLDER:
            self.script_prefix = self.args_list.PREFIX_FOLDER
        else:
            self.script_prefix = "mydump"
        if self.args_list.MYSQL_DUMP_BINARY:
            self.mysql_dump_binary = self.args_list.MYSQL_DUMP_BINARY
        else:
            self.mysql_dump_binary = "/usr/bin/mysqldump"
        if self.args_list.MYSQL_BINARY:
            self.MYSQL = self.args_list.MYSQL_BINARY
        else:
            self.MYSQL = "/usr/bin/mysql"
        self.DESTINATION = self.args_list.DESTINATION + '/'+self.script_prefix
        self.PREFIX_BACKUP = time.strftime('%Y%m%d',time.localtime(time.time())) + "_"+self.args_list.HOSTNAME
        if self.DESTINATION:
            sys.path.append(self.args_list.HOME_FOLDER)
            # from compression.zip_compression import ZipCompression
            from execution.subprocess_execution import SubprocessExecution
            if not os.path.isdir(self.DESTINATION):
                create_dir_cmd = 'mkdir ' + self.DESTINATION
                execution_mkdir = SubprocessExecution.main_execution_function(SubprocessExecution(), create_dir_cmd, True)
                if execution_mkdir[0] != 0:
                    print 'Could Not create directory with command: ' + create_dir_cmd
                    print 'Error code: ' + str(execution_mkdir[0])

    def __get_parameters(self):
        parser_object = argparse.ArgumentParser()
        parser_object.add_argument('--HOSTNAME', type=str, help='Hostname', required=True,action="store")
        parser_object.add_argument('-H', '--HOME_FOLDER', type=str
                                   , help='Script home folder required(from where the master script runs)',
                                   required=True)
        parser_object.add_argument('--DESTINATION', type=str, help='Local backup folder', required=True,action="store")
        parser_object.add_argument('--CONF_PATH', type=str, help='Configuration file path',
                                   required=True,action="store")
        parser_object.add_argument('--CREDENTIAL_PATH', type=str, help='Credential file path',
                                   required=True,action="store")
        parser_object.add_argument('--DATA_DIR', type=str, help='Data dir path', required=True,action="store")
        parser_object.add_argument('--MY_INSTANCES', type=str, help='Instance port', required=True,action="store")
        parser_object.add_argument('--LOG', type=str, help='Log path', required=True,action="store")
        parser_object.add_argument('--BINLOG_PATH', type=str, help='Bin Log folder', required=True, action="store")
        parser_object.add_argument('--BINLOG_FILE_PREFIX', type=str, help='Bin Log file prefix',
                                   required=True, action='store')
        parser_object.add_argument('--MYSQL_DUMP_BINARY',type=str, help='MySQL Dump Binarey',  required=False)
        parser_object.add_argument('--MYSQL_BINARY', type=str, help='MySQL Binarey', required=False)
        parser_object.add_argument('--PREFIX_FOLDER', type=str, help='Prefix or folder to use', required=False)
        args_list, unknown = parser_object.parse_known_args()
        return args_list

    def get_instanceinfo(self,MY_INSTANCE_NAME):
        if MY_INSTANCE_NAME=="3306":
            credential_file=self.args_list.CREDENTIAL_PATH[0]
            MYSQL_DATA_DIR=self.args_list.DATA_DIR[0]
            print "---- MySQL Instance Data Dir: "+MYSQL_DATA_DIR+" ----"
            mysql_dump_and_credentials="sudo mysqldump --defaults-extra-file="+credential_file
            mysql_and_credentials = "sudo mysql --defaults-extra-file="+credential_file
        else:
            credential_file=self.args_list.CREDENTIAL_PATH[1]
            MYSQL_DATA_DIR=self.args_list.DATA_DIR[1]
            print "---- MySQL Instance Data Dir: "+MYSQL_DATA_DIR+" ----"
            mysql_dump_and_credentials="sudo mysqldump --defaults-extra-file="+credential_file
            mysql_and_credentials = "sudo mysql --defaults-extra-file=" + credential_file
        return MYSQL_DATA_DIR,mysql_dump_and_credentials, mysql_and_credentials

    def log_rotate(self,mysql_and_credentials):
        _SQL1="flush logs; SHOW MASTER STATUS; SHOW SLAVE STATUS \G "
        command2=mysql_and_credentials + " -e '"+_SQL1+"' >/dev/null"
        print command2
        rotate_stdout,rotate_stderr=Popen(command2, shell=True, stdout=PIPE, stderr=PIPE).communicate()
        # print rotate_stdout,rotate_stderr
        return rotate_stdout,rotate_stderr

    def run_backup(self,mysql_and_credentials, mysql_dump_and_credentials, DESTINATION, PREFIX, script_prefix,
                   MY_INSTANCE_NAME):
        command1=mysql_and_credentials + " -e 'show databases' | sed '/Database/d' | grep -v 'information_schema' " \
                                         "| grep -v 'performance_schema'"
        stdout, stderr = Popen(command1, shell=True, stdout=PIPE, stderr=PIPE).communicate()
        for DB_NAME in stdout.split('\n')[:-1]:
            _SQL2="\"USE information_schema; SELECT TABLE_NAME FROM TABLES WHERE TABLE_SCHEMA='" + \
                  DB_NAME + "' AND TABLE_TYPE= 'BASE TABLE' AND ENGINE NOT like 'innodb';\""
            command3=mysql_dump_and_credentials+" --opt --routines --triggers --events --flush-privileges " \
                                         "--skip-add-drop-table --master-data=2 --dump-date --databases " + \
                     DB_NAME + "|sudo gzip > " + DESTINATION + "/" + PREFIX + "_" + script_prefix + \
                     "_" + MY_INSTANCE_NAME + "_" + DB_NAME+".sql.gz"
            command4=mysql_dump_and_credentials+" --opt --routines --triggers --events --flush-privileges " \
                                                "--skip-add-drop-table --master-data=2 --single-transaction  " \
                                                "--skip-add-locks --skip-lock-tables --dump-date --databases "\
                     + DB_NAME + " | sudo gzip > " + DESTINATION + "/" + PREFIX + "_" + script_prefix + "_" + \
                     MY_INSTANCE_NAME + "_" + DB_NAME + ".sql.gz"
            print "---- Backing up Instance: "+MY_INSTANCE_NAME+" Database : "+DB_NAME+" ---- "
            command5=mysql_and_credentials + " -e "+_SQL2+"|grep -v TABLE|wc -l"
            stdout2, stderr = Popen(command5, shell=True, stdout=PIPE, stderr=PIPE).communicate()
            if stdout2!=0:
                print "---- "+DB_NAME+" has MYISAM TABLES , using DUMP backup method ---- "
                backup_stdout,backup_stderr=Popen(command3, shell=True,stdout=PIPE, stderr=PIPE).communicate()
            else:
                print "---- "+DB_NAME+" has all InnoDB tables , using InnoDB backup method ---- "
                backup_stdout,backup_stderr=Popen(command4, shell=True,stdout=PIPE, stderr=PIPE).communicate()
        print "---- Backup Done ---- "
        return backup_stdout,backup_stderr

    def backup_logs(self,MYSQL_DATA_DIR,DESTINATION, script_prefix, MY_INSTANCE_NAME,
                    BINLOG_PATH='/var/lib/mysql/data', BINLOG_FILE_PREFIX='mysql-bin'):
        j=""
        command6="ls -l "+MYSQL_DATA_DIR+"| grep 'mysql-bin' | awk '{ print $NF }'"

        if BINLOG_PATH[-1] != '/':
            print 'The path to the folder needs to end in /'
            BINLOG_PATH = BINLOG_PATH + '/'
        stdout6, stderr6 = Popen(command6, shell=True, stdout=PIPE, stderr=PIPE).communicate()
        for i in stdout6.split('\n')[:-1]:
            j=j+" "+MYSQL_DATA_DIR+i
        command7="sudo /usr/local/Cellar/gnu-tar/1.28/bin/tar czf " + str(DESTINATION) + "/" + str(script_prefix) \
                 + "_" + str(MY_INSTANCE_NAME) +".bin-log.gz " + BINLOG_PATH + '/' + BINLOG_FILE_PREFIX + '.*'
        print command7
        logbak_stdout,logbak_stderr=Popen(command7, shell=True, stdout=PIPE, stderr=PIPE).communicate()

        return logbak_stdout,logbak_stderr


def main():

    saveout = sys.stdout
    mydump_object=mydump()
    sys.out=mydump_object.args_list.LOG

    for MY_INSTANCE_NAME in mydump_object.args_list.MY_INSTANCES.split(','):

        print "---- Processing instance: "+MY_INSTANCE_NAME+" ----"

        MYSQL_DATA_DIR,mysql_dump_and_credentials,mysql_and_credentials=mydump_object.get_instanceinfo(MY_INSTANCE_NAME)

        rotate_stdout,rotate_stderr=mydump_object.log_rotate(mysql_and_credentials)
        print rotate_stdout
        print rotate_stderr
        backup_stdout,backup_stderr=mydump_object.run_backup(mysql_and_credentials,mysql_dump_and_credentials,
                                                             mydump_object.DESTINATION,mydump_object.PREFIX_BACKUP,
                                                             mydump_object.script_prefix,MY_INSTANCE_NAME)
        print backup_stdout
        print backup_stderr
        # print mydump_object.args_list.BINLOG_PATH + 'AAAAA'
        logbak_stdout,logbak_stderr=mydump_object.backup_logs(MYSQL_DATA_DIR,mydump_object.DESTINATION,
                                                              mydump_object.script_prefix,
                                                              MY_INSTANCE_NAME,
                                                              mydump_object.args_list.BINLOG_PATH,
                                                              mydump_object.args_list.BINLOG_FILE_PREFIX)
        print logbak_stdout
        print logbak_stderr
    sys.stdout=saveout



if __name__ == "__main__":
    main()