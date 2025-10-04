#Script to connect to MPOD crate HV module and query/set voltages
import subprocess
subprocess.run("IPaddress='169.254.107.70'")
subprocess.run("channel=604")
print(subprocess.run("snmpwalk -v 2c -m +WIENER-CRATE-MIB -c public $IPaddress"),capture_output=True)
