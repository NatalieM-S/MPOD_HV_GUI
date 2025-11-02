import multiprocessing
import time
import dearpygui.dearpygui as dpg
from plotsGUI import plotsGUI

# The function to run in the first process
def first_dpg_instance():
    g=plotsGUI()
    g.start_app()
    # dpg.create_context()
    # with dpg.window(label="Window 1", tag="window1", width=300, height=200):
    #     dpg.add_text("This is the first DPG instance.")
    # dpg.create_viewport(title='DPG Instance 1')
    # dpg.setup_dearpygui()
    # dpg.show_viewport()
    # dpg.start_dearpygui()
    # dpg.destroy_context()

# The function to run in the second process
def second_dpg_instance():
    g2=plotsGUI()
    g2.start_app()
    # dpg.create_context()
    # with dpg.window(label="Window 2", tag="window2", width=300, height=200):
    #     dpg.add_text("This is the second DPG instance.")
    # dpg.create_viewport(title='DPG Instance 2')
    # dpg.setup_dearpygui()
    # dpg.show_viewport()
    # dpg.start_dearpygui()
    # dpg.destroy_context()

if __name__ == "__main__":
    # Create and start the processes
    process1 = multiprocessing.Process(target=first_dpg_instance)
    process2 = multiprocessing.Process(target=second_dpg_instance)

    process1.start()
    process2.start()

    # Wait for both processes to complete
    process1.join()
    process2.join()
