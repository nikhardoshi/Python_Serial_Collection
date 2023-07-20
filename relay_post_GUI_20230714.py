import requests
import os
import argparse# Create the parser
import logging
import subprocess
import time
from final_v28 import write_logs, exitfunct

# input wifi name and password
# name = "IITB_IOT"
# password = "iitbiot1234"

esp_wifi_ip = {
    'Gyro' : 'http://192.168.0.185/post',
    'Acceloremeter' : 'http://192.168.0.188/post',
    'Magnetometer' : 'http://192.168.0.187/post'
}

def createNewConnection(name, SSID, password):
    '''
    Function to create a new WiFi identity XML file for the WiFI with that specific name, password and SSID.
    Also it logs the process wherever required.

    Parameter(s)
    ------------
    name       :  Name of the WiFi network to connect.
    SSID       :  SSID of the WiFi network to connect. It is the same as the name of the WiFi network.
    password   :  Password of the WiFi network to connect.

    Raises
    ------
    Stores the error in log file and continues ahead or breaks.
    '''
    try:
        config = """<?xml version=\"1.0\"?>
        <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
            <name>"""+name+"""</name>
            <SSIDConfig>
                <SSID>
                    <name>"""+SSID+"""</name>
                </SSID>
            </SSIDConfig>
            <connectionType>ESS</connectionType>
            <connectionMode>auto</connectionMode>
            <MSM>
                <security>
                    <authEncryption>
                        <authentication>WPA2PSK</authentication>
                        <encryption>AES</encryption>
                        <useOneX>false</useOneX>
                    </authEncryption>
                    <sharedKey>
                        <keyType>passPhrase</keyType>
                        <protected>false</protected>
                        <keyMaterial>"""+password+"""</keyMaterial>
                    </sharedKey>
                </security>
            </MSM>
        </WLANProfile>"""
        command = "netsh wlan add profile filename=\""+name+".xml\""+" interface=Wi-Fi"
        with open(name+".xml", 'w') as file:
            file.write(config)
        os.system(command)
        time.sleep(1)
    except Exception as e:
        write_logs("Error in createNewConnection() from relay_post.py \n" + str(e))
        exitfunct(f"Error in createNewConnection() from relay_post.py \n" + str(e))

 
# function to connect to a network   
def Wifi_connect(name, SSID, password):
    '''
    Function to connect to a WiFi network. It first calls the 'createNewConnection()' just in case it is a new network
    and it is being connected to the first time.
    Then after 1 second sleep, it connects to the network and verifies the connection.

    Parameter(s)
    ------------
    name       :  Name of the WiFi network to connect.
    SSID       :  SSID of the WiFi network to connect. It is the same as the name of the WiFi network.
    password   :  Password of the WiFi network to connect.

    Raises
    ------
    Stores the error in log file and continues ahead or breaks.
    '''
    try:
        createNewConnection(name, SSID, password)
        wifi = subprocess.check_output(['netsh', 'WLAN', 'show', 'interfaces'])
        data = wifi.decode('utf-8')
        if "IITB_IOT" in data:
            write_logs(f"Connection with wifi {name} established ")
        else:
            raise Exception(f"Connection with wifi {name} not established")
    except Exception as e:
        write_logs("Error in Wifi_connect() from relay_post.py \n" + str(e))
        exitfunct(f"Error in Wifi_connect() from relay_post.py \n" + str(e))


connection_tried_once = False

def HTTP_message(name, SSID,password):
    '''
    Function to send a command (relay or mpu) over the WiFi network to respective IP address. It first verifies the
    connection to the WiFi and then sends the command. At the end, the success or failure is recorded in the logs.

    Parameter(s)
    ------------


    Raises
    ------
    Stores the error in log file and continues ahead or breaks.
    '''
    global connection_tried_once
    try:
        write_logs(f"ESP restart starts for all ESPs")
        wifi = subprocess.check_output(['netsh', 'WLAN', 'show', 'interfaces'])
        data = wifi.decode('utf-8')
        if "IITB_IOT" in data:
            for key in esp_wifi_ip.keys():
                r = requests.post(esp_wifi_ip[key], data = "ESP_RESTART")
                time.sleep(0.4)
                if r.ok:
                    write_logs(f"{key} reset successful!")
                else:
                    raise Exception(f"{key} reset failed!")
        elif connection_tried_once==False:
            Wifi_connect(name=name, SSID=SSID, password=password)
            connection_tried_once=True
            write_logs("Wifi Connecton")
            HTTP_message(name=name, SSID=SSID, password=password)
        else:
            raise Exception(f"Message(s) to ESP32(s) not sent")
    except Exception as e:
        write_logs("Error in HTTP_message() from relay_post.py \n" + str(e))
        exitfunct(f"Error in HTTP_message() from relay_post.py \n" + str(e))
    # WiFi_connect(name, name, logpath)
#     # python relay_post.py --state RELAY_CLOSE
# Wifi_connect(name, name, password, logpath="C:\\Users\\Sudhendu\\Documents\\IITB\\V-guard\\Dummy File Folder\\Saved data\\_Mar 18 00_58_09 2023\\logs1.txt")
# time.sleep(1)
# HTTP_message(cmd="RELAY_OPEN", logpath="C:\\Users\\Sudhendu\\Documents\\IITB\\V-guard\\Dummy File Folder\\Saved data\\_Mar 18 00_58_09 2023\\logs1.txt")