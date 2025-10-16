from GUI import GUI
#Testing GUI with no DAQ connected
# make sure MIB file available at https://file.wiener-d.com/software/net-snmp/ is in the correct directory
#REQUIREMENT:  WIENER-CRATE-MIB.txt must be located in /usr/share/snmp/mibs (Windows: C:\usr\share\snmp\mibs)

g = GUI(take_real_data = True) #also takes IP address as an arg, but default shoud work
g.start_app()
