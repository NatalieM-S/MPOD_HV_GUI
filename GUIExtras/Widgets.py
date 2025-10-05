#functions for widgets on GUI
import dearpygui.dearpygui as dpg

def test(MPOD):
    MPOD.SetPower(101, 1)

def CreateTable(row_names, width, kind):
    with dpg.table(header_row = True):
        columns = ['Channel', 'Target', 'Actual', 'Status']
        for n, column_label in enumerate(columns):
            dpg.add_table_column(label = column_label)
        
        for i, row_label in enumerate(row_names):
            with dpg.table_row():
                dpg.add_text(row_label)
                dpg.add_input_int(default_value = 0, width = width)
                dpg.add_input_double(default_value = 0, width = width, tag=f'{kind}Actual{row_label}', readonly=True)
                # example tag: VActual101
                with dpg.group(horizontal=True):
                    dpg.add_color_button(tag=f'{kind}Indicator{row_label}')
                    dpg.add_text('Off',tag=f'{kind}Status{row_label}')
                    #TODO: setup data linkages for buttons & text
                    # example tag: VIndicator101, VStatus101
# def GetAllData(MPOD)

def CreateIncrementButtons(FX, width):
    v_to_increment = 50
    channels_to_increment = FX.all_channels
    send_now = True
    user_data = [v_to_increment, channels_to_increment, send_now]

    #TODO: add selection for channels to input
    with dpg.group(horizontal=True):
        dpg.add_button(label = "Increment All", callback = lambda sender, app_data, user_data: FX.IncrementAll(sender, app_data, user_data), user_data = user_data, width=width)#, user_data = data, width = width)
        # dpg.add_input_double(default_value=0, width=width, callback = )
        #TODO: pull vtoincrement from numeric user input
        dpg.add_text('Increment all channels by 50 V')

# def 