from relay_post_GUI_20230714 import HTTP_message, Wifi_connect
from final_v28 import call_main, prelim_process, get_error_display, sysbreak_event, exitfunct, list_of_logs
import threading
import json
import time
import logging
import os
import re
json_file_path = "setup_20230714.json"

'''
Declaring the global parameters used throughout the code:
sysbreak    :   Used to stop all the processing of code when 'True'. Used in UI, when cross button is clicked, sysbreak is called.
process_UI  :   Contains the milestones of the processes that are either started or completed based on the 'process.txt' file
count       :   Used to store the name of the folder used for saving all the files for this session. Set using time.asctime and in the format of
                _Month Date Time(hh:mm:ss) Year.  Example: _Apr  1 09_38_13 2023
f           :   Temporary variable to store the instance of 'setup.json' file which is opened to get the below items
data        :   Temporary variable to store the dictionary in the json file
name        :   Name of the Wifi to be connected to send the relay and mpu commands.
password    :   Password of the Wifi to be connected to send the relay and mpu commands.
PATH        :   Path of the folder where the storage saving folders will be created
logpath     :   The path of the Log files that stores the entire process of the code.
'''

sysbreak = False
processes_UI = ''
count = ''
timeout_time = None
f = open(json_file_path, 'r')
data_setup=json.loads(f.read())
PATH = data_setup['PATH']
name = data_setup['name']
password = data_setup['password']
timeout_time = data_setup['time_to_run']
f.close()

g = open('process.txt', 'r')
data_process = g.read()
inst = [int(num) for num in re.findall('delay.([\d]*).', data_process)]
timeout_time += sum(inst)
g.close()

text_obj = ''
logpath = ''

def write_logs(str_):
    str_ = str(str_)
    global list_of_logs 
    logging.basicConfig(filename=logpath,
            filemode='a',
            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt='%H:%M:%S',
            level=logging.DEBUG)
    logging.info(str_)
    list_of_logs.append(str_)

def mainfunc(DOE):
    '''
    Main function that runs the entire process. Starts once the UI calls the function via the 'Start' button click. It runs till all the 
    process in the file are followed or sysbreak is set to True.
    It does multiple things:
        1) Creates the instance folder with 'count' where the session files will be stored and saved.
        2) Connects to the Wi-Fi with which the relay and mpu commands are sent.
        3) Opens/Creates the log file to record the entire process
        4) Starts the process according to the 'logpath.txt' and starts executing all the commands using either eval() or calling them.
        5) Updates process_UI which contains all the milestones to be shown in the UI.
    Uses some global variables:
    => processes_UI, count, sysbreak, logpath

    Raises
    ------
    An error which is recorded in the Logs file and continues ahead.
    '''
    try:
        global processes_UI, count, sysbreak, text_obj, logpath, data_process
        savepath, logpath = create_folders(name = DOE)
        start = time.time()
        write_logs('Starting the processes')

        processes_UI += "At time 0, processes starting!!\n"
        # HTTP_message("IITB_IOT","IITB_IOT", "iitbiot1234")
        # delay(3)
        prelim_process(sp =savepath, lp = logpath)
        collect_audio = None
        processes_in_list = data_process.split('\n')
        for step in processes_in_list:
            if 'call_main(' in step:
                if "True" in step:
                    collect_audio = True
                else:
                    collect_audio = False
        thread1 = threading.Thread(target=call_main, args=(collect_audio, ), daemon=True)
        thread2 = threading.Thread(target=sysbreak_exit, daemon=True)
        thread2.start()
        write_logs(processes_in_list)
        for step in processes_in_list:
            if sysbreak:
                processes_UI += "At time " + str(time.time() - start) + " system wide exit called!\n"
                break
            # step = step.split('\n')[0]
            # write_logs(step)
            processes_UI += "At time " + str(time.time() - start) + " " + str(step)+ " called!\n"
            if ("call_main(" in step):
                    write_logs("Independent call_main() thread started")
                    thread1.start()
            else:
                eval(step)
                processes_UI += "At time " + str(time.time() - start) + " " + str(step)+ " completed!\n"
        if thread1.is_alive():
            thread1.join()
        processes_UI += "At time " + str(time.time() - start) + " " + "call_main() thread joined!\n"
        if thread2.is_alive():
            thread2.join()
        write_logs("From mainv: Threads joined!")
        if sysbreak==False:
            write_logs("Here at the end, all processes complete")
            text_obj = f"Files stored in {savepath}"
        else:
            write_logs("Error occured during execution of mainfunc() in mainv, one or more processes may have failed!!")
    except Exception as e:
        text_obj = "In mainv file's mainfunc(), error: " + str(e)


def print_logs():
    '''
    Function to display the process_UI variable on the UI. Called when 'Logs' button in the UI is clicked.
    '''
    return processes_UI, text_obj


def sysbreak_exit():
    global text_obj, processes_UI, sysbreak
    sysbreak_event.wait(timeout= float(timeout_time + 2))
    text_obj = get_error_display()
    if text_obj != 'NO ERROR Encountered!':
        sysbreak = True
        processes_UI += "Error Encountered, System Exit!! \n"


def delay(step):
    '''
    Simple Delay function. Logs the current time and the amount of time to sleep. Then after time.sleep, again logs the time.

    Parameter(s):
    step  :  Amount of time to sleep.
    '''
    try:
        step_ = 0.1
        write_logs(f"Delay of {step} seconds!")
        while step - step_ >= 0:
            if sysbreak == False:
                time.sleep(step_)
                step = step - step_
            else:
                break
    except Exception as e:
        write_logs(f"Error in delay() from mainv() \n" + str(e))
        exitfunct(f"Error in delay() from mainv()" + str(e))

def create_folders(name):
    try:
        count = str(time.asctime()[4:]).replace(":", "_")
        filecount = str(name) + ' ' + str(count)
        savepath = os.path.join(PATH, filecount)
        os.makedirs(savepath)
        logpath = os.path.join(savepath,"logs.txt")
        return savepath, logpath
    except Exception as e:
        write_logs(f"Error in create_folders() from mainv() \n" + str(e))
        exitfunct(f"Error in create_folders() from mainv()" + str(e))