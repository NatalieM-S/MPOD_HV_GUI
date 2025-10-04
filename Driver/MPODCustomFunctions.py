#testing advanced functions made for MPODClass
import time
''' most recent manual: https://file.wiener-d.com/documentation/MPOD/WIENER_MPOD_Manual_3.2.pdf
'''

class CustomFx:
    def __init__(self, MPOD):
        #custom limits & settings here
        self.max_voltage_ramp = 0.1# [A/s]
        self.MPOD = MPOD #object created from MPOD in MPODclass
        self.all_channels = self.MPOD.GetAllNames()
        self.n_channels = len(self.all_channels)
        self.modules, self.channels = self.ChannelsPerModule()

    def Test(self):
        self.MPOD.GetTargetVoltage(101)
        self.MPOD.GetCurrentLimit(101)
        self.MPOD.SetTargetVoltage(101, 1)
        self.MPOD.SetCurrentLimit(101, 1)

    def ChannelsPerModule(self):
        ''' 
        Returns lists of all installed channels & modules in a useable format
        Example: module with 3 ch in slot 1 & module with 6 ch in slot 5
        occupied_slots: [0,4]
        channel_list: [[1,2,3],[1,2,3,4,5,6]]
        '''
        names = self.MPOD.GetAllNames()
        modules, channels = [], []
        for n in names:
            modules.append(n//100)
            channels.append(n - 100*(n//100))

        occupied_slots = list(set(modules))#slot occupied by each module
        tmp, channel_list = [], []
        for i in range(len(occupied_slots)): 
            for idx, M in enumerate(modules): 
                if M == occupied_slots[i]: 
                    tmp.append(channels[idx])
            channel_list.append(tmp)
            tmp=[]
        return occupied_slots, channel_list

    def RampTogether(self, channels = None):
        #1) get set values
        #2) calculate ideal ramp rates
        #3) discretize using safe ramp rates
        #4) run fx
        if channels is None:
            channels = self.all_channels
        targets, starting, maximum = [], [], []
        for ch in channels: 
            targets.append(self.MPOD.GetTargetVoltage(ch))
            starting.append(self.MPOD.QueryVoltage(ch))
            maximum.append(self.MPOD.GetConfigMaxVoltage(ch, 'Terminal'))
        #TODO: add check for KILL_ENABLE to find limit for rampRate
        #TODO: add user input in initialization to set max rampRate
        #TODO: IMPORTANT: monitor for tripping and reset or turn off all channels
        # is this a stock setting? lots of behavior control bits available (see MIB file & manual)
        deltas, max_rates = [], []
        for i in range(len(targets)): 
            deltas.append(targets[i] - starting[i])# desired dV
            max_rates.append(min([self.max_voltage_ramp, 0.01*maximum[i]]))#[V/s], modify here!
            #When kill_enabled, the maximum rate is 1% of maximum terminal voltage
        rate = min(max_rates)#[V/s] selected voltage rise rate for all channels
        max_idx = deltas.index(max(deltas))# location of maximum delta
        n_div = 10# number of steps to breakup ramp into (arbitrary, can be changed)
        thresh = 1 #[V] threshold for "close enough" to consider finished
        for n in range(n_div):
            for idx, ch in enumerate(channels):
                subdelta = deltas[idx]/n_div #V interval at each step
                self.MPOD.SetTargetVoltage(ch, starting[idx] + subdelta)
                self.MPOD.SetVoltageRate(ch, rate)#only needs to be sent once for ISEG HV
            time.sleep(0.1)
            for idx, ch in enumerate(channels):
                self.MPOD.SetPower(ch, 1)# Turn on HV
                current_V, target_V = 0, thresh*10
            while abs(current_V - target_V) > thresh:
                current_V = self.MPOD.QueryVoltage(channels[max_idx])
                target_V = self.MPOD.GetTargetVoltage(channels[max_idx])
                #manual thresholding. probably better way to do this with querying ramp status
                #waits until biggest change is completed
                #TODO: figure out how to implement this without hanging GUI - multithread? 
                #TODO: add GUI update in loop
                time.sleep(0.1)
                print('Target: ', target_V, '\nCurrent: ', current_V)
            
        def Reset(self, channels = None):
            if channels is None:
                channels = self.all_channels
            for ch in channels:
                self.MPOD.SetPower(ch, 2)#reset EmergencyOff
                self.MPOD.SetPower(ch, 10)#clear events in status

        def RampDownAll(self, channels = None):
            if channels is None:
                channels = self.all_channels
            for ch in channels: 
                self.MPOD.SetTargetVoltage(ch, 0)
                self.MPOD.SetPower(ch, 1)
        
        def GetAllValues(self, channels = self.all_channels):
            x = 1
                

        

        


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