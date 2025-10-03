import dearpygui.dearpygui as dpg
import numpy as np
import pandas as pd
import time
import pathlib
from screeninfo import get_monitors
#import ctypes
"""
Written by Natalie Mujica-Schwahn
from GUI import GUI
G=GUI(n_channels = 5, real_data = False)
G.start_app()
"""
class GUI:
    def __init__(self, n_channels = 5, take_real_data = True):
        self.warnings = ['testwarn']  # List of startup warnings to display on front
        self.n_channels = n_channels  # How many channels are connected
        self.take_real_data = False  # True: Instrument data, False: synthesized data
        # Set to false when not connected to instrument (to test GUI)

        # Initialize  vars for later use
        self.max_data_size = 5000
        self.savefile_path = str(pathlib.Path(__file__).parent.resolve()/"Results") # Default/current file path
        self.data_series = np.array([])  # Windowed data for plotting
        self.time_series = np.array([])
        self.save_data = np.array([])  # Full data to be saved
        self.loop_plot = False # (De)activate plot
        self.en = []  # Enable plot mask
        self.data_size = 0 # Displayed on GUI
        self.sample_rate = 0 # Displayed on GUI
        self.taglist = []  # List of start/stop positions
        self.autosave_counter = 1 # Autosave counter (bins of 100)
        self.autosave = 0 # Does autosave file exist?
        self.n_autosave = 100 # How often to auto save data
        self.n_outputs = self.n_channels * 2
        self.scale_factor = np.ones(self.n_outputs)  # default scale factor of 1, optional
        self.screensize = [1600, 400] #track viewportsize for resize management
        self.initialized = 0 #flag for window initialization
        self.ax_set = [] #list of axes names
        self.plot_set= []
        # Generate enable mask & column names from n_channels
        # Column names 0-indexed
        column_names = ['V', 'I']
        self.units_name = ['[V]', '[A]'] # Units that are measured by columns
        self.column_names = ['t']
        for n in range(self.n_channels):
            for i in range(len(column_names)):
                self.column_names.append(column_names[i] + str(n))
                self.en.append(True)

        # Generate start time & default date/time string
        self.startTime = time.monotonic()  # Sets t=0 of graph
        t = time.localtime()
        self.datestr = f"{t.tm_mon}_{t.tm_mday}_{t.tm_year}_{t.tm_hour}-{t.tm_min}-{t.tm_sec}"

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
                self.taglist.append(line_name)

            for plt in self.plot_set:
                line_name = 'Note' + str(round(dt, 3)) + '_Start' + plt
                dpg.add_plot_annotation(label = 'Plot Start', default_value = (dt, 10), parent = plt, tag = line_name)
                self.taglist.append(line_name)


    def stop_plot(self):
        self.loop_plot = False
        dt = time.monotonic() - self.startTime # Relative time (graph time)
        for ax in self.ax_set:
            line_name = 'Line' + str(round(dt, 3)) + '_Stop' + ax
            dpg.add_inf_line_series([dt], parent = 'y_axis' + ax, tag = line_name, horizontal = False)
            self.taglist.append(line_name)
        for plt in self.plot_set: 
            line_name = 'Note' + str(round(dt, 3)) + '_Stop' + plt
            dpg.add_plot_annotation(label = 'Plot Stop', default_value = (dt, 10), parent = plt, tag = line_name)
            self.taglist.append(line_name)

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
        for tag in self.taglist:  # Cleans up lines for start/stop of plot on graph
            dpg.delete_item(tag)
            
        self.taglist = []

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
            for i in range(1, len(self.column_names)):# Update visibility on Plot 0
                dpg.configure_item(self.column_names[i] + 'tag', show = self.en[i - 1])
                dpg.configure_item(self.column_names[i] + 'tag1', show = self.en[i - 1])

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
        source = sender.split('_')
        source = source[1]
        en_out = []
        for i in range(1, len(self.column_names)):
            if source == self.column_names[i]:
                en_out = i - 1
                # Edit boolean visibility enable list
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
        print('no data task setup')

    def close(self):  # Cleanup save and close instrument
        #TODO: close on save & Protections!
        if len(self.save_data) > 0:
            out = input('Do you want to save your data? y/n    ')
            yes_list = ['y', 'yes', 'Yes', 'Y', 'YES', True, 1, 'ok']
            if yes_list.count(out) > 0:
                self.save_plot()
                print('data saved')

    def resizer(self): #Resize windows automatically
        viewsize = dpg.get_viewport_width(), dpg.get_viewport_height()
        delta = viewsize[0]/self.screensize[0], viewsize[1]/self.screensize[1]
        windows = ['plotter', 'controller', 'saver']
        widths = [round(self.screensize[0]*x) for x in [7/9, 2/9, 1]]  
        heights = [round(self.screensize[1]*x) for x in [5/7, 5/7, 2/7]] 
        xpos = [round(self.screensize[0]*x) for x in [0, 7/9, 0]]
        ypos = [round(self.screensize[1]*x) for x in [0, 0, 5/7]]
        for n, win in enumerate(windows):
            target_size = widths[n], heights[n]
            target_pos = xpos[n], ypos[n]
            dpg.configure_item(win, width = int(target_size[0]*delta[0]), height = int(target_size[1]*delta[1]), pos = (delta[0]*target_pos[0], delta[1]*target_pos[1]))
            if not self.initialized:
                dpg.configure_item(win, no_close = True, no_move = True, no_resize = True)
        
        
        self.initialized = 1

    def button_example(self, sender, data):
        print('button pressed')

    def checkbox_example(self, sender, data):
        print(f'Checkbox set to {data}')

    def input_example(self, sender, data):
        print(f'Input set to {data}')

    def update_loop(self):
        currentTime = np.array(time.monotonic() - self.startTime)
        if self.loop_plot:
            # DAQ process
            if self.take_real_data:  # Instrument is connected
                #check if datatask exists. if N, create, if Y, acquire data
                instrument_data = []
                append_data = np.array(instrument_data)
                append_data = append_data * self.scale_factor 
                if len(self.data_series) == 0:
                    self.data_series = np.copy(append_data)
                else:
                    self.data_series = np.vstack((self.data_series, append_data))
                    
                append_data = np.append(currentTime, append_data)
            else:  # Create dummy data to test GUI
                dummy_data = []
                for i in range(self.n_outputs):
                    dummy_data = np.append(dummy_data, (i + 1) * np.sin(currentTime * (i + 1) / 100))

                dummy_data = dummy_data * self.scale_factor
                if len(self.data_series) == 0:
                    self.data_series = np.copy(dummy_data)
                else:
                    self.data_series = np.vstack((self.data_series, dummy_data))

                append_data = np.append(currentTime, dummy_data)

            # Time series data
            self.time_series = np.append(self.time_series, currentTime)
            # Full data arrays for saving
            if len(self.save_data) == 0:
                self.save_data = np.copy([append_data])
            else:
                self.save_data = np.append(self.save_data, [append_data], axis = 0)
                if len(self.time_series) > 1:
                    for i in range(self.n_outputs):
                        # Plot data for all plots
                        dpg.set_value(self.column_names[i + 1] + 'tag', [self.time_series, np.ndarray.tolist(self.data_series[:, i])])
                        dpg.set_value(self.column_names[i + 1] + 'tag1', [self.time_series, np.ndarray.tolist(self.data_series[:, i])])


            # Remove last element of plot data if length > max_data_size
            if len(self.time_series) > self.max_data_size:
                self.data_series = np.delete(self.data_series, 0, 0)
                self.time_series = np.delete(self.time_series, 0)

            # Updates data size counter
            self.data_size = len(self.save_data + 1) * (self.n_channels + 1)
            dpg.set_value('datasize', f'{self.data_size:.2E}')
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



    ############################INITALIZATION###########################    
    def start_app(self):
        m = get_monitors()
        edge = 9/10
        self.screensize = round(m[0].width * edge), round(m[0].height * edge)#only looks at 1st screen. should work on windows & mac too.
        # Sub-window heights, 5/7 and 2/7 of screen height
        heights = [round(self.screensize[1]*x) for x in [5/7, 2/7]] 
        # Sub-window widths, [2/9,7/9] of screen width 
        widths = [round(self.screensize[0]*x) for x in [2/9, 7/9]]  
        # Create all displays
        dpg.create_context()
        dpg.create_viewport(title = 'Instrument DAQ', width = self.screensize[0], height = self.screensize[1])
        dpg.setup_dearpygui()
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

        dpg.add_file_dialog(directory_selector=True, show=False, tag="file_dialog_id", width=heights[0],
        height=heights[0] // 2, callback=self.user_selected_filepath)
        with dpg.window(label = "Controls", height = heights[0], width = widths[0], pos = (widths[1], 0), tag = "controller"):
            dpg.add_button(label = "Start plotting", tag = "PlotButton", callback = self.start_plot, width = widths[0])
            dpg.add_button(label = "Stop plotting", tag = "StopButton", callback = self.stop_plot, width = widths[0])
            dpg.add_button(label = "Refresh plot", tag = "RefreshButton", callback = self.refresh_plot, width = widths[0])
            dpg.add_separator()
            dpg.add_text('Instruments to plot:')
            N_ch_per_tab = 5
            with dpg.tab_bar(tag = "CheckboxBar"):
                x=1
                n_tabs = self.n_channels//N_ch_per_tab + (np.mod(self.n_channels, N_ch_per_tab) > 0)
                for tab_set in range(n_tabs):
                    dpg.add_tab(label = f"{(tab_set)*N_ch_per_tab}-{min((tab_set + 1)*N_ch_per_tab - 1,self.n_channels-1)}", tag = f"Set{tab_set}")
                    # Creates group of checkboxes for all instruments
                    for N in range(N_ch_per_tab):#repeat N times
                        with dpg.group(label = f"en_group{tab_set}", horizontal = True, parent = f'Set{tab_set}'):
                            for j in range(self.n_outputs//self.n_channels):
                                if x < len(self.column_names):
                                    dpg.add_checkbox(label = f'{self.column_names[x]}', tag = f'enable_{self.column_names[x]}', default_value = True, callback = self.checkbox_TF)# example: V0 & enable_V0
                                    x=x+1




            dpg.add_button(label = "Disable all", tag = "ClearChecks", callback = self.set_all_checks, user_data = False, width = widths[0])
            dpg.add_button(label = "Enable all", tag = "EnableAllChecks", callback = self.set_all_checks, user_data = True, width = widths[0])
            dpg.add_separator()
            dpg.add_text('Data sample rate (approx):')
            dpg.add_input_float(label = 'Hz', default_value = 0, tag = 'sample_rate', min_value = 0, max_value = 60,
            min_clamped = True, max_clamped = True, format = '%f', callback = self.update_sample_rate,
            width = widths[0] * 2 // 3)
            dpg.add_text('Data sampled as fast as possible', wrap = round(widths[0] * 0.9), tag = 'sample_in_seconds')
            dpg.add_text('\nSave data size = ')
            dpg.add_text(f'{self.data_size:g}', tag = 'datasize')
            dpg.add_button(label='Clear save data', callback = self.clear_save_data, tag = 'ClearData', width = widths[0])

        # Create sub-container 1: "Live Graph"
        with dpg.window(label = "Live Graph", height = heights[0], width = widths[1], pos = (0, 0),
            horizontal_scrollbar = True, tag = 'plotter'):
            with dpg.tab_bar(tag = "TabBar"):
                dpg.add_tab(label = "All data", tag = "Tab0")
                dpg.add_tab(label = "Subplots", tag = "Tab1")
                dpg.add_tab(label = "Settings", tag = "Tab2")
                dpg.add_tab(label = 'Instrument info', tag = "Tab3")
                # Add instrument information tab
                img_path = str(pathlib.Path(__file__).parent.resolve()) + '/' + 'info.png'
                width, height, channels, data = dpg.load_image(img_path)
                with dpg.texture_registry(show = False):
                    dpg.add_static_texture(width = width, height = height, default_value = data, tag = "info")
                    dpg.add_text("For Instrument:", parent = 'Tab3')
                    dpg.add_image("info", parent = 'Tab3')

                # Create Plot0 of all data
                self.ax_set.append('')
                self.plot_set.append("Plot0")
                #SINGLE PLOT: 
                with dpg.plot(label = "V(t) for MPOD", height = -1, width = -1, parent = "Tab0", tag = self.plot_set[-1]):
                    # Create legend and axes
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label = "time", tag = "time_axis" + self.ax_set[-1])
                    dpg.add_plot_axis(dpg.mvYAxis, label = "Volts", tag = "y_axis" + self.ax_set[-1])
                    # Add data series (belong to a y axis)
                    for i in range(self.n_outputs):
                        dpg.add_line_series([], [], label = self.column_names[i + 1], parent = "y_axis" + self.ax_set[-1], tag = self.column_names[i + 1] + 'tag')  # Tag = V1tag,I1tag...
                
                
                #DOUBLE PLOT:
                self.ax_set.append('1')
                self.plot_set.append('Plot1')
                with dpg.plot(label = "V(t) for MPOD", height = dpg.get_item_height("plotter")/2, width = -1, parent = "Tab1", tag = self.plot_set[-1]):
                    # Create legend and axes
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label = "time", tag = "time_axis" + self.ax_set[-1])
                    dpg.add_plot_axis(dpg.mvYAxis, label = "Volts", tag = "y_axis" + self.ax_set[-1])
                    for i in range(0,self.n_outputs,2):
                        dpg.add_line_series([], [], label = self.column_names[i + 1], parent = "y_axis" + self.ax_set[-1], tag = self.column_names[i + 1] + 'tag1')  # Tag = V1tag1, V2tag1...

                self.ax_set.append('2')
                self.plot_set.append('Plot2')
                with dpg.plot(label = "I(t) for MPOD", height = -1, width = -1, parent = "Tab1", tag = self.plot_set[-1]):
                    # Create legend and axes
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label = "time", tag = "time_axis" + self.ax_set[-1])
                    dpg.add_plot_axis(dpg.mvYAxis, label = "Current", tag = "y_axis" + self.ax_set[-1])
                    for i in range(1,self.n_outputs,2):
                        dpg.add_line_series([], [], label = self.column_names[i + 1], parent = "y_axis" + self.ax_set[-1], tag = self.column_names[i + 1] + 'tag1')  # Tag = I1tag1, I2tag1...
        

        ### SETTINGS TAB: ###
        #with dpg.group(horizontal = False, Parent = 'Tab2'):
        with dpg.group(horizontal = False, parent = 'Tab2'):
            with dpg.table(header_row = True, parent = 'Tab2'):
                n_columns = 3
                n_rows = 4
                for n in range(n_columns):
                    dpg.add_table_column(label = f'Set {n}')

                for i in range(0, n_rows):
                    with dpg.table_row():
                        for j in range(0, n_columns):
                            dpg.add_text(f"Row{i} Column{j}")
                            dpg.add_input_int(label = 'Value', default_value = 10, width = widths[0] // 2)
                            dpg.add_input_int(label = 'Value', default_value = 10, width = widths[0] // 2)



            dpg.add_button(label = "Blank button", callback = self.button_example, user_data = None, width = widths[0])
            dpg.add_checkbox(label = 'Check', callback = self.checkbox_example, default_value = False)
            dpg.add_input_int(label = 'Value', default_value = 10, callback = self.input_example, width = widths[0] // 2)
            dpg.add_separator()
            dpg.add_text('testing settings')


        with dpg.window(label = "Saving & File Path", height = heights[1], width = self.screensize[0], pos = (0, heights[0]), tag = 'saver'):
            with dpg.group(horizontal = True):
                dpg.add_button(label = "Save", callback = self.save_plot, user_data = self.savefile_path,
                width = widths[0])
                dpg.add_checkbox(label = 'Allow Overwrite', tag = 'enable_overwrite', default_value = False)
                dpg.add_checkbox(label = 'Autosave', tag = 'Autosave', default_value = False,
                callback = lambda: dpg.disable_item('NAutosave') if dpg.get_value('Autosave') else dpg.enable_item('NAutosave'))
                dpg.add_input_int(label = 'N per autosave', tag = 'NAutosave', default_value = self.n_autosave, width = widths[0] // 2)
    
            dpg.add_separator()
            dpg.add_text("\nCurrent save file path: " + self.savefile_path, tag = 'dispFilePath', wrap = round(sum(widths[0:3]) * 0.9))  # Updates with selected file path
            with dpg.group(horizontal = True):
                dpg.add_text("Name of save file (editable):")
                dpg.add_input_text(label = ".csv    ", tag = "saveFilename", default_value = self.datestr, width = widths[1] // 3)
            
            with dpg.group(horizontal = True):
                dpg.add_button(label = "Select save file path", tag = "PathSelector", callback = lambda: dpg.show_item("file_dialog_id"), width = widths[0])
                dpg.add_button(label = 'Generate date string', callback = self.date_string, width = widths[0])

            # Display startup warnings, messages, and errors on GUI panel
            if type(self.warnings) == type(['a']):
                warning = ''
                for i in range(len(self.warnings)):
                    warning = warning + f' {i + 1}) ' + self.warnings[i]
                    dpg.add_text(f'{len(self.warnings)} startup warning(s):' + warning, tag = 'messages',
                    wrap = round(sum(widths[0:3]) * 0.9))
                    dpg.bind_item_theme('messages', 'warning_text_theme')

            else:
                dpg.add_text(self.warnings, tag = 'messages')

                #TODO: enable backup data saving option
                #dpg.set_exit_callback(self.close)  # Asks if user wants to save data on window close

            dpg.set_viewport_resize_callback(callback = self.resizer)


        ############ END APP CONFIG SETUP ########                
        # DearPyGUI window handle functions
        dpg.show_viewport()
        dpg.maximize_viewport()
        t_zero = time.monotonic()  # For sample rate calc
        t_one = 0 # For sample rate calc
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            if self.sample_rate == 0 or t_one > 1 / self.sample_rate:
                self.update_loop()  # Core DAQ and plotting loop
                t_zero = time.monotonic()

            t_one = time.monotonic() - t_zero # For sample rate calc

        dpg.destroy_context()