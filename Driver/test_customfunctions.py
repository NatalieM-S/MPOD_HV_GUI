from MPODClass import MPOD
from MPODCustomFunctions import CustomFx

M=MPOD()
F = CustomFx(M)
# F.Test()
F.ChannelsPerModule()
F.RampTogether([101,102,103,500,501])
F.Reset()
F.RampDownAll()
F.GetAllValues()