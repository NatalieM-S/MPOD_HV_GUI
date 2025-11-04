#MPODClassCall example
from MPODClass import MPOD
IP = '169.254.107.70'
channel = 604
M=MPOD(IP)
M.TestConnection()
result=M.GetVoltage(channel)
print(result)
Set_Voltage = 0
voltage = 5
if Set_Voltage:
    M.SetVoltage(channel,voltage)
    result = M.GetVoltage(channel)
    print(result)
