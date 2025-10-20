#testing advanced functions made for MPODClass
import time
import warnings
import traceback
''' most recent manual: https://file.wiener-d.com/documentation/MPOD/WIENER_MPOD_Manual_3.2.pdf
'''

def my_decorator(func):#testing... 
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except Exception as inst:
            traceback.print_exc()
            tb = traceback.extract_tb(inst.__traceback__)[1]
            # print('Type: ',type(inst))    # the exception type
            # print('Arguments: ',inst.args)     # arguments stored in .args
            print(inst) 
            print(f'Error in {tb.name} on line {tb.lineno}') 
            # warnings.warn(f'{func.__name__} call in MPOD Custom Functions failed')
            #TODO: pass warnings up to front panel
            result = []
            #TODO: more useful exceptions
        return result
    return wrapper

class DecorateAllMethods:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for attr, value in cls.__dict__.items():
            if callable(value):
                setattr(cls, attr, my_decorator(value))

class CustomFx(DecorateAllMethods):
    def __init__(self, MPOD, take_real_data=True):
        #custom limits & settings here
        self.max_voltage_ramp = 0.1# [A/s]
        self.MPOD = MPOD #object created from MPOD in MPODclass
        self.all_channels = self.MPOD.GetAllNames()
        self.modules, self.channels = self.ChannelsPerModule()
        self.n_channels = len(self.all_channels)
        self.active_modules = self.modules.copy()
        self.active_channels = self.all_channels.copy()
        # self.active_channels = [101] #test subset only
        self.last_frame = []#most recently acquired data
        self.GetAllValues() #initialize last_frame with GetAllValues
        cmd_values = [0]*self.n_channels
        self.cmd_values = [cmd_values,cmd_values.copy()]#next values to send

        #[[Voltages],[Currents]]

    def ChannelsPerModule(self):
        ''' 
        Returns lists of all installed channels & modules in a useable format
        Example: module with 3 ch in slot 1 & module with 6 ch in slot 5
        occupied_slots: [0,4]
        channel_list: [[1,2,3],[401,402,403,404,405,406]]
        '''
        names = self.all_channels#self.MPOD.GetAllNames()
        modules, channels = [], []
        for n in names:
            modules.append(n//100)
            # channels.append(n - 100*(n//100))
            channels.append(n)

        occupied_slots = list(set(modules))#slot occupied by each module
        occupied_slots.sort()
        tmp, channel_list = [], []
        for i in range(len(occupied_slots)): 
            for idx, M in enumerate(modules): 
                if M == occupied_slots[i]: 
                    tmp.append(channels[idx])
            channel_list.append(tmp)
            tmp=[]
        return occupied_slots, channel_list

    def RampTogether(self, channels = None, pass_to_GUI = False):
        '''
        Modes (pass to GUI): 
            False (default): Execute ramp
            True: Do not execute ramp. Send ramp parameters to GUI
        #1) get set (target) voltage values
        #2) calculate ideal ramp rates
        #3) discretize using safe ramp rates
        #4) run fx
        # '''
        if channels is None:
            channels = self.active_channels
        targets, starting, maximum = [], [], []
        # for ch in channels: 
        #     targets.append(self.MPOD.GetTargetVoltage(ch))
        #     starting.append(self.MPOD.QueryVoltage(ch))
        #     maximum.append(self.MPOD.GetConfigMaxVoltage(ch, 'Terminal'))
        # #TODO: add check for KILL_ENABLE to find limit for rampRate
        # #TODO: add user input in initialization to set max rampRate
        # #TODO: IMPORTANT: monitor for tripping and reset or turn off all channels
        # # likely a stock setting - lots of behavior control bits available (see MIB file & manual)
        # deltas, max_rates = [], []
        # for i in range(len(targets)): 
        #     deltas.append(targets[i] - starting[i])# desired dV
        #     max_rates.append(min([self.max_voltage_ramp, 0.01*maximum[i]]))#[V/s], modify here!
        #     #When kill_enabled, the maximum rate is 1% of maximum terminal voltage
        # rate = min(max_rates)#[V/s] selected voltage rise rate for all channels
        # max_idx = deltas.index(max(deltas))# location of maximum delta
        # n_div = 10# number of steps to breakup ramp into (arbitrary, can be changed)
        # thresh = 1 #[V] threshold for "close enough" to consider finished
        # if pass_to_GUI: #return parameters for use in GUI
        #     return [deltas, starting, rate, thresh, n_div]
        # else: #Run commands now
        #     for n in range(n_div):
        #         for idx, ch in enumerate(channels):
        #             subdelta = deltas[idx]/n_div #V interval at each step
        #             self.MPOD.SetTargetVoltage(ch, starting[idx] + subdelta)
        #             self.MPOD.SetVoltageRate(ch, rate)#only needs to be sent once for ISEG HV
        #         time.sleep(0.1)
        #         for idx, ch in enumerate(channels):
        #             self.MPOD.SetPower(ch, 1)# Turn on HV
        #             current_V, target_V = 0, thresh*10
        #         while abs(current_V - target_V) > thresh:
        #             current_V = self.MPOD.QueryVoltage(channels[max_idx])
        #             target_V = self.MPOD.GetTargetVoltage(channels[max_idx])
        #             #manual thresholding. probably better way to do this with querying ramp status
        #             #waits until biggest change is completed
        #             #TODO: figure out how to implement this without hanging GUI - multithread? 
        #             #TODO: add GUI update in loop
        #             time.sleep(0.1)
        #             print('Target: ', target_V, '\nActual: ', current_V)
        #     print('Ramp sequence is complete')    
        print('moved to GUI, still preliminary')
        breakpoint

    def Reset(self, channels = None):
        if channels is None:
            channels = self.all_channels #keep as all channels
        for ch in channels:
            self.MPOD.SetPower(ch, 2)#reset EmergencyOff
            self.MPOD.SetPower(ch, 10)#clear events in status

    def RampAll(self, channels_to_ramp = None, ramp_vals = None):
        ''' 
        Default: Ramp all channels down to zero. 
        Otherwise use input ramp_values values
        '''
        print(ramp_vals)
        if channels_to_ramp is None:
            channels_to_ramp = self.all_channels #keep all channels here! 
        if ramp_vals is None:
            ramp_vals = [[0]*len(channels_to_ramp)]*2
        for idx, ch in enumerate(self.all_channels): 
            if ch in channels_to_ramp: 
                self.MPOD.SetTargetVoltage(ch, ramp_vals[0][idx])
                # self.MPOD.SetCurrentLimit(ch, ramp_vals[1][idx])
                self.MPOD.SetPower(ch, 1)

    def IncrementAll(self, sender, app_data, user_data):
        #TODO: maybe this belongs in widgets, not here
        v_to_increment = user_data[0]
        # channels = user_data[1]
        send_now = user_data[1]
        # modules = self.active_modules
        # if channels is None:
        channels = self.active_channels
        for ch in channels: 
            v_target = self.MPOD.GetTargetVoltage(ch)
            self.MPOD.SetTargetVoltage(ch, v_target + v_to_increment)
        if send_now:
            # for idx,m in enumerate(modules):
            for ch in channels:
                self.MPOD.SetPower(ch, 1)

    def GetAllValues(self, channels = None, modules = None):
        pwr_crate = self.MPOD.QueryPowerCrate()
        if pwr_crate: 
            if channels is None:
                    channels = self.all_channels # keep all channels
            if modules is None:
                    modules = self.modules # keep all channels
            if channels == self.all_channels: # read all channels together
                i_rate, v_rate = [], []
                i_limit = self.MPOD.GetAllCurrentLimits()
                i_rate_tmp = self.MPOD.GetAllCurrentRates()
                i_actual = self.MPOD.QueryAllCurrents()
                v_target = self.MPOD.GetAllTargetVoltages()
                v_rate_tmp = self.MPOD.GetAllVoltageRates()
                v_actual = self.MPOD.QueryAllVoltages()
                pwr_ch = self.MPOD.QueryAllPowers()
                s=0
                for idx in range(len(self.modules)):
                    s = s + len(self.channels[idx])-1 
                    i_rate.append(i_rate_tmp[s])
                    v_rate.append(v_rate_tmp[s])                
            else: #read subset of channels (still probably faster to read all and parse)
                i_limit, i_rate, i_actual = [], [], []
                v_target, v_rate, v_actual = [], [], []
                pwr_ch = []

                for n_module, m in enumerate(modules): #only need to read 1x per module for HV modules
                    ch = self.channels[n_module][0]
                    i_rate.append(self.MPOD.GetCurrentRate(ch))#1
                    v_rate.append(self.MPOD.GetVoltageRate(ch))#4
                for ch in channels: 
                    i_limit.append(self.MPOD.GetCurrentLimit(ch))#0
                    i_actual.append(self.MPOD.QueryCurrent(ch))#2

                    v_target.append(self.MPOD.GetTargetVoltage(ch))#3
                    v_actual.append(self.MPOD.QueryVoltage(ch))#5

                    pwr_ch.append(self.MPOD.QueryPower(ch))#6
            self.last_frame = [i_limit, i_rate, i_actual, v_target, v_rate, v_actual, pwr_crate, pwr_ch]
        else: 
            warnings.warn('Crate is powered OFF - turn on')
            self.last_frame[-2] = 0
            #TODO: add better handling and put an indicator on front panel
            #TODO: better as a dictionary or other struct? 
        
                                


'''
#BITFIELD:

"04 08 " /* outputFailureMaxCurrent, outputRampDown *
04 (DEC) == 0100 (BIN)
08 (DEC) == 1000 (BIN)
outputFailureMaxCurrent = (5) AND bits 6 & 7
outputRampDown = (12)
BITS: 04 08 outputFailureMaxCurrent(5) outputRampDown(12)

another example: 
WIENER-CRATE-MIB::moduleStatus.ma0 = BITS: 00 EE 00 00 moduleIsNoSumError(8)
moduleIsNoRamp(9) moduleSafetyLoopIsGood(10) moduleIsGood(12) moduleSupplyIsGood(13)
moduleTemperatureIsGood(14)
'''