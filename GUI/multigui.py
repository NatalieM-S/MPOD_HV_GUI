import dearpygui.dearpygui as dpg
import multiprocessing
from voltageGUI import voltageGUI 
from plotsGUI import plotsGUI 
#TODO: CSVs (highly requested)! 
#TODO: FIX POWER CYCLE HANGING PLOTGUI
#TODO: option to get status on front panel
#TODO: look at status() calls to snmp and pexpect.spawn ocnsideriations
#TODO: Confirmation for voltage ramp down and power crate off and send all values
#Load voltages from previous use
#TODO: power on hangs plot
#TODO: ramp all down button needs to override everything


from Driver.MPODClass import MPOD

def start_gui1():
    G = voltageGUI()
    G.start_app()

def start_gui2():
    g=plotsGUI(take_real_data=True)
    g.start_app()

if __name__ == '__main__':
    multiprocessing.freeze_support()

    p1 = multiprocessing.Process(target=start_gui1)
    p2 = multiprocessing.Process(target=start_gui2)
 
    p1.start()
    p2.start()

    p1.join()
    p2.join()
