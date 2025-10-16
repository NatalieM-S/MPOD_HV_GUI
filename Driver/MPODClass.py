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
        self.mode = mode#mode: 0, driver, 1, debug (not connected), 
        self.dummy_instrument = [0, 1, 2, 13, 14, 15, 1, 0]#1 ch instrument mimic[i_limit, i_rate, i_actual, v_target, v_rate, v_actual, pwr_crate, pwr_ch]
        # os.environ["MIBS"] = "+WIENER-CRATE-MIB"
        # if os.path.isfile(self.mibdir + "/WIENER-CRATE-MIB.txt"):
            # os.environ["MIBDIRS"] = self.mibdir
        # else: 
            # raise RuntimeError(f"MIB file was not found in {self.mibdir}")
        # example = "snmpget -v 2c -Op .12 -m +WIENER-CRATE-MIB -c guru 169.254.107.70 outputPower.u0"
    def Send(self,cmd_type = 'walk', cmd = ''):
        '''Base command struct and MPODCrate communication functions'''
        #result = subprocess.run([cmd],shell = True,capture_output = True)
        if cmd_type == 'walk':#check connection
            #cmd = f"snmpwalk -v 2c -m +WIENER-CRATE-MIB -c public {self.IP} " + cmd#rm -m from all
            cmd = f"snmpwalk -v 2c -m +WIENER-CRATE-MIB -c public {self.IP} " + cmd
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
    
    def ParseReply(self, reply, mode):
        if reply is None: 
            result = None
        else:
            match mode:
                case 'float':
                    #parse float
                    loc = reply.find('Float:')
                    result = float(reply[loc+6:-3])
                case 'string':
                    #SPECIFICALLY FOR FINDING OUTPUT NAMES. MAY NEED EXTENSION
                    result = []
                    for k in reply.split('WIENER-CRATE-MIB::outputName.'):
                        if len(k) > 0:
                            loc = k.find('=')
                            k = k[0:loc].strip().lstrip('u')
                            result.append(int(k))
                case 'integer':
                    #SPECIFICALLY FOR ON/OFF, MAY NEED EXTENSION
                    result = int(reply.split('(')[1].strip(')'))
                case _:
                    warnings.warn(f"mode: {mode} not supported")

        return result
    ###### MAIN FUNCTIONS (LIST FROM ISEG MANUAL TABLE 2)#######
    def SetTargetVoltage(self, channel, voltage):
        ''' 
        Channel Voltage Set Target ::: [V] ::: float
        Channels can be found from Web Browser or GetAllNames(), form will be 600:607,700:707, etc
        '''
        if self.mode: #for testing
            # reply = f'WIENER-CRATE-MIB::outputVoltage.u604 = Opaque: Float: 5.000000000000 V'
            # reply = f'WIENER-CRATE-MIB::outputVoltage.u604 = Opaque: Float: {self.dummy_instrument[3]:.12f} V'
            self.dummy_instrument[3] = voltage
            print(f'VTarget would be set to {voltage} V on Ch{channel}')
        else:
            reply = self.Send('set', f"outputVoltage.u{channel} F {voltage}")
        # result = self.ParseReply(reply, 'float')
        #TODO: see if result is needed/useful or not. Will be neglected for further set cmds for now
        # return result

    def GetTargetVoltage(self, channel):
        ''' Channel Voltage Get Target (target set by SetTargetVoltage) ::: [V] ::: float '''
        if self.mode: 
            reply = f'WIENER-CRATE-MIB::outputVoltage.u604 = Opaque: Float: {self.dummy_instrument[3]:.12f} V'
            #5.000000000000 V'
        else: 
            reply = self.Send('get', f"outputVoltage.u{channel}")
        result = self.ParseReply(reply, 'float')
        return result

    def SetCurrentLimit(self, channel, current):
        '''Channel Current Set Target (limit) ::: [mA] ::: float'''
        current = current / 1000
        if self.mode:
            print(f'ILimit would be set to {current} V on Ch{channel}')
        else:
            self.Send('set', f"outputCurrent.u{channel} F {current}")

    def GetCurrentLimit(self, channel):
        '''Channel Current Get Target (limit set by SetCurrentLimit) ::: [mA] ::: float'''
        if self.mode: 
            reply = 'WIENER-CRATE-MIB::outputCurrent.u604 = Opaque: Float: 0.001000000000 A'
        else: 
            reply = self.Send('get', f"outputCurrent.u{channel}")
        result = self.ParseReply(reply, 'float')
        return result*1000
    
    def QueryVoltage(self, channel, mode = 'Sense'):
        ''' 
        Channel Actual Voltage Query ::: [V] ::: float
        Types: 'Sense' or 'Terminal' 
        '''
        #TODO: determine difference between voltage types. Sense appears to be the useful one for now... 
        if self.mode: #example response to be parsed
            reply = f'WIENER-CRATE-MIB::outputMeasurement{mode}Voltage.u604 = Opaque: Float: {self.dummy_instrument[5]:.12f} V'
        else:
            reply = self.Send('get', f"outputMeasurement{mode}Voltage.u{channel}")
        result = self.ParseReply(reply, 'float')
        return result
        
    def QueryCurrent(self, channel):
        ''' Channel Actual Current Query ::: [mA] ::: float'''
        if self.mode:
            reply = 'WIENER-CRATE-MIB::outputMeasurementCurrent.u604 = Opaque: Float: 0.001592196703 A'
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
            reply = f'WIENER-CRATE-MIB::outputConfigMax{mode}Voltage.u604 = Opaque: Float: 0.093592196703 V'
        else:
            reply = self.Send('get', f"outputConfigMax{mode}Voltage.u{channel}")
        result = self.ParseReply(reply, 'float')
        return result
    
    def GetConfigMaxCurrent(self, channel):
        ''' Channel Max Current Config (nominal) ::: [mA] ::: float'''
        #TODO: figure out how this differs from other currents
        if self.mode:
            reply = 'WIENER-CRATE-MIB::outputConfigMaxCurrent.u604 = Opaque: Float: 0.093592196703 A'
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
            self.dummy_instrument[-1] = power_state
            print(f'power on ch{channel} would be switched to {power_state}')
        else:
            self.Send('set', f"outputSwitch.u{channel} i {power_state}")
        
    def QueryPower(self, channel):
        if self.mode:
            reply = f'WIENER-CRATE-MIB::outputSwitch.u604 = INTEGER: off({self.dummy_instrument[-1]:.0f})'
        else:
            reply = self.Send('get', f"outputSwitch.u{channel}")
        result = self.ParseReply(reply, 'integer')
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
            self.dummy_instrument[4] = rate
            print(f'VRate would be set to {rate} on ch{channel}')
        else: 
            self.Send('set', f"outputVoltage{direction}Rate.u{channel} F {rate}")
    
    def GetVoltageRate(self, channel, direction =  'Rise'):
        ''' 
        Channel Voltage Get Rise Rate ::: [V/s] ::: float)
        directions: 'Rise' and 'Fall' 
        Note: for most modules, rise & fall rates are tied together
        '''
        if self.mode: 
            reply = f'WIENER-CRATE-MIB::outputVoltageRiseRate.u604 = Opaque: Float: {self.dummy_instrument[4]:.12f} V/s'
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
            print(f'IRate would be set to {rate} on ch{channel}')
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
            reply = 'WIENER-CRATE-MIB::outputCurrentRiseRate.u604 = Opaque: Float: 0.093592196703 A/s'
        else: 
            reply = self.Send('get', f"outputCurrent{direction}Rate.u{channel}")
        result = self.ParseReply(reply, 'float')
        return result*1000
    ### ADDITIONAL FUCTIONS ####
    def GetAllNames(self):
        #Output all channel names in an array
        #TODO: get module info
        if self.mode: 
            reply = f'WIENER-CRATE-MIB::outputName.u101 = STRING: {101}'
        else: 
            reply = self.Send('walk', 'outputName')
        result = self.ParseReply(reply, 'string')
        return result

    def SetPowerCrate(self, power_state = None):
        if power_state is None:
            power_state = int(not self.QueryPowerCrate())
        if self.mode:
            self.dummy_instrument[-2] = power_state
            print(f'crate power would be switched to {power_state}')
        else:
            self.Send('set', "sysMainSwitch.0 i {power_state}")
    
    def QueryPowerCrate(self):
        if self.mode:
            reply = f'WIENER-CRATE-MIB::sysMainSwitch.0 = INTEGER: ON({self.dummy_instrument[-2]})'
        else: 
            reply = self.Send('get', "sysMainSwitch.0")
        result = self.ParseReply(reply, 'integer')
        
        return int(result)
        
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

    def ViewAllVoltages(self):
        #Ouput all channel voltages
        result = self.Send('walk', 'outputVoltage')
        return result
        
    def QueryChannel(self, channel):
        r'''Get all channel info (Voltage, Current, On/Off Status)'''
        result = [self.QueryVoltage(channel), self.QueryCurrent(channel), self.QueryPower(channel)]
    
        
    # def LogData(self, DataToLog = [],LogFile = 'log.csv'):
    #     timestamp = datetime.now()
    #     logdatacallhere=[]
    
	    
#result = self.Send([f"snmpwalk -v 2c -m +WIENER-CRATE-MIB -c public {self.IP}"])
#print(result)

#TODO: Data logging (make a separate file)
#TODO: parse query of all voltage/current/power states
#TODO: see if moduleRampSpeedVoltage is preferable to current ramping fx


    
