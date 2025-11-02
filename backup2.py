#Advanced tests to perform if GUI is not in a workable state
#Demonstrates custom calling functions of crate
#REQUIREMENT:  WIENER-CRATE-MIB.txt must be located in /usr/share/snmp/mibs (Windows: C:\usr\share\snmp\mibs)
from Driver.MPODClass import MPOD
from Driver.MPODCustomFunctions import CustomFx

M=MPOD(IP = '169.254.107.70', mode = 0, MIBdir = r"C:\usr\share\snmp\mibs")
FX = CustomFx(M)

occupied_slots, channel_list = FX.ChannelsPerModule()
for idx, slot in occupied_slots:
    print(f'Module in slot{slot} has channels: {channel_list[idx]}')
print('Channels are addressed using channel names:', FX.my_channels)


FX.GetAllValues()
print('Grouped data for all channels:', FX.last_frame)

FX.Reset()
print('Reset function clears any codes')

#Demo: set all channels to 1 V, then ramp all down to zero 
for ch in FX.my_channels:# Set to 1 V
    M.SetTargetVoltage(ch,1)
for ch in FX.my_channels:# Set power on
    M.SetPower(ch,1)
top_voltage = []
for ch in FX.my_channels:
    top_voltage.append(M.QueryVoltage(ch))

FX.RampAll() #default is to ramp all channels to zero
bottom_voltage = []
for ch in FX.my_channels:
    bottom_voltage.append(M.QueryVoltage(ch))
print('Voltages at the top: ', top_voltage, '\nVoltages at the bottom:', bottom_voltage)

#Setup to ramp two channels together
ch1 = FX.my_channels[0]
ch2 = FX.my_channels[1]
V1, V2 = 10, 5
M.SetTargetVoltage(ch1, V1)
M.SetTargetVoltage(ch2, V2)

FX.RampTogether(FX.my_channels[0:2])
#Currently this fx discretizes the rise into 10 segments. 
#this should be adaptively modified
