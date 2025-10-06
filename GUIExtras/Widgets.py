#functions for widgets on GUI
import dearpygui.dearpygui as dpg

def test(MPOD):
    MPOD.SetPower(101, 1)

def CreateTable(row_names, width, kind, FX):
    with dpg.table(header_row = True, resizable=True, policy=dpg.mvTable_SizingFixedFit):
        columns = ['Channel', 'Target Input', 'Set Target', 'Actual', 'Status']
        widths = [width//2, width, width, width, width//2]
        for n, column_label in enumerate(columns):
            dpg.add_table_column(label = column_label, width_fixed= not (column_label == 'Status'), init_width_or_weight = widths[n])
        for i, row_label in enumerate(row_names):
            with dpg.table_row():
                dpg.add_text(row_label)#channel
                dpg.add_input_double(default_value = 0, step=0, step_fast=0)#target input
                dpg.add_text(default_value = f'{0} V', tag=f'{kind}Set{row_label}')#set target
                dpg.add_text(default_value = f'{0} V', tag=f'{kind}Actual{row_label}')#actual
                # example tag: VActual101
                with dpg.group(horizontal=True): #status
                    dpg.add_button(tag=f'{kind}Indicator{row_label}', width = 10)
                    dpg.add_text('Off',tag=f'{kind}Status{row_label}')
                    #TODO: setup data linkages for buttons & text
    SetTable(row_names, kind, FX) #initialize table

def SetTable(row_names, kind, FX):
    # Called every frame
    # FX.last_frame = [i_limit, i_rate, i_actual, v_target, v_rate, v_actual, pwr_crate, pwr_ch]
    if kind == 'V': 
        vals = FX.last_frame[3:6] #v_target, v_rate, v_actual
    elif kind == 'I':
        vals = FX.last_frame[0:3] #i_limit, i_rate, i_actual
    for n, row_label in enumerate(FX.active_channels):#prev row_names
        dpg.set_value(f'{kind}Set{row_label}', f'{vals[0][n]}') 
        dpg.set_value(f'{kind}Actual{row_label}', f'{vals[2][n]}')
        # dpg.set_value(f'{tag}', f'{vals[1]}')#rate, 1 per module. not set up yet
        #TODO: get sizing of status column (and other columns) to properly fit data
        ChannelStatus(n, row_label, kind, FX)

def ChannelStatus(n, row_label, kind, FX):
    # Called every frame
    #TODO: readout full status & set status button based on instrument status
    #TODO: add status for connected but not active
    pwr = FX.last_frame[-1]
    with dpg.theme() as red_theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0))
    with dpg.theme() as green_theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 255, 0))
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
    with dpg.theme() as grey_theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (125, 125, 125))

    if row_label in FX.active_channels:
        dpg.bind_item_theme(f'{kind}Indicator{row_label}', green_theme if pwr[n] else red_theme)
        dpg.set_value(f'{kind}Status{row_label}', 'ON' if pwr[n] else 'OFF')
    else:
        dpg.bind_item_theme(f'{kind}Indicator{row_label}', grey_theme)
    #Button for crate power status & control    
    if FX.last_frame[-2]:
        dpg.bind_item_theme('pwr_crate', green_theme)
        dpg.set_item_label('pwr_crate', 'Crate ON')
    else:
        dpg.bind_item_theme('pwr_crate', red_theme)
        dpg.set_item_label('pwr_crate', 'Crate OFF')
    

def SendValue(sender, app_data, user_data):
    print('Sender:',sender, 'App:', app_data, 'User:', user_data)
    if user_data == 'increment_button':
        existing_data = dpg.get_item_user_data(user_data)
        new_data = existing_data
        if sender == 'v_to_increment':
            new_data[0] = app_data # set v_to_increment
        elif sender == 'send_now':
            new_data[2] = app_data
        dpg.set_item_user_data(user_data, new_data)

def CreateIncrementButtons(FX, width):
    v_to_increment = 0#dpg.get_value('')
    #TODO: setup v_to_increment
    channels_to_increment = FX.active_channels
    send_now = True
    user_data = [v_to_increment, channels_to_increment, send_now]

    #TODO: add selection for channels to input, update to increment only active channels
    with dpg.group(horizontal=True):
        #Note: these multi-module callbacks with user data must be sent as a lambda fx as shown below:
        dpg.add_button(label = "Increment All", callback = lambda sender, app_data, user_data: FX.IncrementAll(sender, app_data, user_data), user_data = user_data, width=width, tag = 'increment_button')
        dpg.add_input_double(default_value=0, width=width, callback = SendValue, user_data = 'increment_button', tag = 'v_to_increment')
        dpg.add_checkbox(default_value = True, callback = SendValue, user_data = 'increment_button', tag = 'send_now')
        dpg.add_text('Increment all channels by ____  Volts')
