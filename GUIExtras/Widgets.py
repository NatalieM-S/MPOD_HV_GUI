#functions for widgets on GUI
import dearpygui.dearpygui as dpg
def CreateTable(row_names, width, kind, FX):
    with dpg.table(header_row = True, resizable=True, policy=dpg.mvTable_SizingFixedFit,row_background = True):
        columns = ['Ch', 'Target Input', 'Target', 'Actual', 'Status']
        widths = [width, width*3//4, width*2//3, width, width//2]
        for n, column_label in enumerate(columns):
            dpg.add_table_column(label = column_label, width_fixed= not (column_label == 'Status'), init_width_or_weight = widths[n])
        for i, row_label in enumerate(row_names):
            with dpg.table_row():
                dpg.add_text(f'{row_label}:{FX.channel_names[i]}')#channel
                dpg.add_input_double(default_value = 0, step=0, tag = f'{kind}Input{row_label}',callback = SendValue,user_data = FX)#target input
                #TODO: send this input to machine when ramp button is pressed
                #TODO: Figure out how to deal w extraneous values (dont send defaulted zeros when not desired to)
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
    # for n, row_label in enumerate(FX.active_channels):#prev row_names
    for n, row_label in enumerate(FX.all_channels):
        dpg.set_value(f'{kind}Set{row_label}', f'{vals[0][n]:.5g}') 
        dpg.set_value(f'{kind}Actual{row_label}', f'{vals[2][n]:.5g}')
        #TODO: check sizing of status column (and other columns) adjust w window
        ChannelStatus(n, row_label, kind, FX)
        UpdateRegistry(FX)

def ChannelStatus(n, row_label, kind, FX):
    # Called every frame
    #TODO: readout full status & set status button based on instrument status bits
    pwr = FX.last_frame[-1]
    crate_pwr = FX.last_frame[-2]
    ### MODULE STATUS ###
    #todo: FIGURE OUT HOW TO GET MODULES IN WHEN CALLED FOR EVERY ROW - MAYBE JUST FOR N =0? 
    ### CHANNEL STATUS ####
    if row_label in FX.active_channels:
        dpg.bind_item_theme(f'{kind}Indicator{row_label}', 'green_theme' if pwr[n] else 'red_theme')
        dpg.set_value(f'{kind}Status{row_label}', 'ON' if pwr[n] else 'OFF')
        dpg.configure_item(f'{kind}Input{row_label}', enabled=True)
    else:
        dpg.bind_item_theme(f'{kind}Indicator{row_label}', 'grey_theme')
        dpg.set_value(f'{kind}Status{row_label}', 'DISABLED')
        dpg.configure_item(f'{kind}Input{row_label}', enabled=False)

    ### CRATE STATUS ###   
    dpg.bind_item_theme('pwr_crate', 'green_theme' if crate_pwr else 'red_theme')
    dpg.set_item_label('pwr_crate', 'Crate ON' if crate_pwr else 'Crate OFF')

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
    if 'Input' in sender:
        #Handles VInput and IInput
        # FX = user_data
        idx = 0 + (sender[0] == 'I') #V = 0, I  = 1
        ch = int(sender.split('Input')[1])
        idx2 = user_data.all_channels.index(ch)
        user_data.cmd_values[idx][idx2] = app_data
        print('SendInput cmd_values: ',user_data.cmd_values)

def CreateIncrementButtons(FX, width):
    v_to_increment = 0#dpg.get_value('')
    #TODO: setup v_to_increment. may be ok
    send_now = True
    user_data = [v_to_increment, send_now]

    with dpg.group(horizontal=True):
        #Note: these multi-module callbacks with user data must be sent as a lambda fx as shown below:
        dpg.add_button(label = "Increment Active Channels", callback = lambda sender, app_data, user_data: FX.IncrementAll(sender, app_data, user_data), user_data = user_data, width=width, tag = 'increment_button')
    dpg.add_input_double(default_value=0, width=width, callback = SendValue, user_data = 'increment_button', tag = 'v_to_increment')
        # dpg.add_checkbox(default_value = True, callback = SendValue, user_data = 'increment_button', tag = 'send_now')
    dpg.add_text('Increments active channels by ____ Volts')

def UpdateRegistry(FX):
    for idx, n in enumerate(FX.modules):
        dpg.set_value(f'{n}_VRate_Source', FX.last_frame[4][idx])
    for i, row_label in enumerate(FX.all_channels):
        for n in range(len(FX.all_channels)):
            try:
                dpg.set_value(f'{i}_{n}_Source',FX.last_frame[n][i])
            except:
                pass

def module_enable(sender,app_data,user_data):
    FX,index,src= user_data
    new_status = False#default in case module is disabled
    if src == 'module':
        module = FX.modules[index]#check if is member of active modules then flip state
        channels = FX.channels[index]#grouped channels
        children = dpg.get_item_children(f"en_data_group{index}",1)
        if module in FX.active_modules:
            FX.active_modules.remove(module)
            FX.active_channels = [ch for ch in FX.active_channels if ch not in channels]
        else: #add module and channels to active list
            idx = FX.modules.index(module)
            FX.active_modules.append(module)
            tmp = [FX.active_channels.append(ch) for ch in FX.channels[idx]]#needs lhs to eval properly
            FX.active_modules.sort()
            FX.active_channels.sort()
            new_status = True
        for child in children:
            grandchildren = dpg.get_item_children(child,1)
            for child in grandchildren:
                dpg.bind_item_theme(child,'green_theme' if new_status else 'red_theme')
                dpg.set_item_label(child,'Enabled' if new_status else 'Disabled')
    else: #src is 'channel'
        channel = FX.all_channels[index]
        if channel//100 in FX.active_modules:
            if channel in FX.active_channels:
                FX.active_channels.remove(channel)
            else:#add channel to active list
                FX.active_channels.append(channel)
                FX.active_channels.sort()
                new_status = True

    dpg.bind_item_theme(sender,'green_theme' if new_status else 'red_theme')
    dpg.set_item_label(sender,'Enabled' if new_status else 'Disabled')
    
    #TODO: dis/enable actions on other tabs