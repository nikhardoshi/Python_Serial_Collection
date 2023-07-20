import time 
import os
import numpy as np   # 1.23.0
import serial    # 3.5
import struct  
import serial.tools.list_ports
import threading
from threading import Event
import pandas as pd  # 1.4.3
import polars as pl 
pl.Config.set_ascii_tables(True)  
import concurrent.futures
import statistics
import sounddevice as sd
from scipy.io.wavfile import write
import glob
import queue
import json
import logging

'''
Declaring the Global Parameters used throughout the code!
PORT                    :  The list of COM Ports connected to the system.
port_identity           :  The characteristic of the each COM port: Name, Header (Sync Byte), Data Format, Description.
myrecording             :  Stores the audio data of a single batch, later on used for storing in CSV and audio file!
audioevent              :  Aids in Audio Recording and Saving. Once it is set, which means recording of a single batch is done, and only then the writing/saving of that batch starts.
BAUD_RATE               :  Baud_rate set in the ESP32.
HEADER                  :  Used to store the HEADER byte set in ESP32.
DATAFMT                 :  List of sizes of data streamed by the ESP32.
time_to_run             :  The overall running time of the program.
fs                      :  Sampling rate.
batch_duration          :  Used when recording Audio. The time for overall batch size recording.
sysbreak                :  Used to stop all the processing of code when 'True'. Used in UI, when cross button is clicked, sysbreak is called.
readobjects             :  Contains list of all the 'ReadLine' class' objects. 
count                   :  Used for counting and serializing the CSV batch files of Audio. 
collection_process_done :  A flag, to denote if the data collection process is done or not.
savepath                :  The name of the COM port like 'COM3'. Used for saving files of each port uniquely!
logpath                 :  The path of the Log files that stores the entire process of the code.
port_timeout            :  Max Waiting time required when joining all the port data threads.
audio_timeout           :  Max Waiting time required when joining all the audio threads.
findport_delay          :  The amount of time that a loop in the function 'findport' should run. Purpose explained in that function.
'''

PORT=[] 
PATH2 = ''                       
port_identity = []             
myrecording = []               
audioevent=Event()             
BAUD_RATE = 0                  
HEADER = bytes()               
DATAFMT = []                   
time_to_run = 0.0              
fs = 0                                
sysbreak=False                 
readobjects = []               
count=0                        
collection_process_done = False
savepath = ''              
logpath = ''             
port_timeout=0                 
audio_timeout=0                
findport_delay=0
err_message = 'NO ERROR Encountered!'    
sysbreak_event = Event()
time_worker = None
list_of_logs = []


def setenvvars():
    '''
    Sets the global parameters according to the values given in the file 'setup.json'. 
    The data can be altered by the user accordingly.
    Uses various global variables
    => PATH, BAUD_RATE, HEADER, DATAFMT, time_to_run, fs, N, count, sysbreak, batch_duration, audio_timeout, port_timeout, findport_delay
    '''
    try:
        global BAUD_RATE, HEADER, DATAFMT, time_to_run, fs, N, PATH2, sysbreak, count, audio_timeout, port_timeout, findport_delay
        f = open('setup_20230714.json', 'r')
        data=json.loads(f.read())
        BAUD_RATE = data['BAUD_RATE'] 
        HEADER = int(data['HEADER'],16).to_bytes(1,"big")
        DATAFMT = data['DATAFMT']
        time_to_run = data['time_to_run']
        fs = data['fs']
        PATH2 = data['PATH2']
        audio_timeout = data['audio_timeout']
        port_timeout = data['port_timeout']
        findport_delay = data['findport_delay']
        sysbreak = bool(data['sysbreak'])
    except Exception as e:
        write_logs("Error in setevars() \n" + str(e))
        exitfunct("Error in setevars()" + str(e))

def findport(rl):
    '''
    Preliminary function that runs before the actual data collection process starts. 
    The purpose is that once all the COM ports are detected and stored in the list PORTS, here they are run for 'findport_delay' time which is set by the user.
    This way which port is sending what channels and type of data can be recognized and stored with the rest of the details in 'port_identity' variable.
    The data stream is discarded. 
    This step is necessary as it guarantees the Data Format sent by each port connected to the device. Uses the global variable
    => port_identity

    Parameter(s)
    -----------
    rl : Readline object of a particular port

    Raises
    ------
    An error which is recorded in the Logs file and continues ahead.
    '''
    try:
        global port_identity, sysbreak
        
        rl.s.reset_input_buffer()
        iters=0
        syncpos=[]
        desc=''
        buf=bytearray()
        for activeport in PORT:
            if activeport[0]==rl.s.name:
                desc=activeport[1]
                break
        starting=time.monotonic()
        ending=0.0  
        write_logs(f"{rl.s.name} entering the while loop in findport, starting at {time.asctime()[11:-5]}")  
        while(ending-starting<=findport_delay):
            if sysbreak:
                break
            i = buf.find(HEADER)
            if i >= 0:
                buf = buf[i + 1:]
                syncpos.append(i)
                iters+=1
            else:    
                while True:
                    ext = rl.s.read(250)
                    i = ext.find(HEADER)
                    count = 0
                    if count%100 == 0 & count!=0:
                        if  (time.monotonic() - starting )>= (findport_delay + 0.1):
                            raise Exception("Unable to find sync byte!!")
                        else:
                            write_logs(f"From Findport: Trying to Finding SyncByte {count}th time")
                    if i >= 0:
                        buf = ext[i + 1:]
                        syncpos.append(i)
                        iters+=1
                        break
                    else:
                        buf += ext
                        count += 1
            ending=time.monotonic()
        if sysbreak:
            return None
        syncbyte_position = statistics.mode(syncpos)
        freq = int(iters/findport_delay)

        if freq<=1_500:
            rl.N = 5000
        elif freq<=30_000:
            rl.N == 90_000
        else:
            rl.N = 1_20_000
        
        port_identity.append({"Port": rl.s.name,"Header": HEADER, "DATAFMT": syncbyte_position, "Description": desc, 'Frequency' : freq, 'Batch_Size' : rl.N})
        
        sensor_identification(rl,syncbyte_position)
        write_logs(f"{rl.s.name} Dataformat: {syncbyte_position} Iterations: {iters} Frequency: {freq} Sensor ID: {str(rl.sensor_id)} samples_per_batch: {rl.N}")

    except Exception as e:
        write_logs(f"Error in findport() for {rl.s.name} \n" + str(e))
        exitfunct(f"Error in findport() for {rl.s.name}" + str(e))


def sensor_identification(rl,syncbyte_position):
    try:    
        data = []
        for _ in range(100):
            data.append(rl.readline())
        write_logs("Finding the sensor format")
        df = parsedata(data, rl)
        if syncbyte_position == 8:
            write_logs(f"{rl.s.name} is: 2 channel data")
            if df.shape[1]==2:
                mode = df[df.columns[-1]].mode()[0]
                if mode==-100:
                    rl.sensor_id = 'PRS'
                elif mode==-1000:
                    rl.sensor_id = 'WTF'
                else:
                    raise Exception(f"Data seems to be of unknown format {rl.s.name} and synbyte_position is {syncbyte_position}") 
            else: 
                raise Exception(f"Data seems to be of unknown format {rl.s.name} and synbyte_position is {syncbyte_position}")

        elif syncbyte_position == 6:
            write_logs(f"{rl.s.name} is: 3 channel data")
            if df.shape[1]==3:
                mean = df[df.columns[-1]].mean()
                if mean > 500 and mean<1500:
                    rl.sensor_id = 'ACC'
                elif mean> 5000:
                    rl.sensor_id = 'GYR'
                else:
                    raise Exception(f"Data seems to be of unknown format {rl.s.name} and synbyte_position is {syncbyte_position}")
            else: 
                raise Exception(f"Data seems to be of unknown format {rl.s.name} and synbyte_position is {syncbyte_position}")


        elif syncbyte_position == 4:
            write_logs(f"{rl.s.name} is: 2 channel data")
            mean = df[df.columns[0]].mean()
            if mean < 5000:
                rl.sensor_id = 'CV1'
            elif mean < 10000:
                rl.sensor_id = 'VRY'
            else: 
                raise Exception(f"Data seems to be of unknown format {rl.s.name} and synbyte_position is {syncbyte_position}")
                
        elif syncbyte_position == 2:
            write_logs(f"{rl.s.name} is 1 channel data")
            mean = df[df.columns[0]].mean()
            if mean < 5000 and mean>=0:
                rl.sensor_id = 'SMG'
            elif mean < 10000 and mean>=5000:
                rl.sensor_id = 'CTR'
            elif mean < 15000 and mean>=10000:
                rl.sensor_id = 'CTY'
            elif mean < 20000 and mean>=15000:
                rl.sensor_id = 'CTB'
            else: 
                raise Exception(f"Data seems to be of unknown format {rl.s.name} and synbyte_position is {syncbyte_position}")
        else: 
                raise Exception(f"Data seems to be of unknown format {rl.s.name} and synbyte_position is {syncbyte_position}")
    except Exception as e:
        write_logs(f"Error sensor_identification() for {rl.s.name} \n" + str(e))
        exitfunct(f"Error sensor_identification() for {rl.s.name}" + str(e))

def sensor_desc_dumps():
    try:
        global readobjects, port_identity
        fpath = os.path.join(savepath,'Sensor_Description.json')
        sensor_desc = {}
        for rl in readobjects:
            for dict_ in port_identity:
                if dict_['Port'] == rl.s.name:
                    dict_['Header'] = str(dict_['Header'])
                    sensor_desc[rl.sensor_id] = dict_
        with open(fpath, 'w') as f:
            # f.write(str(sensor_desc))
            json.dump(sensor_desc,f)
        write_logs(f"Sensor Description .json dumped at {sensor_desc}")
    except Exception as e:
        write_logs(f"Error sensor_desc_dumps() \n" + str(e))
        exitfunct(f"Error sensor_desc_dumps()" + str(e))        


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



class ReadLine:
    '''
    Main class that helps in Data collection process of each COM Port.

    Attributes
    ----------
    s                     :  Data Stream from the ESP32
    buf                   :  Buffer array which stores one row of data from the data stream
    length                :  Used to store the Data format of the respected COM ports (DATAFMT)
    q                     :  Required for storing timestamp in a Queue for respective COM port
    port_data_collection  :  Flag to represent if the data collection of that port is complete or not
    sync_loss_count                 :  Used to denote the number of time the Header (SYNC Byte) is lost in the data collection process
    log                   :  Used to serialize the batch files that are stored of a specific port
    state                 :  Used to describe the batch of data being recorded. Used to enable concurrent writing/reading by using multiple lists/arrays/dataframes in the state space.
    StateEvent            :  Aids in Data Recording and Saving. Once it is set, which means recording of a single batch is done, and only then the writing/saving of that batch starts.
    N                     :  No of points to be recorded in one batch

    Methods
    -------
    readline()  :   Records the data of a particular port in a batch. If first time, it sets the length of the data (self.length).
                    It then checks the length of the buffer array (self.buf) and refills it if required.
                    After that once the HEADER is encountered, it checks the next position of HEADER, and if the data in between equal self.length, returns the data and moves the pointer.
                    Else, the sync is said to be lost, and 'findsync' is called.
                    
                    Raises
                    ------
                    Stores the error in log file.

    findsync()  :   Called if the sync byte (HEADER) is lost while data collection.
                    It tries to directly find the HEADER once and returns the data. If not possible, it runs a double loop.
                    The first loop is run as long as the new length od data found is not equal to the original.
                    Inseid the nested loop runs for 1 sec, trying to find the HEADERS and the correct data length.
                    Once that is done, it returns the data.
                    
                    Raises
                    ------
                    Stores the error in log file.
    '''
    def __init__(self, s):
        self.s = s
        self.buf=bytearray()
        self.length = 0
        self.time_q = queue.Queue(maxsize=5)
        self.port_data_collection = False
        self.sync_loss_count = 0
        self.log = 0
        self.StateEvent = Event()
        self.N = 3*10**4
        self.sensor_id = None
        self.DATAFMT = None
        self.save_data_q = queue.Queue(maxsize=0)



    def findsync(self):
        '''
        Called if the sync byte (HEADER) is lost while data collection.
        It tries to directly find the HEADER once and returns the data. If not possible, it runs a double loop.
        The first loop is run as long as the new length od data found is not equal to the original.
        Inseid the nested loop runs for 1 sec, trying to find the HEADERS and the correct data length.
        Once that is done, it returns the data.
        
        Raises
        ------
        Stores the error in log file.
        '''
        try:
            syncpos = []
            i=self.buf.find(HEADER)
            if self.buf[self.length+i +1].to_bytes(1,'big')==HEADER:
                data = self.buf[i+1:i+1+self.length]
                self.buf = self.buf[i + 1 + self.length:]
                return data
            else:
                position = 0
                while position!=self.length:
                    if sysbreak:
                            break
                    starting=self.time_q.get()
                    ending=0.0
                    while(ending-starting<=1.0):
                        i = self.buf.find(HEADER)
                        if i >= 0:
                            self.buf = self.buf[i + 1:]
                            syncpos.append(i)
                        else:    
                            while True:
                                ext = self.s.read(250)
                                i = ext.find(HEADER)
                                if i >= 0:
                                    self.buf = ext[i + 1:]
                                    syncpos.append(i)
                                    break
                                else:
                                    self.buf += (ext)
                        ending=self.time_q.get()
                    position = statistics.mode(syncpos)
                self.buf=self.buf[position:]
                data=self.buf[:position]
                return data
        except Exception as e:
            write_logs(f"Error in findsync() for {self.s.name} \n" + str(e))
            exitfunct(f"Error in findsync() for {self.s.name} " + str(e))
            return None



    def readline(self):
        '''
        Records the data of a particular port in a batch. If first time, it sets the length of the data (self.length).
        It then checks the length of the buffer array (self.buf) and refills it if required.
        After that once the HEADER is encountered, it checks the next position of HEADER, and if the data in between equal self.length, returns the data and moves the pointer.
        Else, the sync is said to be lost, and 'findsync' is called.
        
        Raises
        ------
        Stores the error in log file.
        '''
        try:
            if self.length==0:
                for i in port_identity:
                    if i['Port'] == self.s.name:
                        self.length = i['DATAFMT']
                        break
            if len(self.buf)<=(2*self.length):
                buftemp=self.s.read(250)
                self.buf=bytearray(self.buf)
                self.buf=self.buf+buftemp
            if (self.buf[0].to_bytes(1,'big')==HEADER) & (self.buf[self.length+1].to_bytes(1,'big')==HEADER):
                data=self.buf[1:self.length+1]
                self.buf=self.buf[self.length+1:]
            else:
                    self.sync_loss_count+=1
                    write_logs(f"Sync Lost in {self.s.name} {self.sync_loss_count} times, now to \"findsync\" ")
                    data=self.findsync()
            return data
        except Exception as e:
            write_logs(f"Error in readline() for {self.s.name} \n" + str(e))
            exitfunct(f"Error in readline() for {self.s.name} " + str(e))
            return None


def timeline(readobjects):
    '''
    Global time checking function. Runs on a separate thread independently from all the other port threads. Used to periodically collect 
    timestamps that are used to note the point of collection of a data point. Runs untill the entire data collection process is completed
    by using 'collection_process_done' flag.
    After every 0.001 second, it records the timestamp and stores in the queue of all the readline objects.
    After every 100 runs, it stores a log.
    It uses the global variable
    => collection_process_done

    Parameter(s)
    -----------
    readobjects  :  list of readline objects requierd to store the timestamps in the respective queues

    Raises
    ------
    Stores the errors in the log file!
    '''
    global collection_process_done
    try:
        start = time.monotonic()
        t_count = 1
        while collection_process_done == False:
            if sysbreak:
                break
            time.sleep(1/10**5)
            timestamp = time.monotonic()-start
            for rl in readobjects:
                if collection_process_done==True:
                    break
                if rl.time_q.full():
                    _ = rl.time_q.get()
                rl.time_q.put(timestamp)
            t_count+=1
            if collection_process_done==True:
                    break
        write_logs("Out of loop in timeline!!")
    except Exception as e:
        write_logs("Error in timeline() \n" + str(e))
        exitfunct("Error in timeline()" + str(e))



def parsedata(x, rl):
    '''
    Function to parse the recorded data from the ports using respective DATAFMT which contains the data format length of all data. 
    The particular one which matches is used to unpack the entire data. The data which also contains Timestamps is stored in a dataframe
    and the returned accordingly.

    Parameter(s)
    ------------
    x  :  The recorded data of a single batch

    Raises:
    ------
    Stores the error, first element and size of the first element of the data in the logs.
    '''
    try:
        if len(x) != 2:
            data = x
            timestamps = None
        else:
            data = x[0]
            timestamps = x[1]

        if rl.DATAFMT == None:
            data_fmt_found = False
            for i in DATAFMT.keys():
                fmt_size = 2*int(i)
                
                if len(data[0])==fmt_size:
                    fmt_list = DATAFMT[i]

                    for fmt in fmt_list:
                        try:
                            x_vals = [struct.unpack(fmt, t) for t in data]
                            data_fmt_found = True
                            rl.DATAFMT == fmt
                            break
                        except:
                            write_logs(f"{fmt} is not the correct format")
                            pass
                if data_fmt_found:
                    break       
            if data_fmt_found == True:    
                x_vals_col_scheme = {'column_' + str(i) : pl.Int32 for i in range(np.array(x_vals).shape[1])}    
                if timestamps !=None :
                    df=pl.DataFrame(timestamps, schema={'Timestamp': pl.Float32}, orient='row')
                    df=pl.concat([df,pl.DataFrame(x_vals, orient = 'row', schema = x_vals_col_scheme)], how = 'horizontal')
                else:
                    df = pl.DataFrame(x_vals, orient = 'row', schema = x_vals_col_scheme)
                return df
            else: 
                raise Exception(f"{rl.s.name} Data is of unknown format")
        else:
            x_vals = [struct.unpack(rl.DATAFMT, t) for t in data]
            x_vals_col_scheme = {'column_' + str(i) : pl.Int32 for i in range(np.array(x_vals).shape[1])}    
            if timestamps !=None :
                df=pl.DataFrame(timestamps, schema={'Timestamp': pl.Float32}, orient='row')
                df=pl.concat([df,pl.DataFrame(x_vals, orient = 'row', schema = x_vals_col_scheme)], how = 'horizontal')
            else:
                df = pl.DataFrame(x_vals, orient = 'row', schema = x_vals_col_scheme)
            return df
    except Exception as e:
        write_logs("Error in parsedata() \n" + str(e))
        exitfunct("Error in parsedata()" + str(e))

def savedata(rl, y, key):
        '''
        Function to store the dataframe returned from the function 'parsedata()' into a CSV file. This data is 1 batch of a particular port.
        The naming convention is port name + file number. 
        Example: COM4 + _ + log (say is 1) + .csv = COM4_1.csv

        Paremeter(s):
        rl  :  readline object required to access the log (rl.log) for the serialization for that port.
        y   :  It is the dataframe which returned from parsedata() and want to save.

        Raises:
        -------
        Stores the error in the logs and continues ahead.
        '''
        try:
            write_logs(f"{rl.s.name} savedata() called for log = {key}")
            fpath = os.path.join(savepath, "Textfiles")
            var = "%02d" % (key)
            write_logs(f"{rl.s.name} file no: {var}")
            files=str(rl.s.name)+'_'+str(var)+'.feather'
            fpath = os.path.join(fpath,files)
            y.write_ipc(fpath)

            if os.path.exists(fpath):
                write_logs(f"Name {rl.s.name} Data log {key} saved at location {fpath} ")
            else:
                raise Exception(f'File {rl.s.name} with log {key} was not saved due to some error!!')
        except Exception as e:
            write_logs("Error in savedata() \n" + str(e))
            exitfunct("Error in savedata()" + str(e))


def audiodata():
    '''
    Function to record audio data. The audio is recorded in batches as per given by the user. The main loop runs for (time_to_run) secs,
    unless 'sysbreak' is True, which stops the process altogether.
    Once the recording of one batch completes, the 'audioevent' is set to notify 'saveaudio()' to start saving the batch while this starts
    recording the next batch.
    Does not require parameters but does directly uses the below given global variables.
    => myrecording, audioevent, count, sysbreak, time_to_run

    Raises
    ------
    Stores the error in the logs and continues ahead.
    '''
    try:
        global myrecording, audioevent, count, time_to_run
        write_logs(f"In sound recording for {time_to_run}")
        myrecording = sd.rec(int(time_to_run * fs), samplerate=fs, channels=1)
        sd.wait()
        audioevent.set()
    except Exception as e:
        write_logs("Error in audiodata() \n" + str(e))
        exitfunct("Error in audiodata()" + str(e))


def saveaudio():
    '''
    Function to start saving the recorded audio batches. Starts as soon as 'audioevent' is set. Saves the file in CSV format with the 
    convention as Sound + .csv.
    Example: Sound1.csv
    The main loop runs until sysbreak is True. Once the audio is saved, the 'audioevent' is set to 'clear' so that
    it can be set for the next batch.
    Doesn't require parameters but uses the below global variables
    => myrecording, audioevent

    Raises
    ------
    Stores the error in the logs and continues ahead.
    '''
    global myrecording, audioevent, sysbreak
    try:
        file_name="SoundMain"
        folder_name = savepath.split('\\')[-1]
        file_name = file_name + ' ' + folder_name + '.csv'
        fpath = os.path.join(savepath,file_name)
        audiopath = os.path.join(savepath,("Audio_Main " + folder_name + '.wav'))

        audioevent.wait()
        
        if sysbreak == False:
            pl.DataFrame(myrecording, schema = {'column_0' : pl.Float32}).write_csv(fpath)
            write_logs(f"Audio .csv saved at {fpath}")
            write(audiopath,  fs, myrecording)
            write_logs(f"Audio .wav saved at {audiopath}")

    except Exception as e:
        write_logs(f"Error in saveadio() \n" + str(e))
        exitfunct("Error in saveadio()" + str(e))


def producer(rl):
    '''
    Function to record the data from a COM port in batches according to . The function runs for 'time_to_run' secs and collects data
    in batches till then unless sysbreak is True, in which case it stops the process altogether. 
    Each batch contains rl.N samples. It gets the timestamp from rl.time_q . 
    
    Global Dynamic variables are used to store the recorded data in them. The  decides where the data is recorded. This is used
    to allow for concurrent writing and reading and the batch helps in making sure that the RAM isn't loaded.

    Once one batch is recorded, the StateEvent is set to signal the 'consumer()' to start saving the file.
    Continuous logs are recorded to ensure proper tracking if needed. They are: Length of a batch, Frequency of data collection of that
    batch, State and Log number of the batch recorded and at the end, a review of how many times the port data collection ran.
    It uses global variabe
    => time_to_run

    Parameter(s)
    -----------
    rl : readline object which is required in multiple places

    Raises
    ------
    Stores the error in the logs and continues ahead.
    '''
    global time_to_run
    start=rl.time_q.get()
    end=0.0
    timeval=0.0
    try:
        
        while(end - start <= time_to_run):
            x = []
            x_time = []
            for _ in range(rl.N):
                x.append(rl.readline())
                if sysbreak:
                    break
                else:
                    if (rl.time_q.empty()==True):
                        x_time.append(timeval)
                    else:
                        timeval = rl.time_q.get()
                        x_time.append(timeval)
            rl.save_data_q.put({rl.log : [x,x_time]})
            write_logs(f'{rl.s.name} producer() data recorded for log = {rl.log} and queue length = {rl.save_data_q.qsize()}\n')
            end=rl.time_q.get()
            rl.log=rl.log+1
            rl.sync_loss_count=0
        end=rl.time_q.get()
        rl.port_data_collection = True
        write_logs(f"{rl.s.name} producer() ran {rl.log} time(s) in {end-start} seconds")
    except Exception as e:
        write_logs(f"Error in producer() for {rl.s.name} \n" + str(e))
        exitfunct(f"Error in producer() for {rl.s.name} " + str(e))



def consumer(rl):
    '''
    Function to store the recorded data of a batch. Waits till 'StateEvent' is set by the 'producer()'. Find the global variable to be 
    checked from the  of the recording. Main loop runs till 'rl.port_data_collection' is True or 'sysbreak' is True. Although there is a timeout 
    which is equal to 'port_timeout' seconds to ensure there is no deadlock or doesn't wait for infinity.

    It logs the port name, then calls 'parseddata()' and 'saveddata()' to unpack and store in the local storage. At the end, another log is
    made which prints the preview of the batch dataframe formed.
    The StateEvent is cleared for producer() to set it for next batch.

    Parameter(s)
    -----------
    rl : readline object which is required in multiple places

    Raises
    ------
    Stores the error in the logs and continues ahead.
    '''
    try:
        while True:
            if sysbreak==False:
                if (rl.port_data_collection == True and rl.save_data_q.empty()==True):
                    break
                else: 
                    if rl.save_data_q.empty()==False:
                        write_logs(f"{rl.s.name} consumer() queue length = {rl.save_data_q.qsize()}")
                        dict_data = rl.save_data_q.get()
                        key_data = list(dict_data.keys())[0]
                        data_to_parse = dict_data[key_data]
                        data_parsed =  parsedata(data_to_parse, rl)
                        savedata(rl,data_parsed, key_data)
                        write_logs(f"{rl.s.name}  data saved log={key_data}")
            else:
                write_logs(f"Consumer() exit as system exit called")
                break
            time.sleep(1/10**4)
    except Exception as e:
        write_logs(f"Error in consumer() for {rl.s.name} \n" + str(e))
        exitfunct(f"Error in consumer() for {rl.s.name} " + str(e))



def mergefiles(readobjects):
    '''
    Function to merge all the batch files created and stored them in one single main CSV file per COM port. It also merges all the batch audio
    files and stores them in one main CSV file. That file is also used to create an audio WAV file.

    The naming convention for COM port files is df_ + port_name + .csv.
    Example: df_COM3.csv

    The naming convention for audio files is Sound_Main.csv
    Also audio WAV file is saved in WAV format Main_Audiofile.wav

    Parameter(s)
    -----------
    readobjects  : the list of the readline objects required to find the multiple files for each port.
    '''
    try:
        if sysbreak == False:
            ## For text files
            for rl in readobjects:
                folder_name = savepath.split('\\')[-1]
                filepath = os.path.join(savepath,str(rl.sensor_id))
                filepath = filepath + ' ' + folder_name + '.csv' 
                pathsearch=savepath +'\\Textfiles\\'+str(rl.s.name)+'_??.feather'
                write_logs(f"{rl.s.name} No of files: {len(glob.glob(pathsearch))}")
                df_main = pl.DataFrame()
                for filename in glob.glob(pathsearch):
                    df = pl.read_ipc(filename)
                    df_main = pl.concat([df_main, df], how = 'vertical')

                df_main.write_csv(filepath)
                time.sleep(0.1)
                # df_main.write_csv(filepath_sec)

                # write_logs(f"{rl.s.name} merged .csv saved at {filepath} and {filepath_sec}")
                write_logs(f"{rl.s.name} merged .csv saved at {filepath}")
                

    except Exception as e:
        write_logs("Error in mergefiles() \n" + str(e))
        exitfunct("Error in mergefiles()" + str(e))
    

def get_error_display():
    return err_message


def exitfunct(msg):    
    '''
    Function to stop all the process by setting sysbreak True. Called in the UI when cross-button is clicked.
    Uses global variable sysbreak.
    '''
    global sysbreak, err_message
    # print("From final_ file: Error encountered!!")
    sysbreak = True
    err_message = msg
    sysbreak_event.set()


def prelim_process(sp, lp):
    '''
    First function to be called during the execution of the program. It sets the global variables by calling 'setenvvars()'. Then it finds
    the list of serial COM ports and stores in PORTS list. It initailises the serial port in a global variable with their 'Baud_Rate'.
    For each port it creates a readline object and the with threading
    it simultaneously calls the 'findport()' function for all the ports to set them up. 
    It is a mandatory function and has to be called first.
    It uses some global variables too
    => PORT, collection_process_done, savepath, readobjects

    Parameter(s)
    -----------
    logpath  :  The location of the log file in which the all the logs of the program execution is to be stored.

    Raises
    ------
    Stores the error in the logs and continues ahead.
    '''
    global PORT, collection_process_done, savepath, readobjects, logpath, time_worker
    logpath = lp
    savepath = sp
    try:
        write_logs("prelim_process() called")
        fpath = os.path.join(savepath, "Textfiles")
        if not os.path.exists(fpath):
            os.makedirs(fpath)
        setenvvars()
        for p in serial.tools.list_ports.comports():
            if " ".join(p[1].split()[:-1])=='Silicon Labs CP210x USB to UART Bridge':
                PORT.append(p)

        write_logs(f"No of Ports: {len(PORT)}")
        if len(PORT)!=0:
            write_logs("Creating ReadLine objects!!")
            for i in range(len(PORT)):
                ser = serial.Serial(PORT[i][0], baudrate=BAUD_RATE)
                rl = ReadLine(ser)
                readobjects.append(rl)
            write_logs(f"Starting timeline and findport({len(PORT)} threads)!!")
            time_worker = threading.Thread(target=timeline, args=(readobjects,), daemon=True)
            time_worker.start()
            time.sleep(1)
            with concurrent.futures.ThreadPoolExecutor() as exe:
                _ = [exe.submit(findport,rl) for rl in readobjects]
            write_logs(port_identity)
        else:
            write_logs("No ports detected, Check your ports")
    except Exception as e:
        write_logs("Error in prelim_process() \n" + str(e))
        exitfunct("Error in prelim_process()" + str(e))



def call_main(collect_audio):
    '''
    The main function of the program after 'prelim_process()'. This function is too called by the UI. It controls and manages the data 
    collection, saving, audio collection and saving and merging of various batch files. It first sets the 'savepath' where the files are 
    supposed to be saved. Then with the help of threading it runs the 'timeline()', 'audiodata()', 'saveaudio()', 'producer()' and 'consumer()' 
    in various threads. At each step, various logs are recorded depicting the milestones of the function. 
    
    At the end, it calls the 'mergefiles()' function to merge all the stored batch files of each port and audio and save them in their 
    final versions. It uses some global variables
    => PORT, collection_process_done, savepath, readobjects, PATH, logpath

    Parameter(s)
    ------------
    sp       :  The path of the folder where the files are to be saved.
    logpath  :  The path of the log file in which the logs are to be stored.

    Raises
    ------
    Stores the error in the logs and continues ahead.
    '''
    global PORT, collection_process_done, savepath, readobjects, sysbreak, time_worker
    try:

        collection_process_done = False
        start=time.monotonic()
        write_logs("call_main() called")
        if len(PORT)!=0:
            sensor_desc_dumps()
            if collect_audio:
                audioreader = threading.Thread(target=audiodata, daemon=True)
                audiowriter = threading.Thread(target=saveaudio, daemon=True)
                audioreader.start()
                audiowriter.start()

            for rl in readobjects:
                write_logs(f"{rl.s.name} Is Open: {rl.s.isOpen()}")
            
            with concurrent.futures.ThreadPoolExecutor() as exe:
                x = [exe.submit(producer, rl) for rl in readobjects]
                y = [exe.submit(consumer, rl) for rl in readobjects]
            write_logs(f"All ports data collected at {time.monotonic() - start}")


            for rl in readobjects:
                write_logs(f"{rl.s.name} port_data_collection: {rl.port_data_collection}")
            
            collection_process_done=True
            if collect_audio:
                audioreader.join()
                write_logs("Out of audio reader thread")
                audiowriter.join()
                write_logs("Out of audio reader and writer thread")


            write_logs(f"All data (ports + mic) collected: {collection_process_done}")
            # for timeline thread
            time_worker.join(timeout=2.0)
            for rl in readobjects:
                rl.s.close()
                write_logs(f"{rl.s.name} : Serial is closed!")
            time.sleep(0.5)
            mergefiles(readobjects=readobjects)
            
        
        else:
            write_logs("No port connected!")
            exitfunct("From call_main(): No Ports connected!!")
        
        write_logs(f"Out of all the threads total run time:{time.monotonic()-start} ")
    
    except Exception as e:
        write_logs("Error in call_main() \n" + str(e))
        exitfunct("Error in call_main()" + str(e))

if __name__ == "__main__":
    print()