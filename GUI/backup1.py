#Tests to perform if GUI is not in a workable state
#Demonstrates basic calling functions of crate
#REQUIREMENT:  WIENER-CRATE-MIB.txt must be located in /usr/share/snmp/mibs (Windows: C:\usr\share\snmp\mibs)
from Driver.MPODClass import MPOD

M=MPOD(IP = '169.254.107.70', mode = 0, MIBdir = r"C:\usr\share\snmp\mibs")

#Turn Crate On
M.SetPowerCrate(1)
x = M.GetPowerCrate()
print('Crate power state: ', x)

x = M.GetAllNames()
print('Channel names :', x)

ch = x[0] #use first detected channel as demo
#typically something like 101

#Voltages
voltage_to_set = 0.5 #[V]
M.SetTargetVoltage(ch, voltage_to_set)
x = M.GetTargetVoltage(ch)
print('Set Target Voltage: ', x, ' V')

#Currents
current_to_set = 1 #[mA]
M.SetCurrentLimit(ch, 1)
x = M.GetCurrentLimit(ch)
print('Set Current Limit: ', x, ' mA')


x = M.GetVoltage(ch,'Sense')
y = M.GetVoltage(ch,'Terminal')
print('Voltages (Sense, Terminal)',x,y, ' V')

x = M.GetCurrent(ch)
print('Actual Current: ', x, ' mA')

x = M.GetConfigMaxVoltage(ch,'Sense')
y = M.GetConfigMaxVoltage(ch,'Terminal')
print('Max Voltages (Sense, Terminal)',x,y, ' V')

x = M.GetConfigMaxCurrent(ch)
print('Max Current ', x, ' mA')

power_state_to_set = 0 #Turned off initially for safety
M.SetPower(ch, power_state = power_state_to_set)
x = M.GetPower(ch)
print('Power state of channel: ', x)

voltage_ramprate_to_set = 1 #[V/s]
current_ramprate_to_set = 1 #[mA/s]
M.SetVoltageRate(ch, voltage_ramprate_to_set, direction =  'Rise')
x = M.GetVoltageRate(ch, direction =  'Rise')
M.SetCurrentRate(ch, current_ramprate_to_set , direction =  'Rise')
y = M.GetCurrentRate(ch, direction =  'Rise')
print('Rise Rates: ', x,' V/s\n', y, ' mA/s')

