import dearpygui.dearpygui as dpg
import pathlib
from Driver.MPODClass import MPOD
from Driver.MPODCustomFunctions import CustomFx
Crate = MPOD(mode=1)# default settings
FX = CustomFx(Crate, active_modules = [0], channel_names = ['Drift','GEM Top+','GEM Top-','GEM Mid+','GEM Mid-','GEM Low+','GEM Low-','None'])

# --- Callback Functions ---
def print_float_value(sender, app_data):
    """Callback for float inputs."""
    print(f"Voltage (Delta) Input '{dpg.get_item_label(sender)}' changed to: {app_data}")
    gem_floats = ['float_1', 'float_3','float_5']
    if dpg.get_value('checkbox_a') and sender in gem_floats:
        for i in gem_floats: 
            dpg.set_value(i, app_data) 


def print_checkbox_state(sender, app_data):
    """Callback for checkboxes."""
    if app_data:
        state = "Checked"
    else:
        state = "Unchecked"
    print(f"Checkbox '{dpg.get_item_label(sender)}' is now: {state}")

def handle_button_click():
    delta_names = ['Drift', 'Top GEM', 'Top Transfer', 'Middle GEM', 'Bottom Transfer', 'Bottom GEM', 'Induction']
    names = delta_names
    v=[]
    for i in range(len(names)):
        v.append(dpg.get_value(f'float_{i}'))

        
    print(f"Float 1: {dpg.get_value('float_1')}")
    print(f"Float 2: {dpg.get_value('float_2')}")
    print(f"Float 3: {dpg.get_value('float_3')}")
    print(f"Float 4: {dpg.get_value('float_4')}")
    print(f"Float 5: {dpg.get_value('float_5')}")
    print(f"Float 6: {dpg.get_value('float_6')}")
    print(f"Float 7: {dpg.get_value('float_7')}")
    print(f"Checkbox A: {dpg.get_value('checkbox_a')}")
    print(f"Checkbox B: {dpg.get_value('checkbox_b')}")
    print(f"Checkbox C: {dpg.get_value('checkbox_c')}")

# --- Main App Setup ---
def main_app():
    # 1. Create a context for the DPG application.
    dpg.create_context()

    # 2. Create the main viewport (the OS window).
    dpg.create_viewport(title='DPG Demo', width=500, height=550)
    with dpg.font_registry():  # Set global font
        font_file_name = 'Vera.ttf'
        font_path = str(pathlib.Path(__file__).parent.resolve()) + '/' + font_file_name
        default_font = dpg.add_font(font_path, 16)
        dpg.bind_font(default_font)
    # 3. Create the main window and add widgets.
    ch_names = ['Drift','GEM Top+','GEM Top-','GEM Mid+','GEM Mid-','GEM Low+','GEM Low-']
    delta_names = ['Drift', 'Top GEM', 'Top Transfer', 'Middle GEM', 'Bottom Transfer', 'Bottom GEM', 'Induction']
    names = delta_names
    to_indent = [2,4]
    with dpg.window(label="Control Panel", tag="main_window"):
        dpg.add_text("Float Inputs:")
        for i in range(len(names)):
            if i in to_indent: 
                with dpg.group(horizontal=True):
                    dpg.add_text('     ')
                    dpg.add_input_float(
                        label=f"{names[i]}", 
                        tag=f"float_{i}", 
                        callback=print_float_value, step = 0, width = 50)
            else: 
                dpg.add_input_float(
                    label=f"{names[i]}", 
                    tag=f"float_{i}", 
                    callback=print_float_value, step = 0, width = 50)
        dpg.add_spacer(height=15)
        dpg.add_text("Checkboxes:")
        dpg.add_checkbox(
            label="Equal GEM Voltages", 
            tag="checkbox_a", 
            callback=print_checkbox_state
        )
        dpg.add_checkbox(
            label="Checkbox B", 
            tag="checkbox_b", 
            callback=print_checkbox_state
        )
        dpg.add_checkbox(
            label="Checkbox C", 
            tag="checkbox_c", 
            callback=print_checkbox_state
        )
        
        dpg.add_spacer(height=20)
        dpg.add_button(
            label="Send All Values", 
            callback=handle_button_click
        )

    # 4. Finalize setup and show the viewport.
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # 5. Start the main render loop.
    dpg.start_dearpygui()

    # 6. Destroy the context when the app is closed.
    dpg.destroy_context()

if __name__ == '__main__':
    main_app()
