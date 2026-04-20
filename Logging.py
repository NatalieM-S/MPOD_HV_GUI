import subprocess
import csv
import re
from datetime import datetime
import time
import os
import tkinter as tk
import threading
from GUI.Driver.MPODClass import MPOD

class Logger:
    def __init__(self):#, n_datapoints = 0):
        ### Settings: 
        IP = "169.254.107.70"
        
        self.n_channels = 8#ch 0:7
        self.n_values  = 3#current, voltage, status
        self.wait_time_ms = 100#0: as fast as possible, not necessary! 100 is true max

        filename = f"{datetime.now().strftime('%m-%d-%Y_%H_%M')}.csv"#ex: 04-05-2026_15_30
        folder = f"{datetime.now().strftime('%b-%Y')}/"#ex: Aug-2026
        folder = 'Results/'+folder

        self.filename=folder+filename

        if not os.path.exists(folder):
            os.makedirs(folder)

        ### Fastest commands can be generated using oid numeric representations!
        base = ".1.3.6.1.4.1.19947.1.3.2.1"

        voltage_oids = [f"{base}.5.{i}" for i in range(1, 9)]
        current_oids = [f"{base}.7.{i}" for i in range(1, 9)]
        status_oids  = [f"{base}.4.{i}" for i in range(1, 9)]
        ### Reads all values
        # self.parsemethod = 1
        # self.cmd = ["snmpwalk", "-v2c", "-c", "public", "-Op", ".12", IP, "WIENER-CRATE-MIB::outputTable"]
        ### Reads specific values, requires MIB parsing
        # self.parsemethod = 1
        # self.cmd = ["snmpbulkget", "-v2c", "-c", "public","-Cr100", "-Op", ".12", IP,
        #     "WIENER-CRATE-MIB::outputMeasurementSenseVoltage",
        #     "WIENER-CRATE-MIB::outputMeasurementCurrent",
        #     "WIENER-CRATE-MIB::outputStatus"]

        ### Reads specific values, no MIB parsing
        # self.parsemethod = 2#All channels in same column

        self.parsemethod = 3 # Preferred, no MIB parsing and channels separated by column, no status

        self.cmd = ["snmpget", "-v2c", "-c", "public", "-On", "-Op", ".12", IP,
            *voltage_oids, *current_oids]#, *status_oids]

        if self.parsemethod == 2: 
            self.cmd=[*self.cmd, *status_oids] # add back statuses
            self.column_names = ["time", "Ch", "V", "I", "Status"]
        if self.parsemethod == 3: 
            self.n_values = 2
            self.column_names = ['time']
            for i in range(self.n_channels):
                self.column_names.append(f'V{i}')
                self.column_names.append(f'I{i}')

        self.event=threading.Event()
        self.high_res=0
        self.b1_text = "Start"

        # self.MPOD = MPOD()

    def increment_voltage(self):
        # self.MPOD.SetTargetVoltage(1,1)
        #todo: send all in a batch
        pass

    def fx1(self):
        pass
    def fx2(self):
        pass
    def increase_resolution(self):
        if self.high_res: #switch high resolution off
            self.wait_time_ms = 2000
            self.b1_text = "Start"
        else: #switch on
            self.wait_time_ms  = 100
            self.b1_text = "Stop"
        self.high_res = not(self.high_res)

    def take_data(self, n_datapoints = 0):
        count = 0 
        while not self.event.is_set():
            count += 1
            
            result = subprocess.run(self.cmd, capture_output=True, text=True)
            if self.wait_time_ms>0:
                time.sleep(self.wait_time_ms/1000)
            if self.parsemethod == 1:
                lines = result.stdout.splitlines()
            else: 
                raw = result.stdout.strip()
                lines = re.split(r'(?=\.\d+\.\d+\.\d+)', raw)
                lines = [l.strip(" '") for l in lines if "=" in l]

            data = {}
            values = []
            now = datetime.now()
            ts = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"

            for line in lines:
                if "=" not in line:
                    continue
                if self.parsemethod == 1: 
                    oid, val = line.split("=", 1)
                    val = val.strip()

                    #Parse reply
                    m = re.search(r'\.u(\d+)', oid)
                    if not m:
                        continue
                    ch = int(m.group(1))

                    if ch not in data:
                        data[ch] = {}
                    while ":" in val and val.split(":", 1)[0].isalpha():
                        val = val.split(":", 1)[-1].strip()

                    val = " ".join(val.split())

                    #Extract desired vals
                    if "outputMeasurementSenseVoltage" in oid:
                        val = re.sub(r'\s*V$', '', val)
                        data[ch]["voltage"] = val
                    elif "outputMeasurementCurrent" in oid:
                        val = re.sub(r'\s*A$', '', val)
                        data[ch]["current"] = val
                    elif "outputStatus" in oid:
                        m_bits = re.match(r'([0-9A-Fa-f ]+)', val)
                        if m_bits:
                            data[ch]["status"] = m_bits.group(1).strip()
                else:
                    _, val = line.split("=", 1)
                    val = val.strip()
                    while ":" in val and val.split(":", 1)[0].isalpha():
                        val = val.split(":", 1)[-1].strip()
                    val = " ".join(val.split())
                    values.append(val)

            if self.parsemethod ==2:
                if len(values) != self.n_channels*self.n_values:
                    data[0] = {"voltage": None,"current": None,"status": "error" }
                    error_count+=1
                    print(error_count)
                        
                else:
                    for ch in range(self.n_channels):
                        # V, I, status
                        v = values[ch].replace(" V", "")
                        c = values[ch + self.n_channels].replace(" A", "")
                        s = values[ch + self.n_channels*2].split(":", 1)[-1].strip()
                        
                        data[ch] = {"voltage": v,"current": c,"status": s}
            elif self.parsemethod == 3:
                if len(values) != self.n_channels*self.n_values:
                    data[0] = {"voltage": None,"current": None}
                    error_count+=1
                    print(error_count)
                        
                else:
                    for ch in range(self.n_channels):
                        # V0, I0, ...  
                        v = values[ch].replace(" V", "")
                        c = values[ch + self.n_channels].replace(" A", "")

                        data[ch] = {"voltage": v,"current": c}

            #Write data to file
            try:
                open(self.filename, "r")
                file_exists = True
            except:
                file_exists = False

            with open(self.filename, "a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(self.column_names)
                
                if self.parsemethod == 3:
                    vals = []
                    for ch in sorted(data.keys()):
                        vals.append(data[ch].get("voltage"))
                        vals.append(data[ch].get('current'))
                    writer.writerow([ts,*vals])
                else:
                    for ch in sorted(data.keys()):
                        vals = data[ch]
                        writer.writerow([ts, ch,vals.get("voltage"),vals.get("current"), vals.get("status") ])
            if n_datapoints >  0 and count >= n_datapoints: 
                break
        
def start_gui(logger):
    root = tk.Tk()
    root.title("Data logging and Custom Controls")
    thread = threading.Thread(target=logger.take_data, daemon=True)
    def on_stop():
        logger.event.set()
        root.destroy()
    #COLUMN 0: 
    L1=tk.Label(root, text="Logger is running in the background")#,font=("DejaVu Sans",10))
    L1.grid(row=0,column=0,columnspan=2, pady=20)

    b1=tk.Button(root, text=f"{logger.b1_text} High Resolution DAQ", command=logger.increase_resolution,height = 2)
    b1.grid(row=1, column=0, pady=10)

    b2=tk.Button(root, text="Increment by N Volts", command=logger.increment_voltage,height = 2)
    b2.grid(row=2, column = 0, pady=10)
    
    L2=tk.Label(root, text = "N volts")
    L2.grid(row=3,column=0,pady=(10,0))

    n1=tk.Entry(root,width=10)
    n1.insert(0,"50")
    n1.grid(row=4,column=0,pady=1)

    b3=tk.Button(root, bg="red",text="Stop & Exit", command=on_stop)
    b3.grid(row=5,column=0, columnspan=2,pady=(50,10))
   
    #COLUMN 1: 
    # L1=tk.Label(root, text="Logger is running in the background")
    # L1.grid(row=0,column=0,columnspan=2, pady=20)
    
    b4=tk.Button(root, text="text" ,command=logger.fx1,height = 2)
    b4.grid(row=1, column=1, pady=10)

    b5=tk.Button(root, text="txt", command=logger.fx2, height = 2)
    b5.grid(row=2, column = 1, pady=10)
    
    L3=tk.Label(root, text = "txt")
    L3.grid(row=3,column=1,pady=(10,0))

    n2=tk.Entry(root,width=10)
    n2.insert(0,"50")
    n2.grid(row=4,column=1,pady=1)

    # b6=tk.Button(root, bg="red",text="Stop & Exit", command=on_stop)
    # b6.grid(row=5,column=0, columnspan=2,pady=(50,10))
    def update_panel():
        b1.config(text=f"{logger.b1_text} High Resolution DAQ")
        if not logger.event.is_set():
            root.after(100, update_panel)

    thread.start()
    update_panel()
    root.mainloop()

if __name__ == "__main__": 
    n_datapoints = 0
    gui_mode = 1

    
    logger = Logger()
    if gui_mode: 
        logger.wait_time_ms = 2000 #slow initial daq
        start_gui(logger)
    else: 
        logger.take_data(n_datapoints)

    print('finished')

""" Todo: setup tkinter to have buttons for various fx: 
    - Auto start on isegcontrol boot
    - Buttons: 
        x End DAQ (completed)
        x Start/finish high resolution DAQ (completed)
        - +N volts on each channel 
    - Display something to make sure channels are ok
        
"""
