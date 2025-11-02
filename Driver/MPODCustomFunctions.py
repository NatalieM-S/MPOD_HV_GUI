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
    def __init__(self, MPOD, take_real_data=True, active_modules = None, channel_names = None):
        ### custom limits & settings here
        self.max_voltage_ramp = 100# [mA/s] 
        self.status_override = [5]
        '''Statuses to override during ramps: 
        Channel:
        5: 'TRIP' (Current Trip Occurred)


        '''


        ###########################################
        self.MPOD = MPOD #object created from MPOD in MPODclass
        self.channel_names = channel_names
        self.full_channel_list = self.MPOD.GetAllNames()
        self.my_channels = self.full_channel_list.copy()#to allow for active module control
        self.modules, self.channels = self.ChannelsPerModule()
        #### Controls active module input, overrides my channels ###
        if active_modules is None: 
            active_modules = self.modules
        else: 
            module_overwrite = active_modules
            channel_overwrite,my_channels_overwrite = [],[]
            for idx, m in enumerate(active_modules):
                loc = self.modules.index(m)
                ch_list = self.channels[loc]
                channel_overwrite.append(ch_list)
                for ch in ch_list: 
                    my_channels_overwrite.append(ch)
            self.modules = active_modules
            self.my_channels = my_channels_overwrite
            self.channels = channel_overwrite
        
        self.get_locs = lambda channels: [self.full_channel_list.index(ch) for ch in channels]
        self.channel_locs = self.get_locs(self.my_channels)
        #channel_locs is index of all_channels
        ###################################################

        self.n_channels = len(self.my_channels)
        self.active_modules = self.modules.copy()
        self.active_channels = self.my_channels.copy()
        self.last_frame = []#most recently acquired data
        self.GetAllValues() #initialize last_frame with GetAllValues
        ## For main GUI
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
        names = self.my_channels#self.MPOD.GetAllNames()
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

    def CheckStatus(self,channels = None):
        ''' Returns True if any of the statuses set to override are detected on active channels'''
        if channels is None:
            channels = self.my_channels
        status = self.MPOD.GetAllStatuses('channel',True)
        # for idx, ch in enumerate(channels):
        for idx in self.channel_locs:
            if 1 in [int(status[idx][n]) for n in self.status_override]:
                return True
        return False

    def ResetIfStatus(self,channels = None):
        if channels is None:
            channels = self.my_channels

    def RampMethod(self,mode,set_values):
        '''
        MODES: 
        - 'Voltage Divider' 
                Inputs: set_values = [drift_voltage, GEM_max_voltage, ratio1, ratio2, ratio3, ratio4, ratio5, ratio6]
                ratios must be < 1 
        - 'Individual Increments'
                Inputs: set_values = [dV0, dV1, dV2, dV3, dV4, dV5, dV6]
        - 'Increment All'
                Inputs: set_values = dV

        Function to set voltages for channels with different behavior. 
        Can be based on channel id or names (GEM, Drift)
        GEM Top+ is the uppermost layer, closest to the top/drift/cathode
        '''
        #Unpack channel IDs
        drift_channel = self.my_channels[self.channel_names.index('Drift')]
        GEMTop_channels = [self.my_channels[self.channel_names.index('GEM Top+')],self.my_channels[self.channel_names.index('GEM Top-')]]
        GEMMid_channels = [self.my_channels[self.channel_names.index('GEM Mid+')],self.my_channels[self.channel_names.index('GEM Mid-')]]
        GEMLow_channels = [self.my_channels[self.channel_names.index('GEM Low+')],self.my_channels[self.channel_names.index('GEM Low-')]]
        all_gem_channels = [*GEMTop_channels,*GEMMid_channels,*GEMLow_channels]
        all_channels = [drift_channel, *all_gem_channels]

        FLAG = 0
        if mode == 'Voltage Divider':
            ''' Acts similar to how a voltage divider would. Pass in value for drift, value for GEMs and desired ratios for GEMs
            Example input: [2000,1500,1,0.8,0.5,0.3,0.2,0.1]
            '''
            drift_voltage = set_values[0]# Example: 2000 V to drift
            GEM_max_voltage = set_values[1]# Example: 1500 V divided between the GEMs
            #The example ratio of 1,0.8,0.5,0.3,0.2,0.1 returns 1500, 1200, 750, 450, 300, 150 V
            #Ramp rates not controlled
            GEM_voltage = []
            self.Reset(all_channels)# reset any faults
            for value in set_values[2:]:
                if value>1: 
                    FLAG = 1# Do not send values, these should be less than or eq to 1 to prevent overvoltage
                GEM_voltage.append(GEM_max_voltage*value)#

            if not FLAG: 
                print('Confirm settings below before sending') #TODO: display ramp rates
                print(f'Drift voltage   on channel {drift_channel}: {drift_voltage} V')
                print(f'GEM Top voltage on channel {GEMTop_channels[0]} & {GEMTop_channels[1]}: {GEM_voltage[0]}, {GEM_voltage[1]} V')
                print(f'GEM Mid voltage on channel {GEMMid_channels[0]} & {GEMMid_channels[1]}: {GEM_voltage[2]}, {GEM_voltage[3]} V')
                print(f'GEM Low voltage on channel {GEMLow_channels[0]} & {GEMLow_channels[1]}: {GEM_voltage[4]}, {GEM_voltage[5]} V')
                reply = input('If this is correct, enter: SEND')
                if reply =='SEND':
                    self.MPOD.SetTargetVoltage(drift_channel, drift_voltage)
                    for idx, val in enumerate(GEM_voltage):
                        self.MPOD.SetTargetVoltage(all_gem_channels[idx],val)
                else: 
                    FLAG = 1
                    print('Cancelled - Voltages not sent')
        elif mode == 'Individual Increments':
            v_to_increment = set_values
            for idx, ch in enumerate(all_channels): 
                    v_target = self.MPOD.GetTargetVoltage(ch)# get prior target
                    self.MPOD.SetTargetVoltage(ch, v_target + v_to_increment[idx])#set new target
        elif mode == 'Increment All':
            '''Send fixed increment to all channels. 
            Example: Increase by 50 V on drift and gem channels'''
            channels = all_channels
            v_to_increment = [set_values]*len(channels)#Single input value
            self.RampMethod('Individual Increments', v_to_increment)

        if not FLAG:#turn channels on if not flagged (and if channels are not currently on)    
            for ch in all_channels:
                if not self.MPOD.QueryPower(ch):
                    self.MPOD.SetPower(ch, 1)
                    #TODO: add monitor for status here 
                    #monitor statuses while ramping. reset & resend cmds if trips

    def RampTogether(self, channels = None, target_voltage = None, pass_to_GUI = False):
        '''
        Modes (pass to GUI): 
            False (default): Execute ramp
            True: Do not execute ramp. Send ramp parameters to GUI
        #1) get set (target) voltage values
        #2) calculate ideal ramp rates
        #3) discretize using safe ramp rates
        #4) run fx
        # '''
        #TODO: implement target voltage
        x=1
        if channels is None:
            channels = self.my_channels
        targets, starting, maximum = [], [], []
        for idx, ch in enumerate(channels): 
            if target_voltage is None: 
                targets.append(self.MPOD.GetTargetVoltage(ch))
            else: 
                targets.append(target_voltage[idx])
            starting.append(abs(self.MPOD.QueryVoltage(ch)))
            maximum.append(abs(self.MPOD.GetConfigMaxVoltage(ch, 'Terminal')))
        #TODO: add check for KILL_ENABLE to find limit for rampRate
        #TODO: add user input in initialization to set max rampRate
        #TODO: IMPORTANT: monitor for tripping and reset or turn off all channels
        # likely a stock setting - lots of behavior control bits available (see MIB file & manual)
        deltas, max_rates = [], []
        for i in range(len(targets)): 
            deltas.append(targets[i] - starting[i])# desired dV
            max_rates.append(min([self.max_voltage_ramp, 0.01*maximum[i]]))#[V/s], modify here!
            #When kill_enabled, the maximum rate is 1% of maximum terminal voltage
        rate = min(max_rates)#[V/s] selected voltage rise rate for all channels
        max_idx = deltas.index(max(deltas))# location of maximum delta
        n_div = 10# number of steps to breakup ramp into (arbitrary, can be changed)
        subdelta = [d/n_div for d in deltas]
        thresh = 1 #[V] threshold for "close enough" to consider finished
        if pass_to_GUI: #return parameters for use in GUI
            return [deltas, starting, rate, thresh, n_div]
        else: #Run commands now
            for n in range(n_div):
                self.MPOD.SendMultiple('start')
                # subdelta=[]
                for idx, ch in enumerate(channels):
                    # subdelta.append(deltas[idx]/n_div) #V interval at each step
                    self.MPOD.SetTargetVoltage(ch, round(starting[idx] + n*subdelta[idx]))
                    # self.MPOD.SetVoltageRate(ch, rate)#only needs to be sent once for ISEG HV
                    #TODO: is this the right voltage rate to set? or do I need to use SetModuleVoltageRate? 
                print(rate,subdelta)
                self.MPOD.SendMultiple('end')
                time.sleep(0.1)
                self.MPOD.SendMultiple('start')
                for idx, ch in enumerate(channels):
                    self.MPOD.SetPower(ch, 1)# Turn on HV
                current_V, target_V = 0, thresh*10
                self.MPOD.SendMultiple('end')
                #TODO: get ramping status here
                while abs(abs(current_V)-abs(target_V)) > thresh:
                    #TODO: need to track ALL to ensure that other doent shut off... see screenshot
                    current_V = abs(self.MPOD.QueryVoltage(channels[max_idx]))
                    target_V = self.MPOD.GetTargetVoltage(channels[max_idx])
                    #manual thresholding. better way to do this with querying ramp status
                    #waits until biggest change is completed
                    time.sleep(0.1)
                    if self.CheckStatus:
                        self.Reset()
                        # self.MPOD.QueryAllPowers()#[i,0,1]
                        #TODO: below is not working yet. setup better! 
                        # [self.MPOD.SetPower(i,1) for i in self.channel_locs if self.MPOD.QueryPower(i)==1]
                        # for i in self.channel_locs:
                        #     if self.MPOD.GetPower(i):self.MPOD.SetPower(i,1)
                        #Will channels power off? YES
                    print('Target: ', target_V, '\nActual: ', current_V)
            print('Ramp sequence is complete')    
        # print('moved to GUI, still preliminary')
        # breakpoint

    def Reset(self, channels = None):
        if channels is None:
            channels = self.my_channels #keep as all channels
        self.MPOD.SendMultiple('start')
        for ch in channels:
            self.MPOD.SetPower(ch, 2)#reset EmergencyOff
            self.MPOD.SetPower(ch, 10)#clear events in status
            #note - this will not switch channels off
        # self.MPOD.SendMultiple('end')
        # self.MPOD.SendMultiple('start')
        for m in self.modules:#manual states that channel events should be cleared before module events
            self.MPOD.ClearModule(m)
        self.MPOD.SendMultiple('end')

    def RampAll(self, channels_to_ramp = None, ramp_vals = None):
        ''' 
        Default: Ramp all channels down to zero. 
        Otherwise use input ramp_values values
        '''
        if channels_to_ramp is None:
            channels_to_ramp = self.my_channels #keep all channels here! 
        if ramp_vals is None:
            ramp_vals = [[0]*len(channels_to_ramp)]*2
        print('Ramp values:', ramp_vals)
        self.MPOD.SendMultiple('start')
        for idx, ch in enumerate(self.my_channels): 
            if ch in channels_to_ramp: 
                self.MPOD.SetTargetVoltage(ch, ramp_vals[0][idx])
                # self.MPOD.SetCurrentLimit(ch, ramp_vals[1][idx])
                self.MPOD.SetPower(ch, 1)
        self.MPOD.SendMultiple()
        
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
                    channels = self.my_channels # keep all channels
            if modules is None:
                    modules = self.modules # keep all channels
            if channels == self.my_channels: # read all channels together
                idx = self.get_locs(self.my_channels)
                # idx=[idx for idx, value in enumerate(self.full_channel_list) if value in self.my_channels] 
                i_rate, v_rate = [], []
                i_limit = self.MPOD.GetAllCurrentLimits()
                i_limit = [i_limit[i] for i in idx]
                i_rate_tmp = self.MPOD.GetAllCurrentRates()
                i_rate_tmp = [i_rate_tmp[i] for i in idx]
                i_actual = self.MPOD.QueryAllCurrents()
                i_actual = [i_actual[i] for i in idx]
                v_target = self.MPOD.GetAllTargetVoltages()
                v_target = [v_target[i] for i in idx]
                v_rate_tmp = self.MPOD.GetAllVoltageRates()
                v_rate_tmp = [v_rate_tmp[i] for i in idx]
                v_actual = self.MPOD.QueryAllVoltages()
                v_actual = [v_actual[i] for i in idx]
                pwr_ch = self.MPOD.QueryAllPowers()
                pwr_ch = [pwr_ch[i] for i in idx]
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
        