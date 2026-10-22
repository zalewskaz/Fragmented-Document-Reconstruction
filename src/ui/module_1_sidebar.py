import customtkinter as ctk
import cv2
import numpy as np
from models import SplittingMethod, ProjectSession

class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, cmd_preview_split, **kwargs):
        super().__init__(master, width=220, corner_radius=0, **kwargs)
        
        self.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(
            self,
            text="Fragmented Docs",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 15))

        # Parameters menu
        self.param_frame = ctk.CTkFrame(self) 
        self.param_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.param_label = ctk.CTkLabel(
            self.param_frame, 
            text="Select parameters",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.param_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Cutting mode selection
        # może to jeszcze rozdzielić, jak wyjdzie za dużo w jednym dropdownie
        self.split_opt_container = ctk.CTkFrame(self.param_frame, fg_color="transparent")
        self.split_opt_container.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.split_opt_container.grid_columnconfigure(1, weight=1)

        self.split_opt_label = ctk.CTkLabel(
            self.split_opt_container, 
            text="Splitting method:"
        )
        self.split_opt_label.grid(row=0, column=0, padx=(0, 10))

        split_methods = [metoda.value for metoda in SplittingMethod]

        self.split_opt_dropdown = ctk.CTkOptionMenu(
            self.split_opt_container,
            values=split_methods,
            command=self.split_parameters_show
        )
        self.split_opt_dropdown.grid(row=0, column=1, columnspan=2, sticky="ew")
        self.split_opt_dropdown.set(SplittingMethod.EVEN_VERTICAL.value)
        ProjectSession.splitting_method = SplittingMethod.EVEN_VERTICAL.value

        self.dynamic_params_frame = ctk.CTkFrame(self.param_frame, fg_color="transparent")
        self.dynamic_params_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.dynamic_params_frame.grid_columnconfigure(1, weight=1)

        self.split_parameters_show(SplittingMethod.EVEN_VERTICAL.value)

        # Reset button
        self.reset_params_button = ctk.CTkButton(
            self.param_frame, 
            text="Reset", 
            command=self.reset_params_action
        )
        self.reset_params_button.grid(row=3, column=0, padx=20, pady=10)

        # Set button
        self.set_params_button = ctk.CTkButton(
            self.param_frame, 
            text="Set", 
            command=self.set_params_action
        )
        self.set_params_button.grid(row=3, column=1, padx=20, pady=10)

        # Preview split button
        self.prev_split_button = ctk.CTkButton(
            self, 
            text="Preview split", 
            command=cmd_preview_split
        )
        self.prev_split_button.grid(row=2, column=0, padx=20, pady=10)

    def get_splitting_method(self):
        return self.split_opt_dropdown.get()

    def split_parameters_show(self, splitting_mode_str):
        splitting_mode = SplittingMethod(splitting_mode_str)

        for widget in self.dynamic_params_frame.winfo_children():
            widget.destroy()

        match splitting_mode:
            # TODO zamienić pola do wpisywania na idk listę?

            case SplittingMethod.EVEN_VERTICAL | SplittingMethod.EVEN_HORIZONTAL:
                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of stripes:"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.stripes_n_entry = ctk.CTkEntry(self.dynamic_params_frame)
                self.stripes_n_entry.insert(0, "5")
                self.stripes_n_entry.grid(row=0, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Stripes' width:"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")

                self.stripes_width_entry = ctk.CTkEntry(self.dynamic_params_frame)
                self.stripes_width_entry.grid(row=1, column=1, pady=5, sticky="ew")

                def on_n_typing(event):
                    if self.stripes_n_entry.get():
                        self.stripes_width_entry.delete(0, "end")

                def on_width_typing(event):
                    if self.stripes_width_entry.get():
                        self.stripes_n_entry.delete(0, "end")

                self.stripes_n_entry.bind("<KeyRelease>", on_n_typing)
                self.stripes_width_entry.bind("<KeyRelease>", on_width_typing)
        
        pass
        
    # TODO resetowanie parametrów   
    def reset_params_action(self):
        pass

    def set_params_action(self):
        ProjectSession.splitting_method = self.split_opt_dropdown.get()

    def get_split_parameters(self):
        current_method = self.split_opt_dropdown.get()
        params = {}

        try:
            match current_method:
                case SplittingMethod.EVEN_VERTICAL:
                    val_n = self.stripes_n_entry.get()
                    if val_n:
                        params["stripes_vertical_n"] = int(val_n)
                        
                    val_width = self.stripes_width_entry.get()
                    if val_width:
                        params["stripes_width"] = int(val_width)

                case SplittingMethod.EVEN_HORIZONTAL:
                    val_n = self.stripes_n_entry.get()
                    if val_n:
                        params["stripes_horizontal_n"] = int(val_n)
                        
                    val_width = self.stripes_width_entry.get()
                    if val_width:
                        params["stripes_height"] = int(val_width)

        except ValueError:
            print("Value error")
            
        return params