This driver (located in Driver folder) is intended for a Wiener MPOD Crate running HV power supplies. 
It has been partially tested on the following modules: 
- EHS 84 60n
- EHS 84 40p
- EHS 84 20n

This (Work in Progress) driver is meant to provide access to functionalities not available in stock programs or GUIs. 

Resources used to develop this driver package: 
- SNMP documentation
- Iseg SNMP Programmers Guide
- Wiener MPOD HV&LV Power Supply System Technical Manual
- FSU's guide at https://fsunuc.physics.fsu.edu/wiki/index.php/Python_Iseg_HV_controller 

MIB files are available at https://file.wiener-d.com/software/net-snmp/ 

Setup instructions: 
(Linux)
1) Install snmp: 
    Required:
        sudo apt-get install snmp 
    Maybe optional:
        sudo apt-get install snmp-mibs-downloader
        sudo sed -i 's/mibs :/# mibs :/g' /etc/snmp/snmp.conf 
2) Download MIB file (link above) WIENER-CRATE-MIB.txt into /usr/share/snmp/mibs (Windows: C:\usr\share\snmp\mibs)

Requirements to run GUI
- this repo downloaded
- working python install
- snmp installed (windows instructions: https://blog.paessler.com/how-to-enable-snmp-on-your-operating-system)
- MIB file downloaded to correct directory
- requirements.txt modules installed
- ethernet connected to instrument on correct IP address in same network as laptop (can check instrument IP in musecontrol)
