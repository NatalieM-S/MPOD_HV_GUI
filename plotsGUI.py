import dearpygui.dearpygui as dpg
import numpy as np
import pandas as pd
import time
import pathlib
from screeninfo import get_monitors
from Driver.MPODClass import MPOD
from Driver.MPODCustomFunctions import CustomFx
import GUIExtras.Widgets as widget
#TODO: enable sendign commands to HV
# add ch on off switch
# add enable.disable module control 
# change tabs so plot is always visible? 

#import ctypes
"""
Written by Natalie Mujica-Schwahn

from GUI import GUI
G=GUI(take_real_data = True)
G.start_app()
"""

class plotsGUI:
    def __init__(self, IP = '169.254.107.70', take_real_data = True, active_modules = [0],channel_names = ['Drift','GEM Top+','GEM Top-','GEM Mid+','GEM Mid-','GEM Low+','GEM Low-','None']):
        #TODO: add check if instrument is connected
        #TODO: add mib file to this repo and point to self
        self.warnings = ['This GUI is a work in progress. Startup delay is 5-60 seconds before plotting rate stabilizes. Saving & File Path panel has been debugged - working!. Autosaving recommended.']  # List of startup warnings to display on front
        self.IP = IP
        self.take_real_data = take_real_data  # True: Instrument data, False: synthesized data
        self.active_modules = active_modules#disable control and data for all but these modules
        # if channel_names is None:
        #     self.channel_names = #required input for self.FX, so conflicting
        # else:   
        self.channel_names = channel_names
        if not take_real_data:
            self.warnings.append('Dummy data plotted. Set take_real_data to True to plot real data')
        self.MPOD, self.FX = None, None #MPOD Class & functions object placeholders
        self.create_data_task()

        # Initialize  vars for later use
        self.max_data_size = 5000
        self.savefile_path = str(pathlib.Path(__file__).parent.resolve()/"Results") # Default/current file path
        self.data_series, self.time_series = np.array([]), np.array([]) # Windowed data for plotting
        self.save_data = np.array([])  # Full data to be saved
        self.loop_plot = True # (De)activate plot
        self.en = []  # Enable plot mask
        self.data_size, self.sample_rate = 0, 0 # Displayed on GUI
        self.autosave_counter = 1 # Autosave counter (bins of 100)
        self.autosave = 0 # Does autosave file exist?
        self.n_autosave = 100 # How often to auto save data
        self.n_outputs = self.FX.n_channels * 2
        self.scale_factor = np.ones(self.n_outputs)  # default scale factor of 1, optional
        self.screensize = [1600, 400] #track viewportsize for resize management
        self.winscale = [1,5/7]#global scaling for windows, width & height
        self.initialized = 0 #flag for window initialization
        self.ax_set, self.plot_set, self.tag_set = [], [], [] #lists of names
        # Generate enable mask & column names from n_channels
        column_names = ['V', 'I']
        self.units_name = ['[V]', '[mA]'] # Units that are measured by columns
        self.column_names = ['t']
        # for m in modules:
        for n in self.FX.all_channels:
            for i in range(len(column_names)):
                self.column_names.append(column_names[i] + str(n))
                self.en.append(True)
        
        
        # Generate start time & default date/time string
        self.startTime = time.monotonic()  # Sets t=0 of graph
        t = time.localtime()
        self.datestr = f"{t.tm_mon}_{t.tm_mday}_{t.tm_year}_{t.tm_hour}-{t.tm_min}-{t.tm_sec}"

        self.run = 1
    def date_string(self):
        t = time.localtime()
        self.datestr = f"{t.tm_mon}_{t.tm_mday}_{t.tm_year}_{t.tm_hour}-{t.tm_min}-{t.tm_sec}"
        dpg.set_value('saveFilename', self.datestr)

    def start_plot(self):
        if not self.loop_plot:  # Only runs if plot is not already started
            self.loop_plot = True
            if len(self.save_data) == 0 and dpg.get_value('saveFilename') == self.datestr:
                self.date_string()  # Updates datestr in file window

            # Add line to graph at current time
            dt = time.monotonic() - self.startTime # Relative time (graph time)
            for ax in self.ax_set:
                line_name = 'Line' + str(round(dt, 3)) + '_Start' + ax
                dpg.add_inf_line_series([dt], parent = 'y_axis' + ax, tag = line_name, horizontal = False)
                self.tag_set.append(line_name)
            for plt in self.plot_set:
                line_name = 'Note' + str(round(dt, 3)) + '_Start' + plt
                dpg.add_plot_annotation(label = 'Plot Start', default_value = (dt, 10), parent = plt, tag = line_name)
                self.tag_set.append(line_name)

    def stop_plot(self):
        if not self.take_real_data: self.run = 0 #TODO: remove this before deploying
        self.run = 0

        self.loop_plot = False
        dt = time.monotonic() - self.startTime # Relative time (graph time)
        for ax in self.ax_set:
            line_name = 'Line' + str(round(dt, 3)) + '_Stop' + ax
            dpg.add_inf_line_series([dt], parent = 'y_axis' + ax, tag = line_name, horizontal = False)
            self.tag_set.append(line_name)
        for plt in self.plot_set: 
            line_name = 'Note' + str(round(dt, 3)) + '_Stop' + plt
            dpg.add_plot_annotation(label = 'Plot Stop', default_value = (dt, 10), parent = plt, tag = line_name)
            self.tag_set.append(line_name)

    def save_plot(self):
        flag = 0 # flag for program closing
        # Generate full file path
        val = dpg.get_value("saveFilename")
        if val is None:
            flag = 1
            val = self.datestr
        full_file_path = pathlib.Path(self.savefile_path + "/" + val + '.csv')
        #scale_out = pd.DataFrame(self.scale_factor)
        #scale_out.to_csv(pathlib.Path(self.savefile_path + "/" + val + '_scale.csv'), header=False, index=False)
        #desc = f'\nScale factors saved to {self.savefile_path + "/" + val}_scale.csv'
        # Reformat column names, then save data using pandas (pd)
        savecolumn_names = []
        for i in range(len(self.column_names)):
            if i == 0:
                savecolumn_names.append(self.column_names[i] + '[s]')
            else:
                savecolumn_names.append(self.column_names[i] + self.units_name[np.mod(i, len(self.units_name))])

        if len(self.save_data) > 0:  # Checks that data is not empty
            dataframe_out = pd.DataFrame(self.save_data, columns = savecolumn_names)
            # Writes file if file does not exist or overwrite is allowed
            if (not pathlib.Path.is_file(full_file_path)) or dpg.get_value('enable_overwrite'):
                dataframe_out.to_csv(full_file_path, index=False)  # Writes data to CSV file
                desc = ''
                if not flag:
                    dpg.set_value('messages', 'Data saved to: ' + str(full_file_path) + desc)
                    dpg.bind_item_theme('messages', 'text_theme')
            else:
                if not flag:
                    dpg.set_value('messages', 'Warning: \nAllow Overwrite or rename file. File already exists.')
                    dpg.bind_item_theme('messages', 'warning_text_theme')

        else:  # Raise warning that data is empty
            if not flag:
                dpg.set_value('messages', 'Warning: \nData is empty')
                dpg.bind_item_theme('messages', 'warning_text_theme')

    def refresh_plot(self):
        self.data_series = np.array([]) 
        self.time_series = np.array([]) 
        self.startTime = time.monotonic()  # Resets t=0 on graph
        for tag in self.tag_set:  # Cleans up lines for start/stop of plot on graph
            dpg.delete_item(tag)
        self.tag_set = []

    def toggle_plot(self,sender,app_data,data):
        if data: # plot is active, turn off
            self.stop_plot()
            dpg.set_item_user_data('PlotToggleButton',False)
            print('turned off')
        else: # plot is off, turn on
            self.start_plot()
            dpg.set_item_user_data('PlotToggleButton',True)
            print('turned on')
    
    def clear_save_data(self):
        self.save_data = np.array([])
        self.autosave_counter = 0
        if dpg.get_value('saveFilename') == self.datestr:
            self.date_string()  # Updates datestr in file window
            dpg.set_value('datasize', 0)
        self.refresh_plot()

    def user_selected_filepath(self, sender, data):
        self.savefile_path = data['file_path_name']
        dpg.set_value('dispFilePath', "\nCurrent file path: " + self.savefile_path)
        dpg.set_value('messages', 'Directory updated to: ' + self.savefile_path)
        dpg.bind_item_theme('messages', 'text_theme')

    def link_plot(self, send, data = 0):  
        # Update plots to reflect self.en visibility list 
        if send == 0:  # Default axis scaling
            for ax in self.ax_set:
                dpg.fit_axis_data('y_axis' + ax)

        if send == 1:  # Show/hide traces
            for i in range(1, len(self.column_names)):
                dpg.configure_item(self.column_names[i] + 'tag1', show = self.en[i - 1])# Update visibility on Plot 1

        # Always update time axis
        for ax in self.ax_set:
            dpg.fit_axis_data("time_axis" + ax)

    def set_all_checks(self, sender, data, TF):
        for i in range(self.n_outputs):
            dpg.set_value('enable_' + self.column_names[i + 1], TF)
            self.en[i] = TF
        self.link_plot(1)

    def checkbox_TF(self, sender, data):
        # Match source to correct column of data
        source_id = sender.split('_')
        source = source_id[1]
        
        if source_id[0] == 'enable':
            en_out = []
            for i in range(1, len(self.column_names)):
                if source == self.column_names[i]:
                    en_out = i - 1# Edit boolean visibility enable list
                    self.en[en_out] = data  
            self.link_plot(1)

    def update_sample_rate(self): # Check and set sample rate for future data points
        self.sample_rate = dpg.get_value('sample_rate')
        if self.sample_rate > 0:
            s = 1 / self.sample_rate
            if s < 100:  # Display sample rate in seconds, minutes, or hours (depending on magnitude)
                dpg.set_value('sample_in_seconds', f'Data sampled every {round(s, 2)} second(s)')
            else:
                if s / 60 < 181:
                    dpg.set_value('sample_in_seconds', f'Data sampled every {round(s / 60, 1)} minutes')
                else:
                    dpg.set_value('sample_in_seconds', f'Data sampled every {round(s / 3600, 1)} hours')

        else:  # Sample rate set back to zero
            dpg.set_value('sample_in_seconds', 'Data sampled as fast as possible')

    def create_data_task(self):
        self.MPOD = MPOD(IP = self.IP, mode = not self.take_real_data)
        self.FX = CustomFx(self.MPOD, self.take_real_data, self.active_modules, self.channel_names)

    def close(self):  # Cleanup save and close instrument
        #TODO: close on save & Protections!
        #TODO: window doesnt close before displaying savedata question
        print('program closed')
        if len(self.save_data) > 0:
            out = input('Do you want to save your data? y/n    ')
            yes_list = ['y', 'yes', 'Yes', 'Y', 'YES', True, 1, 'ok']
            if yes_list.count(out) > 0:
                self.save_plot()
                print('data saved')

    def display_warnings(self):
        #TODO: include warnings from other submodules too
        warning = ''
        for i in range(len(self.warnings)):
            warning = warning + f' {i + 1}) ' + self.warnings[i] + '\n'
        for i in range(len(self.MPOD.warnings)):
            warning = warning + f' {i + 1}) ' + self.MPOD.warnings[i] + '\n'
            dpg.set_item_label(f'Current warning(s):' + warning, tag = 'messages')#,wrap = round(sum(widths[0:3]) * 0.9))
            dpg.bind_item_theme('messages', 'warning_text_theme')

    def get_plot_data(self):
        
        v_actual = self.MPOD.QueryAllVoltages()
        i_actual = self.MPOD.QueryAllCurrents()#data from MPOD.QueryCurrent

        data = []
        for idx, ch in enumerate(self.FX.full_channel_list):
            if ch in self.FX.all_channels:
                data.append(v_actual[idx])
                data.append(i_actual[idx])
        return data

    def update_loop(self,update_data = True):
        currentTime = np.array(time.monotonic() - self.startTime)
        if self.loop_plot:
            # DAQ process
            # if self.take_real_data:  # Instrument is connected
            if self.MPOD is None:
                self.create_data_task()
            #TODO: Add check if datatask exists. if N, recreate, if Y, acquire data
            update_data = self.MPOD.QueryPowerCrate()
            if update_data:#keeps buttons live when sample rate is low
                instrument_data = self.get_plot_data()#takes data, updates table
                append_data = np.array(instrument_data)
                append_data = append_data * self.scale_factor 
                if len(self.data_series) == 0:
                    self.data_series = np.copy(append_data)
                else:
                    self.data_series = np.vstack((self.data_series, append_data))
                    
                append_data = np.append(currentTime, append_data)
                # Time series data
                self.time_series = np.append(self.time_series, currentTime)
                # Full data arrays for saving
                if len(self.save_data) == 0:
                    self.save_data = np.copy([append_data])
                else:
                    self.save_data = np.append(self.save_data, [append_data], axis = 0)
                    if len(self.time_series) > 1:
                        for i in range(self.n_outputs):# Plot data for all plots
                            dpg.set_value(self.column_names[i + 1] + 'tag1', [self.time_series, np.ndarray.tolist(self.data_series[:, i])])

                # Remove last element of plot data if length > max_data_size
                if len(self.time_series) > self.max_data_size:
                    self.data_series = np.delete(self.data_series, 0, 0)
                    self.time_series = np.delete(self.time_series, 0)

                # Updates data size counter
                self.data_size = len(self.save_data + 1) * (self.FX.n_channels + 1)
                dpg.set_value('datasize', f'{self.data_size:.2E}')
                #Refresh plot
                self.link_plot(0)

                # Auto saving
                if dpg.get_value("Autosave"):
                    self.n_autosave = dpg.get_value('NAutosave')
                    if len(self.save_data) > (self.autosave_counter * self.n_autosave):
                        if self.autosave == 0:
                            self.save_plot()
                            self.autosave = 1
                            self.autosave_counter = len(self.save_data) // self.n_autosave
                        else:
                            # Generate full file path
                            val = dpg.get_value("saveFilename")
                            full_file_path = pathlib.Path(self.savefile_path + "/" + val + '.csv')
                            df = pd.DataFrame(self.save_data[-self.n_autosave - 1:-1, :])  # New data to save
                            df.to_csv(full_file_path, mode = 'a', index = False, header = False)  # Append new data
                            self.autosave = self.autosave + 1
                            dpg.set_value('messages', f'Autosave #{self.autosave}, data saved to: ' + str(full_file_path))
                            dpg.bind_item_theme('messages', 'text_theme')
                            self.autosave_counter = self.autosave_counter + 1
            self.display_warnings()


    ############################INITALIZATION###########################    
    def start_app(self):
        m = get_monitors()
        edge = 1/2
        self.screensize = round(m[0].width * edge), round(m[0].height * edge)#only looks at 1st screen. should work on windows & mac too.
        # Sub-window widths & heights as fraction of detected screen height
        heights = [round(self.screensize[1]*x) for x in [self.winscale[1], 1-self.winscale[1]]] 
        widths = [round(self.screensize[0]*x) for x in [1-self.winscale[0], self.winscale[0]]]  
        
        # Create all displays
        dpg.create_context()
        dpg.create_viewport(title = 'MPOD Crate HV DAQ', width = widths[0]+widths[1], height = heights[0]+heights[1])
        dpg.setup_dearpygui()
        # dpg.show_metrics()
        # Display options (font, colors, sizes)
        with dpg.font_registry():  # Set global font
            font_file_name = 'Vera.ttf'
            font_path = str(pathlib.Path(__file__).parent.resolve()) + '/' + font_file_name
            default_font = dpg.add_font(font_path, 16)
            dpg.bind_font(default_font)
            with dpg.theme(tag = 'warning_text_theme'):
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, [204, 102, 0], category = dpg.mvThemeCat_Core)
            with dpg.theme(tag = 'error_text_theme'):
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, [204, 0, 0], category = dpg.mvThemeCat_Core)
            with dpg.theme(tag = 'text_theme'):
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, [0, 204, 0], category = dpg.mvThemeCat_Core)        
        ### Status button themes: 
        with dpg.theme(tag = 'red_theme'):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_Text,(0,0,0))
        with dpg.theme(tag = 'green_theme'):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 255, 0))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0))
        with dpg.theme(tag = 'grey_theme'):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (125, 125, 125))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0))

        dpg.add_file_dialog(directory_selector = True, show = False, tag = "file_dialog_id", width = heights[0],
        height=heights[0] // 2, callback = self.user_selected_filepath)
        ########## CONTROLS WINDOW ############### prior width: widths[0]
        with dpg.window(label = "Controls", height = heights[1]*2, width = widths[1], pos = (0, heights[0]), tag = "controller"):
            with dpg.tab_bar(tag = "ControlsTabBar"):
                dpg.add_tab(label = "Plot", tag = "TabA")
                dpg.add_tab(label = "Save", tag = "TabB")
                # dpg.add_tab(label = 'Functions',tag = "TabC")
        ### DATA CONTROLS TAB #####
        with dpg.group(horizontal = False, parent = "TabA"):
            with dpg.group(horizontal = True):
                dpg.add_button(label = "Stop/Start", tag = "PlotToggleButton", callback = self.toggle_plot, user_data = True, width = 100)
                dpg.add_button(label = "Refresh", tag = "RefreshButton", callback = self.refresh_plot, width = 100)
                dpg.add_text('Save data size = ')
                dpg.add_text(f'{self.data_size:g}', tag = 'datasize')
                dpg.add_button(label='Clear save data', callback = self.clear_save_data, tag = 'ClearData', width = 200)
            # with dpg.group(horizontal = True):
            #     dpg.add_text('Data sample rate (approx):')
            #     dpg.add_input_float(label = 'Hz', default_value = 0, tag = 'sample_rate', min_value = 0, max_value = 60,
            #     min_clamped = True, max_clamped = True, format = '%f', callback = self.update_sample_rate,
            #     width = 50)
            #     dpg.add_text('Data sampled as fast as possible', wrap = round(widths[0] * 0.9), tag = 'sample_in_seconds')
                
        ### SETUP CONTROLS TAB #####
        # with dpg.group(horizontal = False, parent = "TabB"):
            with dpg.group(horizontal = True):
                dpg.add_button(label = 'Crate Power', callback = lambda: self.MPOD.SetPowerCrate(), tag='pwr_crate')
                dpg.add_text('Turns entire crate on/off')
                    
        ########## MAIN WINDOW ###############
        with dpg.window(label = "Live Graph", height = heights[0], width = widths[1], pos = (0, 0), horizontal_scrollbar = True, tag = 'plotter', no_title_bar = True):
            with dpg.tab_bar(tag = "TabBar"):
                dpg.add_tab(label = "Main", tag = "Tab1")
                # dpg.add_tab(label = "Instructions", tag = "Tab2")#TODO: fillout instructions page
                # dpg.add_tab(label = 'Debug',tag = 'DebugTab')
                # dpg.add_tab(label = 'Instrument info', tag = "Tab3")
        for w in 0.5, 0.5: widths.append(int(widths[1]*w)) #new container sizes w margin for padding
        for h in 0.5, 0.5: heights.append(int(heights[0]*h*0.95))
        #TODO: match color of channel label to plot color! 
        ### SETTINGS TAB: ###
        #TODO: Consider using:
        #  menu bar (like a dropdown that hides settings)
        #  multiple selection lists (selectables)
        ### FUNCTIONS CONTROL TAB ########
        # with dpg.group(horizontal = False, parent = 'TabC'):
            
        #     # with dpg.group(horizontal = True):
        #     dpg.add_text('Voltage Ramping Functions:')
        #     dpg.add_button(label = "Ramp Together (WORK IN PROGRESS)", callback = self.GUI_ramp_together, user_data = None, width = widths[0])
        #         # dpg.add_text(f'Ramps all channels at proportional ramp rates via N discrete steps')
        #     with dpg.group(horizontal = True):
        #         dpg.add_button(label = "Ramp Selected to Inputs", callback = lambda: self.FX.RampAll(self.FX.active_channels, self.FX.cmd_values), user_data = None, width = widths[0])
                
        #         # dpg.add_text(f'Ramps all channels at set ramp rates: {self.FX.last_frame[4]} V/s')
            
        #     dpg.add_button(label = "Ramp All to Zero", callback = self.FX.RampAll, user_data = None, width = widths[0])
        #     dpg.add_text(f"Module ramp rates [V/s]:")
        #     with dpg.group(horizontal = True):
        #         for idx, n in enumerate(self.FX.modules):
        #             dpg.add_input_float(format="%.2g",source = f'{idx}_VRate_Source',readonly = True, width = widths[0]//3,step = 0)

        #         #TODO: add user input to update to ramp rate value in text above
        #     widget.CreateIncrementButtons(self.FX, widths[0])
        #     dpg.add_separator()
        #     dpg.add_button(label = 'Fault Reset', tag = 'rst', callback = self.FX.Reset)
        #     dpg.add_text('still testing many other settings.... ')
        #     #TODO: add CSV drag & drop input option

            ###### MAIN TAB ###########
        ### MAIN/PLOTS TAB  ####
        with dpg.group(horizontal=True, parent = 'Tab1'):
            ##### PLOTS ####################
            with dpg.child_window(height=round(heights[0]*0.95), width=round(widths[2]*2*0.95)):
                ##### PLOT 1 ######
                self.ax_set.append('1')
                self.plot_set.append('Plot1')
                with dpg.plot(label = "V(t) for MPOD", height = round(heights[0]*0.95//2), width = round(widths[2]*2*0.95), tag = self.plot_set[-1], no_title = True):
                    dpg.add_plot_legend()# Create legend and axes
                    dpg.add_plot_axis(dpg.mvXAxis, tag = "time_axis" + self.ax_set[-1])
                    dpg.add_plot_axis(dpg.mvYAxis, label = "Voltage [V]", tag = "y_axis" + self.ax_set[-1])
                    for i in range(0,self.n_outputs,2):
                        dpg.add_line_series([], [], label = self.channel_names[(i + 1)//2], parent = "y_axis" + self.ax_set[-1], tag = self.column_names[i + 1] + 'tag1')  # Tag = V1tag1, V2tag1...
                ##### PLOT 2 ######
                self.ax_set.append('2')
                self.plot_set.append('Plot2')
                with dpg.plot(label = "I(t) for MPOD", height = round(heights[0]*0.95//2), width = round(widths[2]*2*0.95), tag = self.plot_set[-1], no_title = True):
                    dpg.add_plot_legend()# Create legend, then axes
                    dpg.add_plot_axis(dpg.mvXAxis, label = "time", tag = "time_axis" + self.ax_set[-1])
                    dpg.add_plot_axis(dpg.mvYAxis, label = "Current [mA]", tag = "y_axis" + self.ax_set[-1])
                    for i in range(1,self.n_outputs,2):
                        dpg.add_line_series([], [], label = self.channel_names[((i + 1)//2)-1], parent = "y_axis" + self.ax_set[-1], tag = self.column_names[i + 1] + 'tag1')  # Tag = I1tag1, I2tag1...
            ##### CHANNEL STATUS TABLES ####
            # with dpg.child_window(height=heights[0], width=widths[3]):
            #     with dpg.child_window(height=heights[2], width=widths[3]):
            #         with dpg.group(horizontal = True):
            #             dpg.add_text("Voltage Control (in V)")
            #             # dpg.add_button("Send All Input Voltages", callback = self.FX., small = True)
            #         widget.CreateTable(self.FX.all_channels, widths[3]*0.9//4, "V", self.FX)

            #     with dpg.child_window(width=widths[3], height=heights[2]):
            #         dpg.add_text("Current Control (in mA)")
            #         widget.CreateTable(self.FX.all_channels, widths[3]*0.9//4, "I", self.FX)
                #TODO: cleanup sizing of children, maybe use padding values
                #TODO: add indicator lines on plots to show target voltage(s)
     
            ##### INSTRUMENT INFO TAB ##########
        #     img_path = str(pathlib.Path(__file__).parent.resolve()) + '/' + 'info.png'
        #     im_width, im_height, im_channels, im_data = dpg.load_image(img_path)
        #     with dpg.texture_registry(show = False):
        #         dpg.add_static_texture(width = im_width, height = im_height, default_value = im_data, tag = "info")
        #         dpg.add_text("Basic module specs:", parent = 'Tab3')
        #         dpg.add_image("info", parent = 'Tab3')
        # with dpg.group(parent = 'DebugTab'):
        #     with dpg.table(header_row = True, resizable=True, policy=dpg.mvTable_SizingFixedFit,row_background = True):
        #         columns = ['i_limit', 'i_rate', 'i_actual', 'v_target', 'v_rate', 'v_actual', 'pwr_crate', 'pwr_ch']
        #         w = [widths[1]//len(columns)]*len(columns)
        #         for n, column_label in enumerate(columns):
        #             dpg.add_table_column(label = column_label, width_fixed= not (column_label == 'Status'), init_width_or_weight = w[n])
        #         for i, row_label in enumerate(self.FX.all_channels):
        #             with dpg.table_row():
        #                 for n in range(len(columns)):
        #                     try:
        #                         dpg.add_input_float(source = f'{i}_{n}_Source',step = 0,readonly=True)
        #                     except:
        #                         dpg.add_text('NaN')#set target

        ########## SAVE & FILE PATH WINDOW ###############
        # with dpg.window(label = "Saving & File Path", height = heights[1], width = self.screensize[0], pos = (0, heights[0]), tag = 'saver'):
        with dpg.group(parent = 'TabB'):
            with dpg.group(horizontal = True):
                dpg.add_button(label = "Save", callback = self.save_plot, user_data = self.savefile_path,
                width = 100)
                dpg.add_checkbox(label = 'Allow Overwrite', tag = 'enable_overwrite', default_value = False)
                dpg.add_checkbox(label = 'Autosave', tag = 'Autosave', default_value = False,
                callback = lambda: dpg.disable_item('NAutosave') if dpg.get_value('Autosave') else dpg.enable_item('NAutosave'))
                dpg.add_input_int(label = 'N per autosave', tag = 'NAutosave', default_value = self.n_autosave, width = 100)

            dpg.add_separator()
            dpg.add_text("\nCurrent save file path: " + self.savefile_path, tag = 'dispFilePath', wrap = round(sum(widths[0:3]) * 0.9))  # Updates with selected file path
            with dpg.group(horizontal = True):
                dpg.add_text("Name of save file (editable):")
                dpg.add_input_text(label = ".csv    ", tag = "saveFilename", default_value = self.datestr, width = 200)
            
            with dpg.group(horizontal = True):
                dpg.add_button(label = "Select save file path", tag = "PathSelector", callback = lambda: dpg.show_item("file_dialog_id"), width = widths[0])
                dpg.add_button(label = 'Generate date string', callback = self.date_string, width = widths[0])

            # Display startup warnings, messages, and errors on GUI panel
            # with dpg.child_window(autosize_x = True, autosize_y = True):
            #     if type(self.warnings) == type(['a']):
            #         warning = ''
            #         for i in range(len(self.warnings)):
            #             warning = warning + f' {i + 1}) ' + self.warnings[i]
            #         dpg.add_text(f'{len(self.warnings)} startup warning(s):' + warning, tag = 'messages',wrap = round(sum(widths[0:3]) * 0.9))
            #         dpg.bind_item_theme('messages', 'warning_text_theme')
            #     else:
            #         dpg.add_text(self.warnings, tag = 'messages')

                #TODO: enable backup data saving option
                #dpg.set_exit_callback(self.close)  # Asks if user wants to save data on window close
            # dpg.set_viewport_resize_callback(callback = self.resizer)

        ############ END APP CONFIG SETUP ########                
        # DearPyGUI window handle functions
        dpg.show_viewport()
        # dpg.maximize_viewport()
        t_zero = time.monotonic()  # For sample rate calc
        t_one = 0 # For sample rate calc
        while dpg.is_dearpygui_running() and self.run:
            dpg.render_dearpygui_frame()
            if self.sample_rate == 0 or t_one > 1 / self.sample_rate:
                self.update_loop(True)  # Core DAQ and plotting loop
                t_zero = time.monotonic()
            else: 
                self.update_loop(False)
            t_one = time.monotonic() - t_zero # For sample rate calc                    
        self.close()
        dpg.destroy_context()

g = plotsGUI(take_real_data = True) 
g.start_app()
# plotsGUI