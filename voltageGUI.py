import dearpygui.dearpygui as dpg
import pathlib
import csv
from screeninfo import get_monitors
from Driver.MPODClass import MPOD
from Driver.MPODCustomFunctions import CustomFx

class voltageGUI: 
    def __init__(self, IP = '169.254.107.70', take_real_data = True, active_modules = [0],channel_names = ['Cathode','GEM Top+','GEM Top-','GEM Mid+','GEM Mid-','GEM Low+','GEM Low-','None'],Crate = None, FX = None):
        self.dv_tags = ["DriftInput","TopGEMInput","TopTransferInput","MidGEMInput","LowTransferInput","LowGEMInput","InductionInput"]
        self.v_tags = ['VCathode', 'VTopGEM+', 'VTopGEM-', 'VMidGEM+', 'VMidGEM-', 'VLowGEM+', 'VLowGEM-', 'VAnode']
        if Crate is None:
            self.Crate = MPOD(IP=IP)
        self.savefile_path = str(pathlib.Path(__file__).parent.resolve()/"Results") # Default/current file path
        if FX is None: 
            self.FX = CustomFx(self.Crate, take_real_data=take_real_data,active_modules = active_modules, channel_names = [channel_names])

    def print_checkbox_state(self, sender, app_data):
        """Callback for checkboxes."""
        if app_data:
            state = "Checked"
        else:
            state = "Unchecked"
        print(f"Checkbox '{dpg.get_item_label(sender)}' is now: {state}")

    def handle_button_click(self,sender,app_data):
        if sender == 'SendAll':
            v = [dpg.get_value(tag) for tag in self.v_tags]
            if dpg.get_value('checkbox_b'):
                self.FX.RampTogether(self.FX.my_channels,v,n_div = 25)
            else:
                self.FX.RampAll(self.FX.my_channels,[v])

        if sender == 'IncrementAll':
            #Desired behavior: increment all but anode by v_increment 
            #TODO: Validate that this is desired behavior! different than previous setup.. maybe use voltage divider function here
            tag = 'InductionInput'
            dpg.set_value(tag,dpg.get_value(tag)+dpg.get_value('v_increment'))
            self.update_voltages_callback()
        if sender == 'IncrementPercentage':
            pct = dpg.get_value('pct_increment')
            for tag in self.v_tags:
                v_start = dpg.get_value(tag)
                dpg.set_value(tag,round(v_start*(1+pct/100),1))
            self.update_voltages_callback('VCathode')
   
    def save_config(self):
        # new_row_data = [a,b,c]
        # with open('people.csv', mode='a', newline='') as file:
        #     writer = csv.writer(file)
        #     writer.writerow(new_row_data)
        pass
        #TODO: add csv append target voltages 


    def update_voltages_callback(self, sender = [], app_data =[], user_data=[]):
        """
        Calculates absolute and relative voltages based on inputs
        """
        # try:
        # self.dv_tags = ["DriftInput","TopGEMInput","TopTransferInput","MidGEMInput","LowTransferInput","LowGEMInput","InductionInput"] 
        #### SET ABSOLUTE FROM RELATIVE #####
        if sender not in self.v_tags:
            gem_floats = ["TopGEMInput","MidGEMInput","LowGEMInput"]
            if dpg.get_value('checkbox_a') and sender in gem_floats:
                for tag in gem_floats: 
                    dpg.set_value(tag, app_data) 
                    print(app_data)
            
            v_bottom_to_top =[]
            next_v = dpg.get_value('VAnode')
            for idx, tag in enumerate(reversed(self.dv_tags)):
                next_v = next_v + dpg.get_value(tag)
                v_bottom_to_top.append(next_v)
            for idx,V in enumerate(reversed(v_bottom_to_top)):
                dpg.set_value(self.v_tags[idx],V)

        #### SET RELATIVE FROM ABSOLUTE #####
        if sender not in self.dv_tags:
            last_v = dpg.get_value('VCathode')
            for idx,tag in enumerate(self.v_tags[1::]):
                dpg.set_value(self.dv_tags[idx],last_v-dpg.get_value(tag))
                last_v=dpg.get_value(tag) 

        # # except Exception as e:
        #     print(f"Error updating voltages: {e}")
    
    def start_app(self):
        m = get_monitors()
        winscale = [1,5/7]
        edge = 1/2
        screensize = round(m[0].width * edge), round(m[0].height * edge)#only looks at 1st screen. should work on windows & mac too.
        heights = [round(screensize[1]*x) for x in [winscale[1], 1-winscale[1]]] 
        widths = [round(screensize[0]*x) for x in [1-winscale[0], winscale[0]]]
        w = heights[0]*5//4
        h = heights[0]*2  
        dpg.create_context()
        dpg.create_viewport(title='Triple GEM Voltage Controller', width=w, height=h,x_pos=widths[0]+widths[1],y_pos = 0)
        with dpg.font_registry():  # Set global font
            font_file_name = 'Vera.ttf'
            font_path = str(pathlib.Path(__file__).parent.resolve()) + '/' + font_file_name
            default_font = dpg.add_font(font_path, 14)
            dpg.bind_font(default_font)
        dpg.setup_dearpygui()

        with dpg.window(width=w, height=h*3//2, no_resize=True,no_move = True, no_close = True,no_title_bar=True,pos=[0,0]):
            with dpg.group(horizontal = True):
                dpg.add_text('Relative \nVoltages')
                dpg.add_spacer(width = 110)
                dpg.add_text('Absolute \nVoltages')
            with dpg.group(horizontal=True):
                layer_height, spacing = 50, 20
                padding_y = 5
                text_x_pos = 20 # X position for the dynamic text within the drawlist
                padding_x = 10 
                text_padding_y = 19 #14 pt txt is about 19px 
                canvas_width, canvas_height = 100, layer_height*5+spacing*4

                ##### DIFFERENTAL VOLTAGE (Float Inputs)######
                with dpg.group():
                    labels = ['Drift', 'Top GEM', 'Top Transfer','Middle GEM','Lower Transfer','Lower GEM','Induction']
                    defaults = [500,350,100,350,100,350,500]
                    dpg.add_spacer(height = layer_height+spacing//2-text_padding_y//2)
                    for i in range(len(labels)):
                        # label=labels[i], 
                        dpg.add_input_float(tag=self.dv_tags[i], default_value=defaults[i], step=0, format="%.0f V", callback= self.update_voltages_callback, width=60)
                        h=(spacing+layer_height-text_padding_y*3)//2
                        dpg.add_spacer(height=h)
                ###### CARTOON ######
                with dpg.group(horizontal = True):
                    with dpg.drawlist(width=canvas_width, height=canvas_height):
                        c = [[100, 100, 255],[100, 255, 100],[255, 100, 100]]#color specs
                        f = [[50, 50, 150],[50, 150, 50],[150, 50, 50]]
                        # CATHODE
                        # y_position = padding_y + layer_height/2
                        dpg.draw_rectangle((padding_x, padding_y), (canvas_width - padding_x, padding_y + layer_height), color=c[0], fill=f[0], thickness=1)
                        # dpg.draw_text((text_x_pos, padding_y + layer_height//2-text_padding_y//2), size=14, text='Cathode')

                        dpg.draw_text((text_x_pos, padding_y + layer_height/2 -text_padding_y//2 ), text = "  Cathode", tag="CathodeTxt", size=14)
                        
                        # DRIFT
                        dpg.draw_text((0, padding_y + layer_height+spacing//2-text_padding_y//2), size=14, text=' -------Drift-------')
                                    
                        # Top GEM
                        y_gem1 = padding_y + layer_height + spacing
                        dpg.draw_rectangle((padding_x, y_gem1), (canvas_width - padding_x, y_gem1 + layer_height), color=c[1], fill=f[1], thickness=1)
                        # dpg.draw_text((text_x_pos, y_gem1 + layer_height/2 - text_padding_y), "V_TopGEM", tag="TopGEMTxt", size=14)
                        dpg.draw_text((text_x_pos, y_gem1 + layer_height/2-text_padding_y//2), tag="TopGEMTxt", size=14, text = ' Top GEM')

                        #TOP TRANSFER
                        dpg.draw_text((0, y_gem1 + layer_height+spacing//2-text_padding_y//2), size=14, text=' -----Transfer-----')

                        # Mid GEM
                        y_gem2 = y_gem1 + layer_height + spacing
                        dpg.draw_rectangle((padding_x, y_gem2), (canvas_width - padding_x, y_gem2 + layer_height), color=c[1], fill=f[1], thickness=1)
                        dpg.draw_text((text_x_pos, y_gem2 + layer_height/2 - text_padding_y//2), tag="MidGEMTxt", size=14,text = 'Middle GEM')

                        # LOW TRANSFER 
                        dpg.draw_text((0, y_gem2 + layer_height+spacing//2-text_padding_y//2), size=14, text=' -----Transfer-----')

                        # Low GEM
                        y_gem3 = y_gem2 + layer_height + spacing
                        dpg.draw_rectangle((padding_x, y_gem3), (canvas_width - padding_x, y_gem3 + layer_height), color=c[1], fill=f[1], thickness=1)
                        dpg.draw_text((text_x_pos, y_gem3 + layer_height/2 - text_padding_y//2), tag="LowGEMTxt", size=14,text='Lower GEM')

                        # INDUCTION 
                        dpg.draw_text((0, y_gem3 + layer_height+spacing//2-text_padding_y//2), size=14, text=' -----Induction-----')

                        # ANODE
                        y_anode = y_gem3 + layer_height + spacing
                        dpg.draw_rectangle((padding_x, y_anode), (canvas_width - padding_x, y_anode + layer_height), color=c[2], fill=f[2], thickness=1)
                        dpg.draw_text((text_x_pos, y_anode + layer_height/2 - text_padding_y//2), tag="AnodeTxt", size=14, text = '  Anode')
                    #### ABSOLUTE VOLTAGES ##### 
                    with dpg.group():
                        labels = ['Cathode', 'Top GEM +', 'Top GEM -', 'Mid GEM +', 'Mid GEM -', 'Low GEM +', 'Low GEM -', 'Anode']
                        dpg.add_spacer(height=layer_height - text_padding_y)
                        for i in range(8):
                            h=(layer_height-text_padding_y*5//2) if i%2 else (spacing-text_padding_y//2)
                            dpg.add_input_float(label=labels[i],default_value=0, width = 60,step=0,format="%.0f V",tag = self.v_tags[i],callback=self.update_voltages_callback)
                            dpg.add_spacer(height=h) # Used to vertica)lly align with the rectangle visually
            ch_names = ['Drift','GEM Top+','GEM Top-','GEM Mid+','GEM Mid-','GEM Low+','GEM Low-']
            delta_names = ['Drift', 'Top GEM', 'Top Transfer', 'Middle GEM', 'Bottom Transfer', 'Bottom GEM', 'Induction']
            names = delta_names

            dpg.add_separator()
            with dpg.group(horizontal = True):
                with dpg.group(horizontal = False):
                    dpg.add_checkbox(label="Equal GEM Voltages", 
                        tag="checkbox_a", callback=self.print_checkbox_state)
                    dpg.add_checkbox(label="Ramp Together (%)", 
                        tag="checkbox_b", callback=self.print_checkbox_state)
                    with dpg.group(horizontal = True):               
                        dpg.add_button(label="Increment All", 
                            tag="IncrementAll", callback=self.handle_button_click)
                        dpg.add_text(' by')
                        dpg.add_input_float(tag = 'v_increment',default_value = 50, format="%.0f V",step=0,width = 50)
                    with dpg.group(horizontal = True):               
                        dpg.add_button(label="Increment All", 
                            tag="IncrementPercentage", callback=self.handle_button_click)
                        dpg.add_text(' by')
                        dpg.add_input_float(tag = 'pct_increment',default_value = 5, format="%.0f %%",step=0,width = 50)
                dpg.add_spacer(width = 20)
                dpg.add_button(label="Send All Values", tag='SendAll', callback=self.handle_button_click,height = 75,width = 100)

            dpg.add_button(label="Ramp All to 0V",tag = 'RampOff',callback=self.FX.RampAll)
            dpg.add_button(label="Clear Faults", tag = 'ClearFaults', callback = self.FX.Reset)
            dpg.add_button(label="Save Current Config", tag = 'SaveConfig',callback  = self.save_config)
            #TODO: Get Saveconfig working! 

        # Run the initial callback once everything is set up to display the default values correctly
        dpg.set_frame_callback(1, self.update_voltages_callback)

        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

if __name__ == '__main__':

    G = voltageGUI()
    G.start_app()