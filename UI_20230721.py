import customtkinter
from mainv6 import mainfunc, print_logs
import threading
import json
from final_v28 import list_of_logs
import polars as pl
from plots_20230721 import plots

pl.Config.set_ascii_tables(True)  
customtkinter.set_appearance_mode("light")

thread1 = None
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        f = open("setup_20230714.json", 'r')
        data=json.loads(f.read())
        data_DOE = data['data_DOE']
        data_pump = data['data_pump']
        data_sampleno = data['data_sampleno']
        sc_height = self.winfo_screenheight()
        sc_width = self.winfo_screenwidth()
        dims = f"{sc_width}x{sc_height}"
        g = open('process.txt', 'r')
        self.text_to_read = g.read()
        g.close()
        self.title("Python Data Collection")
        self.file_name = []
        self.prev_index = 0
        print(dims)
        self.geometry(dims)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=0)

        self.sidebar_frame = self.create_frame(self, 0, 0)
        self.middle_frame = self.create_frame(self, 0, 1)
        self.right_frame = self.create_frame(self, 0, 2)
        self.sidebar_frame_lower = self.create_frame(self.sidebar_frame, 3, 0, fg_color_= 'transparent')
        
        self.display_title(master_=self.middle_frame, text_ = "VGuard Data Collection", row_= 0, column_= 1, padx_= 0, pady_= (18, 0), size_ = 36)
        self.display_title(master_=self.sidebar_frame, text_ = "PROCESSES TO BE FOLLOWED", row_= 0, column_= 0, padx_= 0, pady_= (78, 5), size_ = 18)
        self.display_title(master_=self.sidebar_frame, justify_ = 'center', text_ = self.text_to_read, row_= 1, column_= 0, padx_= 20, pady_= (0, 10), size_=16)
        self.display_title(master_=self.sidebar_frame_lower, size_ = 16, text_ = "Select the DOE please!", row_= 2, column_= 0, padx_= (sc_width * 2)//70, pady_= (20, 0))
        self.display_title(master_=self.sidebar_frame_lower, size_ = 16, text_ = "Select the Pump name please!", row_= 4, column_= 0, padx_= (sc_width * 2)//70, pady_= (20, 0))
        self.display_title(master_=self.sidebar_frame_lower, size_ = 16, text_ = "Select the Sample name please!", row_= 6, column_= 0, padx_= (sc_width * 2)//70, pady_= (20, 0))

        self.combobox_var1 = customtkinter.StringVar(value="Select")
        self.combobox_var2 = customtkinter.StringVar(value="Select")
        self.combobox_var3 = customtkinter.StringVar(value="Select")

        self.combobox1 = customtkinter.CTkComboBox(self.sidebar_frame_lower, state = 'readonly', values= data_DOE, font=('Arial', 14), command = self.combobox_callback, variable=self.combobox_var1, corner_radius = 2, justify='left', height=32)
        self.combobox1.grid(row = 3, column= 0, padx = ((sc_width * 1.5)//250, 0), pady=(0, 15))
        self.combobox2 = customtkinter.CTkComboBox(self.sidebar_frame_lower, state = 'readonly', values= data_pump, font=('Arial', 14), command = self.combobox_callback, variable=self.combobox_var2, corner_radius = 2, justify='left' , height=32)
        self.combobox2.grid(row = 5, column= 0, padx = ((sc_width * 1.5)//250, 0), pady=(0, 15))
        self.combobox3 = customtkinter.CTkComboBox(self.sidebar_frame_lower, state = 'readonly', values= data_sampleno, font=('Arial', 14), command = self.combobox_callback, variable=self.combobox_var3, corner_radius = 2, justify='left',  height=32)
        self.combobox3.grid(row = 7, column= 0, padx = ((sc_width * 1.5)//250, 0), pady=(0, 15))
        self.Set_DOE = customtkinter.CTkButton(self.sidebar_frame_lower, text = "Set", command = self.Set_DOE_button, width = 56, height=36, font = ('Arial', 20), state = 'disabled')
        self.Set_DOE.grid(row = 8, column = 0, padx = ((sc_width * 1.5)//200, 0), pady=(15, 20))


        self.Return_Text = customtkinter.CTkTextbox(self.middle_frame, text_color = 'black', font = ("Arial", 22), width=int(sc_width*0.4778), height = int(sc_height*0.15))
        self.Return_Text.grid(row = 1, column = 1, pady = (20,0), padx = (0, 0)) 
        self.Enter_Button = customtkinter.CTkButton(self.middle_frame, text = "Start", command = self.serial_port, width = 60, height=36, state = 'disabled', font = ('Arial', 20))
        self.Enter_Button.grid(row = 2, column = 1, pady = (20, 20), padx = (0, 0))

        self.LogText1 = customtkinter.CTkTextbox(self.middle_frame,  width=int(sc_width*0.4778), font = ("Arial", 18), height = int(sc_height*0.45509))
        self.LogText1.grid(row = 3, column = 1, padx = (0, 0))
        self.LogsToggle = customtkinter.CTkButton(self.middle_frame, text = "View", command = self.toggle, width = 60, height=36, font = ('Arial', 20))
        self.LogsToggle.grid(row = 4, column = 1, pady = (20, 30), padx = (0, 0))
        

        self.display_title(self.right_frame, text_ = 'PROCESSES COMPLETED', row_ = 1, column_= 2, padx_= 5, pady_= (5, 0), size_=18)
        self.LogText = customtkinter.CTkTextbox(self.right_frame, font = ("Arial", 18), width=int(sc_width*0.2831), height = int(sc_height*0.25148))
        self.LogText.grid(row = 0, column = 2, padx = (15, 10), pady = (80, 5))

        self.plots = customtkinter.CTkButton(self.right_frame, text = "Show Plots", command = self.plotting, width = 60, height=36, font = ('Arial', 20))
        self.plots.grid(row = 3, column = 2, pady = (20, 30), padx = (0, 0))
        
        self.after(100, self.logv)
        self.mainloop()

    def serial_port(self):
        global thread1
        self.Enter_Button.configure(state = 'disabled')
        experiment_name = str(self.combobox_var1.get()) + '_' + str(self.combobox_var2.get()) + '_' + str(self.combobox_var3.get())
        thread1 = threading.Thread(target=mainfunc, args=(experiment_name, ), daemon=True)
        thread1.start()

    def logv(self ):
        logs, msg = print_logs()
        self.Return_Text.delete("0.0", "end" + "\n")
        self.Return_Text.insert("0.0", str(msg) + "\n")
        self.LogText.delete("0.0", "end")
        self.LogText.insert("0.0", logs +"\n")
        self.after(2000, self.logv)


    def toggle(self ):
        if len(list_of_logs) != 0: 
            if self.prev_index !=len(list_of_logs):
                content = ''
                for i in range(self.prev_index, len(list_of_logs)):
                    content += (list_of_logs[i]+"\n")
                self.LogText1.insert("end", content)
                self.prev_index = len(list_of_logs)
            self.after(100, self.toggle)


    def combobox_callback(self, choice):
        print("combobox dropdown clicked:", choice)
        if (self.combobox_var1.get()!= 'Select') & (self.combobox_var2.get()!= 'Select') & (self.combobox_var3.get()!= 'Select'):
            self.Set_DOE.configure(state = 'normal')
            print('All variables set')
        else:
            print('All variables not set yet')

    def Set_DOE_button(self):
        self.Enter_Button.configure(state = 'normal')
        self.Set_DOE.configure(state = 'disabled')
        self.combobox1.configure(state='disabled')
        self.combobox2.configure(state='disabled')
        self.combobox3.configure(state='disabled')

    def display_title(self, master_,  text_, row_, column_, padx_, pady_, size_=14, weight_ = 'bold', justify_ = 'left'):
        logo_label = customtkinter.CTkLabel(master = master_, justify=justify_,  text=text_, font=customtkinter.CTkFont(size= size_, weight= weight_))
        logo_label.grid(row = row_, column= column_, padx= padx_, pady = pady_)

    def create_frame(self, master_, row_, column_, width_ = 10, fg_color_ = None):
        frame = customtkinter.CTkFrame(master_, width= width_, corner_radius=0, fg_color= fg_color_)
        frame.grid(row = row_, column= column_, sticky="nsew")
        return frame

    def plotting(self):
        from mainv6 import logpath
        if thread1.is_alive():
            thread1.join()
        print(logpath)
        thread_ = threading.Thread(target = plots, args=(logpath, ))
        thread_.start()

if __name__ == "__main__":
    app = App()
    app.mainloop()