import os
import pexpect as px #for linux
import subprocess #for windows
import platform
import time
import traceback
import inspect

# Written by Natalie Mujica-Schwahn, last updated: 10/4/25
class MPOD:
    r'''
    Input IP to connect to MPOD
    REQUIREMENT:  WIENER-CRATE-MIB.txt must be located in /usr/share/snmp/mibs (Windows: C:\usr\share\snmp\mibs)
    Reference 1: https://file.wiener-d.com/documentation/MPOD/WIENER_MPOD_Manual_3.2.pdf
    Reference 2: https://fsunuc.physics.fsu.edu/wiki/images/1/10/Iseg_SNMP_Programmers_Guide.pdf
    '''

    def __init__(self, IP = '169.254.107.70', mode = 0, MIBdir = "/usr/share/snmp/mibs"):
        self.IP = IP
        self.mibdir = MIBdir #or os.path.expanduser("~/.snmp/mibs")
        self.mode = mode#mode: 0, driver, 1, debug (not connected)
        self.debug_mode = 0
        self.os = platform.system()#windows or linux
        #If program will not start, check these environment variables below. They may need to be set in shell. 
        # os.environ["MIBS"] = "+WIENER-CRATE-MIB"
        # if os.path.isfile(self.mibdir + "/WIENER-CRATE-MIB.txt"):
        #     os.environ["MIBDIRS"] = self.mibdir
        # else: 
            # raise RuntimeError(f"MIB file was not found in {self.mibdir}")
        self.warnings = []
        self.gather_commands=0
        self.gathered_commands = []
        self.gathered_command_type = ''
        self.last_cmd=''
        if self.debug_mode == 1:
            self.start_time = time.monotonic()
            self.last_cmd={'All commands': [], 'All replies': [], 'Errors':[],'error time':[],'command time': []}
        
        self.precision ='-Op .12 '#high precision creating problems on windows. older SNMP protocols do not support this option 
        #Test power on and precision 
        if not mode:
            if len(self.Send('get','sysMainSwitch.0'))<1:
                self.precision = ''#try lower precision values for older SNMP protocols
                if len(self.Send('get','sysMainSwitch.0'))<1:
                    self.WarnHandler('Crate is not connected or configured correctly')
            if not self.QueryPowerCrate():
                self.WarnHandler('Crate is off - powering on now, wait for system to respond')
                self.SetPowerCrate(1)
                time.sleep(1)
                if self.QueryPowerCrate():#if power on was successful, wait for modules to respond
                    while 'No Such Instance' in self.Send('walk','outputSwitch'):
                        pass#time.sleep(0.5)
                else: 
                    self.WarnHandler('Crate did not turn on')
                   
        self.n_channels = len(self.GetAllNames())
        ### FOR DEBUG ONLY: ###
        if mode: 
            d = {'i_limit':1.0123456789012, 'i_rate':2.1234567890123, 'i_actual':0.11234567890123, 'v_target':2000.1234567890123, 
            'v_rate':5.1234567890123, 'v_sense':0.0123456789012, 'v_terminal': 0.1234567890123,'pwr':0,'v_configmax_sense':5000.1234567890123,
            'v_configmax_terminal': 5000.1234567890123,'i_configmax':1.1234567890123, 'i_triptimemax':500}
            d_pwr = {'pwr':1,'channels':self.GetAllNames()}
            self.mimic = {'crate': d_pwr}
            for ch in d_pwr['channels']:
                self.mimic[str(ch)] = dict(d)
        #######################
       
        ##example command : "snmpget -v 2c -Op .12 -m +WIENER-CRATE-MIB -c guru 169.254.107.70 outputPower.u0"
    
    def Send(self,cmd_type = 'walk', cmd = ''):
        '''Base command struct and MPODCrate communication functions'''
        #result = subprocess.run([cmd],shell = True,capture_output = True)
        n=[]
        
        original_cmd = cmd
        if self.gather_commands:       
            for i in range(len(inspect.stack())):
                n.append(inspect.stack()[i].filename)
            f=[i for i,f in enumerate(n) if __file__ not in f]
            if 'GUI' in n[f[0]].split('/')[-1]:#check if sender is GUI, dont block if so
                self.SendMultiple('pause')
                self.Send(cmd_type,cmd)
                self.SendMultiple('start')
            else:
                if len(self.gathered_command_type)>0:
                    if self.gathered_command_type is not cmd_type:
                        self.WarnHandler('Command type does not match, skipping')
                    else: 
                        self.gathered_commands.append(cmd)
                else:         
                    self.gathered_command_type = cmd_type
                    self.gathered_commands.append(cmd)
        else:
            if cmd_type == 'walk':#check connection
                if cmd == '': #use lower precision
                    cmd = f"snmpwalk -v 2c -m +WIENER-CRATE-MIB -c public {self.IP} " + cmd
                else: # require higher precision (if available)
                    cmd = f"snmpwalk -v 2c {self.precision}-m +WIENER-CRATE-MIB -c public {self.IP} " + cmd
            elif cmd_type == 'set':
                cmd = f"snmpset -v 2c {self.precision}-m +WIENER-CRATE-MIB -c guru {self.IP} " + cmd
            elif cmd_type == 'get':
                cmd = f"snmpget -v 2c {self.precision}-m +WIENER-CRATE-MIB -c guru {self.IP} " + cmd
            else:
                self.WarnHandler(cmd_type + ' is invalid command type')
            try:
                if self.os == 'Windows':
                    result = subprocess.run(cmd.split(), capture_output = True, shell = True)
                    result = result.stdout
                else: 
                    result = px.run(cmd)
                result_parsed = result.decode().rstrip('\n').rstrip('\r')
                if self.debug_mode == 0:
                    self.last_cmd = cmd
                else:
                    self.last_cmd['All commands'].append(cmd_type + ': ' + original_cmd)
                    self.last_cmd['All replies'].append(result_parsed)  
                    self.last_cmd['command time'].append(time.monotonic()-self.start_time)          
                
            except Exception as ex:# subprocess.CalledProcessError as err:
                try: #reattempt
                    time.sleep(0.1)#brief delay to prevent overloading filedescriptor on linux

                    result_parsed = self.Send(cmd_type, cmd.split(' ')[-1])
                    if self.debug_mode:
                        self.last_cmd['All commands'].append(cmd)
                        self.last_cmd['All replies'].append(result_parsed)  
                        self.last_cmd['command time'].append(time.monotonic()-self.start_time) 
                    self.WarnHandler(f"SNMP command succesfully retried. Command: {cmd})")
                except Exception as ex: 
                    self.WarnHandler(f"SNMP command failed. Command: {cmd})")#, Error: {err.stderr}")
                    result_parsed=None
            return result_parsed#, result, cmd#, result.stderr 
    
    def ParseReply(self, reply, mode):
        if reply is None: 
            result = 0
            if 'array' in mode:
                result = [0]*self.n_channels
            self.WarnHandler(f'Value read error for {self.last_cmd}, zeros returned instead') 
        else: 
            if 'no such instance currently exists at this oid' in reply:
                self.WarnHandler('Warning: Disconnected from crate')
                result = None
            else:
                reply = reply.lower()#easier to match mixed cases this way
                result = []
                match mode:
                    case 'float':
                        loc = reply.find('float:')
                        result = float(reply[loc+6:-3])
                    case 'float array':
                        for idx, k in enumerate(reply.split('float: ')):
                            if idx > 0:                           
                                result.append(float(k.split(' ')[0]))
                    case 'integer':
                        loc = reply.find('integer: ')
                        result = int(reply[loc+8:-3])
                    case 'integer array':
                        for idx, k in enumerate(reply.split('integer: ')):
                            if idx > 0:                           
                                result.append(int(k.split(' ')[0]))
                    case 'string':
                        #SPECIFICALLY FOR FINDING OUTPUT NAMES
                        for k in reply.split('wiener-crate-mib::outputname.'):
                            if len(k) > 0:
                                loc = k.find('=')
                                k = k[0:loc].strip().lstrip('u')
                                result.append(int(k))
                    case 'binary':
                        #SPECIFICALLY FOR ON/OFF, MAY NEED EXTENSION
                        result = int(reply.split('(')[1].strip(')'))
                    case 'binary array':
                        for idx, k in enumerate(reply.split('(')):
                            if idx > 0:                           
                                result.append(int(k.split(')')[0]))
                    case 'bits':
                        reply=reply.split('bits: ')[1]
                        result = [r for r in reply.split(' ') if len(r) == 2]
                        # 'WIENER-CRATE-MIB::outputStatus.u101 = BITS: 04 00 40 outputFailureMaxCurrent(5) outputLowCurrentRange(17)
                    case 'bits array':
                        for idx, bit in enumerate(reply.split('bits: ')):
                            if idx > 0:
                                result.append([r for r in bit.split(' ') if len(r) == 2])
                    case _:
                        self.WarnHandler(f"mode: {mode} not supported")                    
        return result

    def WarnHandler(self,warning_text):
        self.warnings.append(warning_text)
        if self.debug_mode: 
            self.last_cmd['error time'].append(time.monotonic()-self.start_time)
            self.last_cmd['Errors'].append(warning_text)
        print(warning_text)
        #TODO: pass these to front panel 

    def SendMultiple(self,mode = 'end'):
        ''' Usage Example: 
        SendMultiple('start')
        SetTargetVoltage(0,500)
        SetTargetVoltage(1,1000)
        SetPower(0,1)
        SetPower(1,1)
        SendMultiple('end')
        TODO: issue-this will block GUI! 
        '''
        mode=mode.lower()
        if mode == 'start':#Begin (or continue) listening to inputs
            self.gather_commands = 1
        elif mode == 'pause':#Stop listening, just pass inputs thru like normal
            self.gather_commands = 0
        elif mode == 'end':#Send then reset 
            self.gather_commands = 0
            self.Send(self.gathered_command_type, ' '.join(self.gathered_commands))
            if self.gathered_command_type == 'get':
                self.ParseReply()#not set up yet... 
                #TODO: parse by command before clearing
            
            self.gathered_commands = []
            self.gathered_command_type = ''
               

    ###### MAIN FUNCTIONS: BASIC ONE CHANNEL GET/SET/QUERY (LIST FROM ISEG MANUAL TABLE 2)#######
    def SetTargetVoltage(self, channel, voltage):
        ''' 
        Channel Voltage Set Target ::: [V] ::: float
        Channels can be found from Web Browser or GetAllNames(), form will be 600:607,700:707, etc
        '''
        if self.mode: #for testing
            # reply = 'WIENER-CRATE-MIB::outputVoltage.u604 = Opaque: Float: 5.000000000000 V'
            self.mimic[str(channel)]['v_target'] = voltage
        else:
            reply = self.Send('set', f"outputVoltage.u{channel} F {voltage}")

    def GetTargetVoltage(self, channel):
        ''' Channel Voltage Get Target (target set by SetTargetVoltage) ::: [V] ::: float '''
        if self.mode: 
            # reply = 'WIENER-CRATE-MIB::outputVoltage.u604 = Opaque: Float: 0.000000000000 V'
            result = self.mimic[str(channel)]['v_target']
        else: 
            reply = self.Send('get', f"outputVoltage.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result

    def SetCurrentLimit(self, channel, current):
        '''Channel Current Set Target (limit) ::: [mA] ::: float'''
        current = current / 1000
        if self.mode:
            self.mimic[str(channel)]['i_limit'] = current 
        else:
            self.Send('set', f"outputCurrent.u{channel} F {current}")

    def GetCurrentLimit(self, channel):
        '''Channel Current Get Target (limit set by SetCurrentLimit) ::: [mA] ::: float'''
        if self.mode: 
            # reply = 'WIENER-CRATE-MIB::outputCurrent.u604 = Opaque: Float: 0.001000000000 A'
            result = self.mimic[str(channel)]['i_limit']
        else: 
            reply = self.Send('get', f"outputCurrent.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result*1000
    
    def QueryVoltage(self, channel, mode = 'Sense'):
        ''' 
        Channel Actual Voltage Query ::: [V] ::: float
        Modes: 'Sense' or 'Terminal' 
        FOR HV MODULES, SENSE AND TERMINAL VALUES ARE IDENTICAL
        '''
        #TODO: determine difference between voltage types. Sense appears to be the useful one for now... 
        if self.mode: #example response to be parsed
            # reply = 'WIENER-CRATE-MIB::outputMeasurementSenseVoltage.u604 = Opaque: Float: 0.000000000000 V'
            result = self.mimic[str(channel)][f'v_{mode.lower()}']
        else:
            reply = self.Send('get', f"outputMeasurement{mode}Voltage.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result
        
    def QueryCurrent(self, channel):
        ''' Channel Actual Current Query ::: [mA] ::: float'''
        if self.mode:
            # reply = 'WIENER-CRATE-MIB::outputMeasurementCurrent.u604 = Opaque: Float: 0.001592196703 A'
            result = self.mimic[str(channel)]['i_actual']
        else:
            reply = self.Send('get', f"outputMeasurementCurrent.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result*1000

    def GetConfigMaxVoltage(self, channel, mode = 'Sense'):
        ''' 
        Channel Max Voltage Config (nominal) ::: [V] ::: float
        Types: 'Sense' or 'Terminal' 
        FOR HV MODULES, SENSE AND TERMINAL VALUES ARE IDENTICAL
        '''
        #TODO: figure out how this differs from other voltages
        if self.mode:
            # reply = 'WIENER-CRATE-MIB::outputConfigMaxSenseVoltage.u604 = Opaque: Float: 0.093592196703 V'
            result = self.mimic[str(channel)][f'v_configmax_{mode.lower()}']
        else:
            reply = self.Send('get', f"outputConfigMax{mode}Voltage.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result
    
    def GetConfigMaxCurrent(self, channel):
        ''' Channel Max Current Config (nominal) ::: [mA] ::: float'''
        #TODO: figure out how this differs from other currents
        if self.mode:
            # reply = 'WIENER-CRATE-MIB::outputConfigMaxCurrent.u604 = Opaque: Float: 0.093592196703 A'
            result = self.mimic[str(channel)]['i_configmax']
        else:
            reply = self.Send('get', f"outputConfigMaxCurrent.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result*1000

    def SetPower(self, channel, power_state = 0):
        '''
        Turn channel on (1) or off (0) ::: int
        Additonal states: resetEmergencyOff (2), setEmergencyOff (3), clearEvents(10)
        '''
        if self.mode:
            self.mimic[str(channel)]['pwr'] = power_state
        else:
            self.Send('set', f"outputSwitch.u{channel} i {power_state}")
        
    def QueryPower(self, channel):
        # returns integer, parse as binary
        if self.mode:
            # reply = 'WIENER-CRATE-MIB::outputSwitch.u604 = INTEGER: off(0)'
            result = self.mimic[str(channel)]['pwr']
        else:
            reply = self.Send('get', f"outputSwitch.u{channel}")
            result = self.ParseReply(reply, 'binary')
        return result
    
    def SetVoltageRate(self, channel, rate, direction =  'Rise'):
        ''' 
        Channel Voltage Set Rise Rate ::: [V/s] ::: float)
        direction: 'Rise' or 'Fall' 
        Range: 1 mV/s - (20% * VoltageNominal)
                OR 1 mV/s - 1%*VoltageNominal) IFF KILL_ENABLED
        TODO: finish validate input with Range
        Note: for most modules, rise & fall rates are tied together
        '''
        if rate < 0.001:
            rate = 0.001
            self.WarnHandler('Requested rate too low! Rate set to minimum 1 mV/s')
        
        if self.mode: 
            self.mimic[str(channel)]['v_rate'] = rate
        else: 
            self.Send('set', f"outputVoltage{direction}Rate.u{channel} F {rate}")
    
    def GetVoltageRate(self, channel, direction =  'Rise'):
        ''' 
        Channel Voltage Get Rise Rate ::: [V/s] ::: float)
        directions: 'Rise' and 'Fall' 
        Note: for most modules, rise & fall rates are tied together
        '''
        if self.mode: 
            # reply = 'WIENER-CRATE-MIB::outputVoltageRiseRate.u604 = Opaque: Float: 0.000000000000 V/s'
            result = self.mimic[str(channel)]['v_rate']
        else: 
            reply = self.Send('get', f"outputVoltage{direction}Rate.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result

    def SetCurrentRate(self, channel, rate, direction =  'Rise'):
        ''' 
        Channel Current Set Rise Rate ::: [mA/s] ::: float)
        directions: 'Rise' and 'Fall' 
        Note: for most modules, rise & fall rates are tied together
        '''
        rate = rate/1000
        if self.mode: 
            self.mimic[str(channel)]['i_rate'] = rate
        else: 
            self.Send('set', f"outputCurrent{direction}Rate.u{channel} F {rate}")
    
    def GetCurrentRate(self, channel, direction =  'Rise'):
        ''' 
        Channel Current Get Rise Rate ::: [mA/s] ::: float)
        directions: 'Rise' and 'Fall' 
        Range: 2% - 100% * CurrentNominal
        TODO: validate range
        Note: for most modules, rise & fall rates are tied together
        '''
        if self.mode: 
            # reply = 'WIENER-CRATE-MIB::outputCurrentRiseRate.u604 = Opaque: Float: 0.093592196703 A/s'
            result = self.mimic[str(channel)]['i_rate']
        else: 
            reply = self.Send('get', f"outputCurrent{direction}Rate.u{channel}")
            result = self.ParseReply(reply, 'float')
        return result*1000
    ### ADDITIONAL SINGLE CHANNEL FUNCTIONS #####
    def SetTripTimeMaxCurrent(self, channel, time):
        # For HV only, time in ms
        #TODO: validation range 16-4000 ms
        if self.mode: 
            self.mimic[str(channel)]['i_triptimemax'] = time
        else:
            self.Send('set', f'outputTripTimeMaxCurrent.u{channel} i {int(time)}')

    def GetTripTimeMaxCurrent(self, channel):
        # For HV only, time in ms 
        if self.mode: 
            result = self.mimic[str(channel)]['i_triptimemax']
        else: 
            reply = self.Send('get','outputTripTimeMaxCurrent')
            result = self.ParseReply(reply,'integer')
        return result
        
    ### GROUP FUNCTIONS: GET/QUERY ALL CHANNELS ####
    def GetAllTargetVoltages(self):
        #Output all target voltages
        if self.mode: 
            result = [self.GetTargetVoltage(ch) for ch in self.mimic['crate']['channels']]
        else: 
            reply = self.Send('walk', 'outputVoltage')
            result = self.ParseReply(reply, 'float array')
        return result
    
    def GetAllCurrentLimits(self):
        #Output all current limits ::: [mA] ::: list of floats
        if self.mode: 
            result = [self.GetCurrentLimit(ch)/1000 for ch in self.mimic['crate']['channels']]
        else: 
            reply = self.Send('walk','outputCurrent')
            result = self.ParseReply(reply, 'float array')
        return [r * 1000 for r in result]
    
    def QueryAllVoltages(self, mode = 'Sense'):
        ''' Output all actual voltages
        Modes: 'Sense' or 'Terminal' 
        FOR HV MODULES SENSE AND TERMINAL VALUES ARE IDENTICAL'''
        if self.mode: 
            result = [self.QueryVoltage(ch,mode) for ch in self.mimic['crate']['channels']]
        else: 
            reply = self.Send('walk', f'outputMeasurement{mode}Voltage')
            result = self.ParseReply(reply, 'float array')
        return result

    def QueryAllCurrents(self):
        # Output all actual currents ::: [mA] ::: list of floats
        if self.mode: 
            result = [self.QueryCurrent(ch)/1000 for ch in self.mimic['crate']['channels']]
        else:
            reply = self.Send('walk', f'outputMeasurementCurrent')
            result = self.ParseReply(reply, 'float array')
        return [r * 1000 for r in result]

    def GetAllConfigMaxVoltages(self, mode = 'Sense'):
        # Modes: 'Sense' or 'Terminal' 
        if self.mode:
            result = [self.GetConfigMaxVoltage(ch,mode) for ch in self.mimic['crate']['channels']]
        else: 
            reply = self.Send('walk', f"outputConfigMax{mode}Voltage")
            result = self.ParseReply(reply, 'float array')
        return result

    def GetAllConfigMaxCurrents(self):
        # desc ::: [mA] ::: list of floats
        if self.mode: 
            result = [self.GetConfigMaxCurrent(ch)/1000 for ch in self.mimic['crate']['channels']]
        else:
            reply = self.Send('walk', f"outputConfigMaxCurrent")
            result = self.ParseReply(reply, 'float array')
        return [r * 1000 for r in result]
    
    def GetAllVoltageRates(self, direction =  'Rise'):
        if self.mode: 
            result = [self.GetVoltageRate(ch,direction) for ch in self.mimic['crate']['channels']]
        else:
            reply = self.Send('walk', f"outputVoltage{direction}Rate")
            result = self.ParseReply(reply, 'float array')
        return result       
    
    def GetAllCurrentRates(self, direction =  'Rise'):
        # desc ::: [mA] ::: list of floats
        if self.mode: 
            result = [self.GetCurrentRate(ch)/1000 for ch in self.mimic['crate']['channels']]
        else: 
            reply = self.Send('walk', f"outputCurrent{direction}Rate")
            result = self.ParseReply(reply, 'float array')
        return [r * 1000 for r in result]

    def GetAllTripTimeMaxCurrent(self):
        ''' desc ::: [ms] ::: list of integers 
        '''
        if self.mode: 
            result = [self.GetTripTimeMaxCurrent(ch) for ch in self.mimic['crate']['channels']]
        else: 
            reply = self.Send('walk', f"outputTripTimeMaxCurrent")
            result = self.ParseReply(reply, 'integer array')
        return result
    ### ADDITIONAL FUCTIONS ####
    def GetAllNames(self):
        #Output all channel names in an array
        if self.mode: 
            # 'WIENER-CRATE-MIB::outputName.u100 = STRING: 100 \\ WIENER-CRATE-MIB::outputName.u101 = STRING: 101'
            result = [0,1,2,100,101,102,200,201,202,300,301,302,500,501,502,600,601,602,800,801,802]
            result =[0,1,2,3,4,5,6,7]
            result =[0,1,2,3,4,5,6,7,100,101,500,501]

        else: 
            reply = self.Send('walk', 'outputName')
            result = self.ParseReply(reply, 'string')
        return result

    def SetPowerCrate(self, power_state = None):
        if power_state is None:
            power_state = int(not self.QueryPowerCrate())
        if self.mode:
            self.mimic['crate']['pwr'] = power_state
        else:
            self.Send('set', f"sysMainSwitch.0 i {power_state}")
    
    def QueryPowerCrate(self):
        #returns integer, parse as binary
        if self.mode:
            # reply = 'WIENER-CRATE-MIB::sysMainSwitch.0 = INTEGER: ON(1)'
            result = self.mimic['crate']['pwr']
        else: 
            reply = self.Send('get', "sysMainSwitch.0")
            result = self.ParseReply(reply, 'binary')
        
        return int(result)

    def QueryAllPowers(self):
        # desc ::: list of integers (parse as binary array)
        if self.mode: 
            result = [self.QueryPower(ch) for ch in self.mimic['crate']['channels']]
        else: 
            reply = self.Send('walk', f"outputSwitch")
            result = self.ParseReply(reply, 'binary array')
        return result    
    
    def ClearModule(self,module):
        self.Send('set',f'moduleDoClear.ma{module} i 1')

    def GetModuleVoltageRate(self, module):
        ''' 
        Module Voltage Ramp Rate ::: [%] ::: float
        For HV modules only, a percentage of the nominal voltage of the module
        '''
        # if self.mode: 
            # reply = ''
            # result = '''
        # else: 
        reply = self.Send('get', f"moduleRampSpeedVoltage.ma{module}")
        result = self.ParseReply(reply, 'float')
        # v_nominal = self.GetConfigMaxVoltage()
        return result

    def GetModuleCurrentRate(self, module):
        ''' 
        Module Current Ramp Rate ::: [%] ::: float
        For HV modules only, a percentage of the nominal current of the module
        '''
        # if self.mode: 
            # reply = ''
            # result = []
        # else: 
        reply = self.Send('get', f"moduleRampSpeedCurrent.ma{module}")
        result = self.ParseReply(reply, 'float')
        return result
    
    def SetModuleVoltageRate(self, module, pct_rate):
        #TODO: Check if input is in % or V/s and update descs
        self.Send('set', f"moduleRampSpeedVoltage.ma{module} F {pct_rate}")
    
    def SetModuleCurrentRate(self, module, pct_rate):
        ''' 
        Channel Current Set Rise Rate ::: [%] ::: float)
        '''
        # if self.mode: 
        #     self.mimic[] = rate
        # else: 
        self.Send('set', f"moduleRampSpeedCurrent.ma{module} F {pct_rate}")
    
    def GetAllModuleVoltageRate(self):
        # Returned as percentage of the nominal voltage of the HV channels
        reply = self.Send('walk', f"moduleRampSpeedVoltage")
        result = self.ParseReply(reply, 'float array')
        return result
    
    def GetAllModuleCurrentRate(self):
        # Returned as percentage of the nominal current of the HV channels
        reply = self.Send('walk', f"moduleRampSpeedCurrent")
        result = self.ParseReply(reply, 'float array')
        return result
    #source: iseg snmp maual pg 26
    #returns:  'WIENER-CRATE-MIB::moduleRampSpeedCurrent.ma0 = Opaque: Float: 50.000000000000 %\r\nWIENER-CRATE-MIB::moduleRampSpeedCurrent.ma7 = Opaque: Float: 50.000000000000 %\r\nWIENER-CRATE-MIB::moduleRampSpeedCurrent.ma8 = Opaque: Float: 50.000000000000 %'
    #note: in percentage of outputConfigMaxCurrent (but this doesnt agree with channel ramp rate... )
    #TODO: can set all at once? probably not... 
    ##### WORKS IN PROGRESS####    
    def GetStatus(self, channel_or_module = None, mode = 'Crate',quick = False):
        '''Modes: 
        'crate','channel','module','module event'
        Module Events are static (vs 'module' -> flags that are transient)
                
        '''
        if self.mode: 
            reply = 'WIENER-CRATE-MIB::outputStatus.u101 = BITS: 04 00 40 outputFailureMaxCurrent(5) outputLowCurrentRange(17)'
        else: 
            hex_length = 2 # default length for everything but channel
            bit_length = 16
            if mode == 'crate':
                reply = self.Send('get','sysStatus.0')
            elif mode == 'channel':
                reply = self.Send('get', f'outputStatus.u{channel_or_module}')
                hex_length = 3
                bit_length = 24
            elif mode == 'module':
                self.WarnHandler('module status handling not set up - use "module event" instead')
                reply = self.Send('get',f'outputStatus.ma{channel_or_module}')
            elif mode == 'module event':
                reply = self.Send('get',f'moduleEventStatus.ma{channel_or_module}')
            else:
                self.WarnHandler(f"Mode '{mode}' is not a valid input to GetStatus")

        parsed_reply = self.ParseReply(reply,'bits')
        while len(parsed_reply)<hex_length:
            parsed_reply.append('00')
        if quick:
            return self.ParseStatus(parsed_reply,mode,bit_length,quick)
        else: 
            [name,flag,desc,active_bits] = self.ParseStatus(parsed_reply,mode,bit_length,quick)  
            return [name,flag,desc,active_bits]

    def GetAllStatuses(self,mode,quick = False):
        hex_length = 2
        bit_length = 16
        if mode == 'module':
            reply = self.Send('walk','moduleStatus')
        if mode =='channel':
            reply  = self.Send('walk','outputStatus')
            hex_length = 3
            bit_length = 24
        parsed_reply = self.ParseReply(reply,'bits array')
        status=[]
        for p in parsed_reply: 
            while len(p)<hex_length:
                p.append('00')
            status.append(self.ParseStatus(p,mode,bit_length,quick))
        return status

    def TestConnection(self):
        '''Check for instrument response'''
        result = self.Send()
        print(result)

    def ParseStatus(self,status, mode, bit_length, quick = False):
        #TODO: handle these statuses, add more desc
        ''' MSB is bit 0. Also, bits are chunked so each status is its own hex-pseduo bit (2digit)
        A perplexing choice of convention... 
        bit_length is 16 for all but channel status (24 for channel status)
        '''
        full_status = ''.join(status)
        int_status = int(full_status,16)
        binary_status=format(int(full_status,16),f'0{bit_length}b')
        if quick: 
            return binary_status
            #to get single bit from status, take int(binary_status[bit#]) == True
        else: 
            active_bits = []
            for idx, x in enumerate(binary_status):
                if int(x):
                    active_bits.append(idx)
            name = []
            flag = []
            desc = []
            if mode == 'crate':
                for i in active_bits: 
                    match i: 
                        case 0:#bit0 = 'crate on flag' #ACTUALLY BIT 15!!! 
                            name.append('ON')
                            flag.append('Main On')
                            desc.append('Crate status flag "Main On". The crate is switched on.')
                        case 1:#bit1 = 'main inhibit'#BIT 14!!
                            name.append('INHIBIT')
                            flag.append('Main Inhibit')
                            desc.append('An external (hardware-) interlock of the complete system is active.')
                        case 2:#bit2 = 'local control only'#BIT 13
                            name.append('LOCAL')
                            flag.append('Local Control Only')
                            desc.append('Only local control is possible (CAN BUS write access denied).')
                        case 3:#bit3 = 'input error'#BIT 12
                            name.append('INPUT ERROR')
                            flag.append('Input Failure')
                            desc.append('An input failure such as a power fail occurred.')
                        case 4:#bit4 = 'channel error (see channel status)'#BIT 11
                            name.append('CHANNEL ERROR')
                            flag.append('Channel Error')
                            desc.append('A channel error occurred. More details are available from the channel status flags.')
                        case 5:#bit5 = 'fan tray failure'#BIT 10
                            name.append('FAN')
                            flag.append('Fan Tray Failure')
                            desc.append('A fan tray failure occurred.')
                        case 8:#bit8 = 'incompatible power supply and rack'#BIT 7
                            name.append('INCOMPAT')
                            flag.append('Plug and Play Incompatible')
                            desc.append('A wrong power supply and rack have been connected.')
                        case 9:#bit9 = 'system bus reset signal'#BIT 6
                            name.append('RESET')
                            flag.append('Bus Reset')
                            desc.append('The system bus (e.g. VME or CPCI) reset signal is active.')
                        case 10:#bit10= 'system power supply has derating (DEG) signal active' #BIT 5
                            name.append('DERATING')
                            flag.append('Supply Derating')
                            desc.append('The first system power supply has the DEG signal active.')
                        case 11:#bit11= 'system power supply has failure (FAL) signal active' #BIT 4
                            name.append('SUPPLY')
                            flag.append('Supply Failure')
                            desc.append('The first system power supply has the FAL signal active.')
                        
            elif 'module' in mode:
                #NOTE: FOR MODULE FLAGS, INVERTED BITS ARE NOT INVERTED. Otherwise identical! 
                mask = b'0000 0000 1110 1110'#inverted bits in MSB order. bitwise sum should flip to indicate active states
                #not implemented, ick! 
                #Status behavior: sticky, i.e. indicates that the flag was triggered, must be cleared to remove
                for i in active_bits: 
                    match i: 
                        case 0:#bit0 (actually bit 15)
                            name.append('ADJ')
                            flag.append('Fine Adjustment Active')
                            desc.append('In fine adjustment mode: an additional compensation loop in the firmware adjusts Vmeas to the user set value for Vset. Fine adjustment takes some time to be effective after enabling the option.')
                        case 2:#bit2
                            name.append('LIVE INS')
                            flag.append('Live Insertion')
                            desc.append('Set if a hot plug is prepared for the module. Not available for all power supplies.')
                        case 3:#bit3
                            name.append('HV')
                            flag.append('High Voltage On')
                            desc.append('At least one channel delivers a high voltage.')
                        case 4:#bit4
                            name.append('SERVICE')
                            flag.append('Maintenance Required')
                            desc.append('The module has to be returned for maintenance.')
                        case 5:#bit5
                            name.append('V LIMIT')
                            flag.append('Hardware Voltage Limit Exceeded')
                            desc.append("The hardware voltage limit isn't in the correct range. Not available for all hardware, only HV distributor modules with current mirror.")
                        case 6:#bit6
                            name.append('IN ERROR')
                            flag.append('Input Error')
                            desc.append('A set value is out of range, has a bad polarity sign or other communication problem. Channel input errors are also reported here.')
                        case 8:#bit8
                            #inverted flag
                            name.append('SUM ERROR')
                            flag.append('Sum Error')
                            desc.append('A critical event occurred in at least one channel. The concerned channel status flags are: I LIMIT, V LIMIT, TRIP, INHIBIT, V BOUND, I BOUND.')
                        case 9:#bit9
                            #TODO: Query just this bit for a lot of utility.. 
                            #inverted flag
                            name.append('RAMP')
                            flag.append('Ramping')
                            desc.append('At least one channel is ramping up or down.')
                        case 10:#bit10
                            #inverted flag
                            name.append('SAFETY')
                            flag.append('Safety Loop Open')
                            desc.append("The safety loop is open. The SL connector on the front panel is potential free and requires an external 5-20 mA current to be closed. The internal optocoupler has a voltage drop of approx. 3 V. The safety loop needs to be activated by removing the jumper on the module's bottom side.")
                        case 11:#bit11
                            name.append('EVENT')
                            flag.append('Event Active')
                            desc.append('Set if a module event is active and the masks have been set accordingly. The module events that will trigger this flag are: SAFETY, ... list appears to be incomplete')
                        case 12:#bit12
                            #inverted flag
                            name.append('MOD ERROR')
                            flag.append('Module Error')
                            desc.append('One of the following module flags is active : SUM ERROR, MAX TEMP, SUPPLY, SAFETY.')
                        case 13:#bit13
                            #inverted flag
                            name.append('SUPPLY')
                            flag.append('Power Supply Failure')
                            desc.append("The module's power supply fails.")
                        case 14:#bit14
                            #inverted flag
                            name.append('MAX TEMP')
                            flag.append('Temperature High')
                            desc.append('The temperature of the module is too high.')
                        case 15:#bit15
                            #TODO: Query just this bit for lots of behavior info
                            name.append('KILL')
                            flag.append('Kill Enabled')
                            desc.append('The "Kill" option has been enabled for the module. If "Kill" is enabled, several channel status flags will lead to a shutdown of the channel. These status flags are TRIP, I LIMIT, V LIMIT, I BOUND, V BOUND, ARC.')
            elif mode == 'channel':
                #NOTE: Channel statuses are different for LV and HV modules! this is for HV modules only
                for i in active_bits: 
                    match i: 
                        case 0:#Bit 0 (actually bit 23 in conventional ordering)
                            name.append('ON')
                            flag.append('Channel On')
                            desc.append('The channel has been switched on.')
                        case 1:#Bit 1 (actually bit 22)
                            name.append('INHIBIT')
                            flag.append('External Inhibit Detected')
                            desc.append('An external inhibit signal is detected on the inhibit pin of the module. The channel will be shut down according to the "External Inhibit Action" in the channel properties. Also set if the crate controller interlock is active.')
                        case 4:#Bit 4 (actually bit 19)
                            name.append('V LIMIT')
                            flag.append('Voltage Limit Exceeded')
                            desc.append('Set if the voltage exceeds the value defined for the hardware voltage limit (Vmax potentiometer). If the "Kill" option has been enabled for the module, the channel will be shut down.')
                        case 5:#Bit 5 (actually bit 18)
                            name.append('TRIP')
                            flag.append('Current Trip Occurred')
                            desc.append('Set if Imeas exceeds Iset and the "Kill" option is enabled for the module or a delayed trip action has been defined. If a delayed trip is used the flag will only be set after Imeas exceeded Iset for a user-defined delay time. If the "Kill" option is not enabled for the module and no delayed trip action has been defined,the module will operate in current control mode when the output current reaches Iset.')
                        case 10:#Bit 10 (actually bit 13)
                            name.append('CC')
                            flag.append('Constant Current Mode')
                            desc.append('If module option "kill" has been disabled and no delayed trip action has been defined: this flag is set if the current defined for Iset is reached. The channel operates in current control mode. If the module option "kill" has been enabled or a delayed trip action has been defined: this flag is never set. A current trip will occur instead.')
                        case 11:#Bit 11 (actually bit 12)
                            name.append('RAMP UP')
                            flag.append('Ramping Up')
                            desc.append('The channel is ramped up')
                        case 12:#Bit 12 (actually bit 11)
                            name.append('RAMP DOWN')
                            flag.append('Ramping Down')
                            desc.append('The channel is ramped down')
                        case 13:#Bit 13 (actually bit 10)
                            name.append('KILL')
                            flag.append('Kill Enabled')
                            desc.append('The "Kill" option has been enabled for the module. If "Kill" is enabled, several channel status flags will lead to a shutdown of the channel. These status flags are TRIP, I LIMIT, V LIMIT, I BOUND, V BOUND.')
                        case 14:#Bit 14 (actually bit 9)
                            name.append('EMCY')
                            flag.append('Emergency Off')
                            desc.append('Emergency off is triggered by the user. The channel is shut down without ramp. The emergency has to be cleared before the channel can be switched on again.')
                        case 15:#Bit 15 (actually bit 8)
                            name.append('ADJ')
                            flag.append('Fine Adjustment Active')
                            desc.append('The module is in fine adjustment mode. An additional compensation loop in the firmware adjusts Vmeas to the user set value for Vset. Fine adjustment takes some time to be effective after enabling the option.')
                        case 16:#Bit 16 (actually bit 7)
                            name.append('CV')
                            flag.append('Constant Voltage Mode')
                            desc.append('Set if the voltage defined for Vset is reached. The channel operates in voltage control mode. Also active when the channel is ramped up or down.')
                        case 17:#Bit 17 (actually bit 6)
                            name.append('LCR')
                            flag.append('Low Current Measurement Range')
                            desc.append('Set if the low current range is used for current measurements. This increases the precision of Imeas. Only available for high precision power supplies.')
                        case 18:#Bit 18 (actually bit 5)
                            name.append('V BOUND')
                            flag.append('Vbound Exceeded')
                            desc.append('Set if | Vmeas - Vset | > Vbound. If the "Kill" option has been enabled for the module, the channel will be shut down.')
                        case 19:#Bit 19 (actually bit 4)
                            name.append('I LIMIT')
                            flag.append('Current Limit Exceeded')
                            desc.append('Set if the current exceeds the value defined for the hardware current limit (Imax potentiometer). If the "Kill" option has been enabled for the module, the channel will be shut down.')
            return [name, flag, desc, active_bits[0:bit_length]] 
           
    def QueryChannel(self, channel):
        r'''Get all channel info (Voltage, Current, On/Off Status)'''
        result = [self.QueryVoltage(channel), self.QueryCurrent(channel), self.QueryPower(channel)]
    
#TODO: see if moduleRampSpeedVoltage is preferable to current ramping fx
    
### FUNCTIONS IN PROG ADDING: 
# outputSupervisionBehavior
# walk? yes 
# write? yes
#source: iseg snmp maual pg 19
#returns:  INTEGER: 4160\r\nWIENER-CRATE-MIB::outputSupervisionBehavior.u807 = INTEGER: 4160'

#outputTripActionMaxCurrent
#outputTripActionExternalInhibit
#same as above

#moduleDescription, returns Company name, firmware name, channel number, serial number
#'WIENER-CRATE-MIB::moduleDescription.ma0 = STRING: "iseg, E08F2, 08, 7200262, 06.78"\r\nWIENER-CRATE-MIB::moduleDescription.ma7 = STRING: "iseg, E08F2, 08, 7200296, 07.09"\r\nWIENER-CRATE-MIB::moduleDescription.ma8 = STRING: "iseg, E08F2, 08, 7200260, 06.78"'

#groupsSwitch: # For HV modules this variable allows to trigger or clear an emergency off. It is the only possibility to
# configure the “fine adjust” and the “kill” options. It also allows to clear events.

#bad cmd example reply: 'outputTable.u1: Unknown Object Identifier (Sub-id not found: outputTable -> u1)'
#bad channel example reply: 'WIENER-CRATE-MIB::outputEntry = No Such Object available on this agent at this OID'
#bad module example reply: 'moduleEventStatus.ma12: Unknown Object Identifier (Index out of range: ma12 (moduleIndex))'

#To increase voltage ramp range: 
# a ramp speed higher than 1% isn’t accepted unless the following steps are taken:
# •disable the “Kill Enable” option for the module. See the “groupsSwitch” SNMP variable.
# •set the delayed trip time to 0 for all channels of the module. See the SNMP variable “outputTripTimeMaxCurrent”.
# •set delayed trip action to “ignore if a current trip occurs” for all channels of the module. This
# can be achieved by writing the appropriate bits in “outputSupervisionBehavior”.
