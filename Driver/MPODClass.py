import subprocess
import os
import warnings
from datetime import datetime
import pexpect as px
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
        ### FOR DEBUG ONLY: ###
        d = {'i_limit':1.0123456789012, 'i_rate':2.1234567890123, 'i_actual':0.11234567890123, 'v_target':2000.1234567890123, 
        'v_rate':5.1234567890123, 'v_sense':0.0123456789012, 'v_terminal': 0.1234567890123,'pwr':0,'v_configmax_sense':5000.1234567890123,
        'v_configmax_terminal': 5000.1234567890123,'i_configmax':1.1234567890123, 'i_triptimemax':500}
        d_pwr = {'pwr':1,'channels':self.GetAllNames()}
        self.mimic = {'crate': d_pwr}
        for ch in d_pwr['channels']:
            self.mimic[str(ch)] = dict(d)
        #######################
        # os.environ["MIBS"] = "+WIENER-CRATE-MIB"
        # if os.path.isfile(self.mibdir + "/WIENER-CRATE-MIB.txt"):
            # os.environ["MIBDIRS"] = self.mibdir
        # else: 
            # raise RuntimeError(f"MIB file was not found in {self.mibdir}")
        ##example command : "snmpget -v 2c -Op .12 -m +WIENER-CRATE-MIB -c guru 169.254.107.70 outputPower.u0"
    def Send(self,cmd_type = 'walk', cmd = ''):
        '''Base command struct and MPODCrate communication functions'''
        #result = subprocess.run([cmd],shell = True,capture_output = True)
        if cmd_type == 'walk':#check connection
            if cmd == '': #use lower precision
                cmd = f"snmpwalk -v 2c -m +WIENER-CRATE-MIB -c public {self.IP} " + cmd
            else: # require higher precision
                cmd = f"snmpwalk -v 2c -Op .12 -m +WIENER-CRATE-MIB -c public {self.IP} " + cmd
        elif cmd_type == 'set':
            cmd = f"snmpset -v 2c -Op .12 -m +WIENER-CRATE-MIB -c guru {self.IP} " + cmd
        elif cmd_type == 'get':
            cmd = f"snmpget -v 2c -Op .12 -m +WIENER-CRATE-MIB -c guru {self.IP} " + cmd
        else:
            warnings.warn(cmd_type + ' is invalid command type')
        try:
            # result = subprocess.run(cmd.split(), capture_output = True)#doesnt work in python! 
            # result_parsed = str(result.stdout).lstrip('b\'').rstrip('\'').rstrip('\n')
            result = px.run(cmd)
            result_parsed = result.decode().rstrip('\n').rstrip('\r')
        except:# subprocess.CalledProcessError as err:
            warnings.warn(f"SNMP command failed. Command: {cmd})")#, Error: {err.stderr}")
            result_parsed=None
            #raise RuntimeError(f"SNMP command failed: {err.stderr.strip()}")
        return result_parsed#, result, cmd#, result.stderr 
    
    def ParseReply(self, reply, mode, source = None):
        if reply is None: 
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
                    #SPECIFICALLY FOR FINDING OUTPUT NAMES. MAY NEED EXTENSION
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
                case _:
                    warnings.warn(f"mode: {mode} not supported")

        return result
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
            warnings.warn('Requested rate too low! Rate set to minimum 1 mV/s')
        
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
        # Output all actual voltages
        # Modes: 'Sense' or 'Terminal' 
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
        #TODO: get module info
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
    
    #TODO: can set all at once? 
    ##### WORKS IN PROGRESS####    
    def GetStatus(self, channel):
        #TODO: Get this up and running - clearly important!! 
        ''' 
        Notes: Bitstrings will be harder to parse than text... likely hex
        for best examples search BITS:
                ***SEE MIB FILE****
        Known statuses: 
        outputEnableKill (13)
        outputEmergencyOff (14)

        There are more statuses with more complex behavior (see MPOD manual) such as:
        outputFailureMaxCurrent(5) 
        outputLowCurrentRange(17)
        '''
        print('Work in progress')
        if self.mode: 
            reply = 'WIENER-CRATE-MIB::outputStatus.u101 = BITS: 04 00 40 outputFailureMaxCurrent(5) outputLowCurrentRange(17)'
        else: 
            reply = self.Send('get', f'outputStatus.u{channel}')
        result = self.ParseReply(reply, 'bits')
        
    def TestConnection(self):
        '''Check for instrument response'''
        result = self.Send()
        print(result)
     
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
#same as above

#outputTripActionExternalInhibit
#same as above

# moduleRampSpeedVoltage
# walk? yes 
# write? yes
#source: iseg snmp maual pg 26
#returns:  'WIENER-CRATE-MIB::moduleRampSpeedCurrent.ma0 = Opaque: Float: 50.000000000000 %\r\nWIENER-CRATE-MIB::moduleRampSpeedCurrent.ma7 = Opaque: Float: 50.000000000000 %\r\nWIENER-CRATE-MIB::moduleRampSpeedCurrent.ma8 = Opaque: Float: 50.000000000000 %'
#note: in percentage of outputConfigMaxCurrent (but this doesnt agree with channel ramp rate... )

#moduleRampSpeedCurrent
#same as above

#moduleStatus

#moduleEventstatus
#moduleDoClear = 1 to clear status bit 
#   integer tag: i

#moduleDescription, returns Company name, firmware name, channel number, serial number
#'WIENER-CRATE-MIB::moduleDescription.ma0 = STRING: "iseg, E08F2, 08, 7200262, 06.78"\r\nWIENER-CRATE-MIB::moduleDescription.ma7 = STRING: "iseg, E08F2, 08, 7200296, 07.09"\r\nWIENER-CRATE-MIB::moduleDescription.ma8 = STRING: "iseg, E08F2, 08, 7200260, 06.78"'

#bad cmd example reply: 'outputTable.u1: Unknown Object Identifier (Sub-id not found: outputTable -> u1)'
#bad channel example reply: 'WIENER-CRATE-MIB::outputEntry = No Such Object available on this agent at this OID'
#bad module example reply: 'moduleEventStatus.ma12: Unknown Object Identifier (Index out of range: ma12 (moduleIndex))'
