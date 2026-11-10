import customtkinter as ctk
import cv2
import numpy as np
from models import ReconstructingMethod, ProjectSession, RotationOption, EdgePixelAttributionOption
from .CTkSpinbox import CTkSpinbox

class SidebarFrameModule2(ctk.CTkFrame):
    def __init__(self, master, cmd_run_extract, cmd_run_reconstruct, cmd_save, **kwargs):
        super().__init__(master, width=220, corner_radius=0, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        self.grid_rowconfigure(2, weight=1)

        # Extract
        self.extract_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.extract_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.extract_frame.grid_columnconfigure(0, weight=1)
        
        # Reconstruct
        self.reconstruct_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.reconstruct_frame.grid(row=1, column=0, sticky="nsew")
        self.reconstruct_frame.grid_columnconfigure(0, weight=1)

        self.init_extract(frame=self.extract_frame, cmd_run=cmd_run_extract)
        self.init_reconstruct(frame=self.reconstruct_frame, cmd_run=cmd_run_reconstruct, cmd_save=cmd_save)
        self.set_reconstruct_enabled(False)

    def init_extract(self, frame, cmd_run):
        # title
        self.title = ctk.CTkLabel(
            frame,
            text="Extracting",
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title.grid(row=0, column=0, padx=10, pady=10)

        # show fragment borders button
        self.run_extract_button = ctk.CTkButton(
            frame, 
            text="Show fragment borders", 
            command=cmd_run
        )
        self.run_extract_button.grid(row=1, column=0, padx=20, pady=10)

        # TODO: optionally add a manual override

    def init_reconstruct(self, frame, cmd_run, cmd_save):
        # title
        self.title = ctk.CTkLabel(
            frame,
            text="Reconstructing",
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title.grid(row=0, column=0, padx=10, pady=10)

        # Parameters menu
        self.param_frame = ctk.CTkFrame(frame) 
        self.param_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.param_frame.grid_columnconfigure((0, 1), weight=1)

        self.param_label = ctk.CTkLabel(
            self.param_frame, 
            text="Select parameters",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.param_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Reconstructing mode selection
        # TODO: optionally change into two dropdowns
        self.reconstruct_opt_container = ctk.CTkFrame(self.param_frame, fg_color="transparent")
        self.reconstruct_opt_container.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.reconstruct_opt_container.grid_columnconfigure(1, weight=1)

        self.reconstruct_opt_label = ctk.CTkLabel(
            self.reconstruct_opt_container, 
            text="Reconstructing method:"
        )
        self.reconstruct_opt_label.grid(row=0, column=0, padx=(0, 10))

        reconstruct_methods = [method.value for method in ReconstructingMethod]

        self.reconstruct_opt_dropdown = ctk.CTkOptionMenu(
            self.reconstruct_opt_container,
            values=reconstruct_methods,
            command=self.reconstruct_parameters_show
        )
        self.reconstruct_opt_dropdown.grid(row=0, column=1, columnspan=2, sticky="ew")
        self.reconstruct_opt_dropdown.set(ReconstructingMethod.RECONSTRUCTING.value)

        # Parameters for the selected splitting method
        self.dynamic_params_frame = ctk.CTkFrame(self.param_frame, fg_color="transparent")
        self.dynamic_params_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.dynamic_params_frame.grid_columnconfigure(1, weight=1)

        self.reconstruct_parameters_show(ReconstructingMethod.RECONSTRUCTING.value)

        # Reset button
        self.reset_params_button = ctk.CTkButton(
            self.param_frame, 
            text="Reset", 
            command=self.reset_params_action
        )
        self.reset_params_button.grid(row=3, column=0, padx=20, pady=10, columnspan=2)

        # Run button
        self.run_button = ctk.CTkButton(
                    self, 
                    text="Run", 
                    command=cmd_run
                )
        self.run_button.grid(row=5, column=0, padx=20, pady=10)

        # Save button - only in single mode, greyed out until there's a result to save
        self.save_button = ctk.CTkButton(
            self,
            text="Save",
            command=cmd_save,
            state="disabled",
        )
        self.save_button.grid(row=6, column=0, padx=20, pady=10)

    def reconstruct_parameters_show(self, reconstructing_mode_str):
        pass

    def get_splitting_method(self):
        """Retrieves the currently selected reconstructing method."""
        return self.reconstruct_opt_dropdown.get()

    def reset_params_action(self):
        """Resets parameters to their default state."""
        reconstructing_method = self.get_reconstructing_method()
        self.reconstruct_parameters_show(reconstructing_method)

    def set_save_enabled(self, enabled: bool):
        """Enables or disables the Save button."""
        self.save_button.configure(state="normal" if enabled else "disabled")

    def set_reconstruct_enabled(self, enabled: bool):
        """Enables or disables the recuntraction options."""
        self.reconstruct_opt_dropdown.configure(state="normal" if enabled else "disabled")
        # TODO: disable everything in the dynamic params frame
        self.reset_params_button.configure(state="normal" if enabled else "disabled")
        self.run_button.configure(state="normal" if enabled else "disabled")
        # TODO: disable save if needed
        # self.save_button.configure(state="normal" if enabled else "disabled")

    def set_batch_mode(self, is_batch: bool):
        """Configures the UI layout for batch mode (one "Run & Save" button) or single mode (separate "Run" and "Save" buttons)."""
        if is_batch:
            self.run_button.configure(text="Run & Save")
            self.save_button.grid_remove()
        else:
            self.run_button.configure(text="Run")
            self.save_button.grid()
        self.set_save_enabled(False)