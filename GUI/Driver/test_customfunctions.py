from MPODClass import MPOD
from MPODCustomFunctions import CustomFx

M=MPOD()
FX = CustomFx(M)
# FX.Test()
FX.ChannelsPerModule()
# FX.RampTogether()
FX.Reset()
FX.RampAll() #default is to ramp all channels to zero
FX.GetAllValues()
print(FX.last_frame)