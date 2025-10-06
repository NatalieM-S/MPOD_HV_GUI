from GUI import GUI
#Testing GUI with no DAQ connected

g = GUI(take_real_data = True) #also takes IP address as an arg, but default shoud work
g.start_app()
