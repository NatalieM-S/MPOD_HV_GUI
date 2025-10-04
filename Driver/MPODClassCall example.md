#MPODClassCall example
from MyProj.MPODClass import MPOD
IP = '169.254.107.70'
channel = 604
M=MPOD(IP)
M.TestConnection()
result=M.QueryVoltage(channel)
print(result)
Set_Voltage = 0
voltage = 5
if Set_Voltage:
    M.SetVoltage(channel,voltage)
    result = M.QueryVoltage(channel)
