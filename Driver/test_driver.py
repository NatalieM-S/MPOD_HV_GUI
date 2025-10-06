from MPODClass import MPOD

M=MPOD()
ch = 101 #assumes slot 1 channel 1

#Voltages
M.SetTargetVoltage(ch ,0.5)
x = M.GetTargetVoltage(ch)
print('Target Voltage: ', x, ' V')

M.SetCurrentLimit(ch, 1)
x = M.GetCurrentLimit(ch)
print('Current Limit: ', x, ' mA')


x = M.QueryVoltage(ch,'Sense')
y = M.QueryVoltage(ch,'Terminal')
print('Voltages (Sense, Terminal)',x,y)

x = M.QueryCurrent(ch)
print('Current ', x)

x = M.GetConfigMaxVoltage(ch,'Sense')
y = M.GetConfigMaxVoltage(ch,'Terminal')
print('Max Voltages (Sense, Terminal)',x,y)

x = M.GetConfigMaxCurrent(ch)
print('Max Current ', x)

M.SetPower(ch, power_state = 0)
x = M.QueryPower(ch)
print('Power ', x)

M.SetVoltageRate(ch, 0.1, direction =  'Rise')
x = M.GetVoltageRate(ch, direction =  'Rise')
M.SetCurrentRate(ch, 0.1, direction =  'Rise')
y = M.GetCurrentRate(ch, direction =  'Rise')
print('Rise Rates: ', x, y)

x = M.GetAllNames()
print('Module names ', x)

M.SetPowerCrate(1)
x = M.QueryPowerCrate()
print('Crate power state ', x)
