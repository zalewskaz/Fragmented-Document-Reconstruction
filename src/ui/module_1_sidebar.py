import customtkinter as ctk
import cv2
import numpy as np
from models import SplittingMethod, ProjectSession, RotationOption, EdgePixelAttributionOption
from .CTkSpinbox import CTkSpinbox

class SidebarFrameModule1(ctk.CTkFrame):
    """
    A sidebar widget containing parameter controls and action buttons for the first module of the application.

    This frame holds the UI elements necessary to select a splitting method, 
    adjust its specific parameters dynamically, and trigger main actions 
    like previewing the split, running the algorithm, and saving the results.

    Args:
        master (Any): The parent widget to which this sidebar belongs.
        cmd_preview_split (callable): Callback function executed when the "Preview Split" button is pressed.
        cmd_run (callable): Callback function executed when the "Run" button is pressed.
        cmd_save (callable): Callback function executed when the "Save" button is pressed.
        warning_callback (callable): Function used by the backend to display UI warning pop-ups.
        **kwargs: Additional keyword arguments passed to the underlying CTkFrame.
    """

    def __init__(self, master, cmd_preview_split, cmd_run, cmd_save, warning_callback, **kwargs):
        super().__init__(master, width=220, corner_radius=0, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.warning_callback = warning_callback
        
        self.grid_rowconfigure(10, weight=1)

        # Parameters menu
        self.param_frame = ctk.CTkFrame(self) 
        self.param_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.param_frame.grid_columnconfigure((0, 1), weight=1)

        self.param_label = ctk.CTkLabel(
            self.param_frame, 
            text="Select parameters",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.param_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Cutting mode selection
        # TODO: optionally change into two dropdowns
        self.split_opt_container = ctk.CTkFrame(self.param_frame, fg_color="transparent")
        self.split_opt_container.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.split_opt_container.grid_columnconfigure(1, weight=1)

        self.split_opt_label = ctk.CTkLabel(
            self.split_opt_container, 
            text="Splitting method:"
        )
        self.split_opt_label.grid(row=0, column=0, padx=(0, 10))

        split_methods = [method.value for method in SplittingMethod]

        self.split_opt_dropdown = ctk.CTkOptionMenu(
            self.split_opt_container,
            values=split_methods,
            command=self.split_parameters_show
        )
        self.split_opt_dropdown.grid(row=0, column=1, columnspan=2, sticky="ew")
        self.split_opt_dropdown.set(SplittingMethod.EVEN_VERTICAL.value)

        # Parameters for the selected splitting method
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
        self.reset_params_button.grid(row=3, column=0, padx=20, pady=10, columnspan=2)

        # Preview split button
        self.prev_split_button = ctk.CTkButton(
            self, 
            text="Preview split", 
            command=cmd_preview_split
        )
        self.prev_split_button.grid(row=2, column=0, padx=20, pady=10)

        # Piece rotation dropdown
        self.rotation_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.rotation_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.rotation_frame.grid_columnconfigure(1, weight=1)

        self.rotation_label = ctk.CTkLabel(
            self.rotation_frame,
            text="Piece rotation:"
        )
        self.rotation_label.grid(row=0, column=0, padx=(0, 10))

        rotation_options = [rotation_option.value for rotation_option in RotationOption]

        self.rotation_dropdown = ctk.CTkOptionMenu(
            self.rotation_frame,
            values=rotation_options
        )
        self.rotation_dropdown.grid(row=0, column=1, sticky="ew")

        self.rotation_dropdown.set(RotationOption.NO_ROTATION.value)

        # Edge pixel attribution dropdown
        self.edge_pixel_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.edge_pixel_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        self.edge_pixel_frame.grid_columnconfigure(1, weight=1)

        self.edge_pixel_label = ctk.CTkLabel(
            self.edge_pixel_frame,
            text="Edge pixel attribution:"
        )
        self.edge_pixel_label.grid(row=0, column=0, padx=(0, 10))

        edge_pixel_options = [edge_pixel_option.value for edge_pixel_option in EdgePixelAttributionOption]

        self.edge_pixel_dropdown = ctk.CTkOptionMenu(
            self.edge_pixel_frame,
            values=edge_pixel_options
        )
        self.edge_pixel_dropdown.grid(row=0, column=1, sticky="ew")

        self.edge_pixel_dropdown.set(EdgePixelAttributionOption.DISAPPEAR.value)

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

    def set_batch_mode(self, is_batch: bool):
        """Configures the UI layout for batch mode (one "Run & Save" button) or single mode (separate "Run" and "Save" buttons)."""
        if is_batch:
            self.run_button.configure(text="Run & Save")
            self.save_button.grid_remove()
        else:
            self.run_button.configure(text="Run")
            self.save_button.grid()
        self.set_save_enabled(False)

    def set_batch_running(self, running: bool):
        """Locks or unlocks the Run and Preview buttons during batch processing, so the run can't be started twice."""
        self.run_button.configure(state="disabled" if running else "normal")
        self.prev_split_button.configure(state="disabled" if running else "normal")

    def set_save_enabled(self, enabled: bool):
        """Enables or disables the Save button."""
        self.save_button.configure(state="normal" if enabled else "disabled")

    def get_splitting_method(self):
        """Retrieves the currently selected splitting method."""
        return self.split_opt_dropdown.get()

    def get_rotation_option(self) -> str:
        """Retrieves the currently selected rotation option."""
        return self.rotation_dropdown.get()

    def get_edge_pixel_option(self) -> str:
        """Retrieves the currently selected edge pixel generation option."""
        return self.edge_pixel_dropdown.get()

    def split_parameters_show(self, splitting_mode_str):
        """
        Shows parameters for the selected splitting method.

        Args:
            splitting_mode_str (string): Name of the selected splitting method.
        """

        splitting_mode = SplittingMethod(splitting_mode_str)

        for widget in self.dynamic_params_frame.winfo_children():
            widget.destroy()

        # shows proper parameters for the selected method
        match splitting_mode:
            case SplittingMethod.EVEN_VERTICAL | SplittingMethod.EVEN_HORIZONTAL:
                def on_n_typing(value):
                    if value.strip() != "":
                        self.strips_width_entry.clear()

                def on_width_typing(value):
                    if value.strip() != "":
                        self.strips_n_entry.clear()
                
                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of strips:"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40,
                    command=on_n_typing)
                self.strips_n_entry.grid(row=0, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Strips' width:"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")

                self.strips_width_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=40, 
                    min_value=20, 
                    max_value=200,
                    command=on_width_typing)
                self.strips_width_entry.clear()
                self.strips_width_entry.grid(row=1, column=1, pady=5, sticky="ew")

            case SplittingMethod.RANDOM_VERTICAL | SplittingMethod.RANDOM_HORIZONTAL:             
                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Random number of strips"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

                def toggle_strips_entry():
                    if self.random_strips_n_check.get() == 1:
                        self.strips_n_entry.block()
                    else:
                        self.strips_n_entry.unblock()

                self.random_strips_n_check = ctk.CTkCheckBox(
                    self.dynamic_params_frame,
                    text="",
                    command=toggle_strips_entry
                )
                self.random_strips_n_check.grid(row=0, column=1, pady=5, sticky="w")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of strips:"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40
                    )
                self.strips_n_entry.grid(row=1, column=1, pady=5, sticky="ew")

            case SplittingMethod.EVEN_RECTANGLES:
                def on_vertical_n_typing(value):
                    if value.strip() != "":
                        self.strips_width_entry.clear()

                def on_width_typing(value):
                    if value.strip() != "":
                        self.strips_vertical_n_entry.clear()

                def on_horizontal_n_typing(value):
                    if value.strip() != "":
                        self.strips_height_entry.clear()

                def on_height_typing(value):
                    if value.strip() != "":
                        self.strips_horizontal_n_entry.clear()

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of vertical strips:"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_vertical_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40,
                    command=on_vertical_n_typing)
                self.strips_vertical_n_entry.grid(row=0, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Rectangles' width:"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")

                self.strips_width_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=40, 
                    min_value=20, 
                    max_value=200,
                    command=on_width_typing)
                self.strips_width_entry.clear()
                self.strips_width_entry.grid(row=1, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of horizontal strips:"
                ).grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_horizontal_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40,
                    command=on_horizontal_n_typing)
                self.strips_horizontal_n_entry.grid(row=2, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Rectangles' height:"
                ).grid(row=3, column=0, padx=(0, 10), pady=5, sticky="w")

                self.strips_height_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=40, 
                    min_value=20, 
                    max_value=200,
                    command=on_height_typing)
                self.strips_height_entry.clear()
                self.strips_height_entry.grid(row=3, column=1, pady=5, sticky="ew")

            case SplittingMethod.RANDOM_RECTANGLES:
                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Random number of vertical strips"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Random number of horizontal strips"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")

                def toggle_vertical_strips_entry():
                    if self.random_vertical_strips_n_check.get() == 1:
                        self.strips_vertical_n_entry.block()
                    else:
                        self.strips_vertical_n_entry.unblock()

                def toggle_horizontal_strips_entry():
                    if self.random_horizontal_strips_n_check.get() == 1:
                        self.strips_horizontal_n_entry.block()
                    else:
                        self.strips_horizontal_n_entry.unblock()

                self.random_vertical_strips_n_check = ctk.CTkCheckBox(
                    self.dynamic_params_frame,
                    text="",
                    command=toggle_vertical_strips_entry
                )
                self.random_vertical_strips_n_check.grid(row=0, column=1, pady=5, sticky="w")

                self.random_horizontal_strips_n_check = ctk.CTkCheckBox(
                    self.dynamic_params_frame,
                    text="",
                    command=toggle_horizontal_strips_entry
                )
                self.random_horizontal_strips_n_check.grid(row=1, column=1, pady=5, sticky="w")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of vertical strips:"
                ).grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_vertical_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40
                    )
                self.strips_vertical_n_entry.grid(row=2, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of horizontal strips:"
                ).grid(row=3, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_horizontal_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40
                    )
                self.strips_horizontal_n_entry.grid(row=3, column=1, pady=5, sticky="ew")

            case SplittingMethod.SEGMENTED_STRIPS:
                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Equal segments per strip"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

                def toggle_equal_segments_entry():
                    if self.equal_segments_strip_check.get() == 0:
                        self.random_horizontal_strips_n_check.select()
                        self.strips_horizontal_n_entry.block()

                self.equal_segments_strip_check = ctk.CTkCheckBox(
                    self.dynamic_params_frame,
                    text="",
                    command=toggle_equal_segments_entry
                )
                self.equal_segments_strip_check.grid(row=0, column=1, pady=5, sticky="w")
                self.equal_segments_strip_check.select()

                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Even strips' width"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")

                self.even_strips_width = ctk.CTkCheckBox(self.dynamic_params_frame, text="")
                self.even_strips_width.grid(row=1, column=1, pady=5, sticky="w")
                self.even_strips_width.select()

                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Random number of vertical strips"
                ).grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")

                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Random number of horizontal strips"
                ).grid(row=3, column=0, padx=(0, 10), pady=5, sticky="w")

                def toggle_vertical_strips_entry():
                    if self.random_vertical_strips_n_check.get() == 1:
                        self.strips_vertical_n_entry.block()
                    else:
                        self.strips_vertical_n_entry.unblock()

                def toggle_horizontal_strips_entry():
                    if self.random_horizontal_strips_n_check.get() == 1:
                        self.strips_horizontal_n_entry.block()
                    else:
                        self.strips_horizontal_n_entry.unblock()

                self.random_vertical_strips_n_check = ctk.CTkCheckBox(
                    self.dynamic_params_frame,
                    text="",
                    command=toggle_vertical_strips_entry
                )
                self.random_vertical_strips_n_check.grid(row=2, column=1, pady=5, sticky="w")

                self.random_horizontal_strips_n_check = ctk.CTkCheckBox(
                    self.dynamic_params_frame,
                    text="",
                    command=toggle_horizontal_strips_entry
                )
                self.random_horizontal_strips_n_check.grid(row=3, column=1, pady=5, sticky="w")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of vertical strips:"
                ).grid(row=4, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_vertical_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40
                    )
                self.strips_vertical_n_entry.grid(row=4, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of horizontal strips:"
                ).grid(row=5, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.strips_horizontal_n_entry = CTkSpinbox(
                    self.dynamic_params_frame, 
                    start_value=5, 
                    max_value=40
                    )
                self.strips_horizontal_n_entry.grid(row=5, column=1, pady=5, sticky="ew")

            case SplittingMethod.STRAIGHT_POLYGONS:
                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Recursive cutting"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

                self.recursive_cutting_check = ctk.CTkCheckBox(self.dynamic_params_frame, text="")
                self.recursive_cutting_check.grid(row=0, column=1, pady=5, sticky="w")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of cuts:"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.lines_n_entry = CTkSpinbox(
                    self.dynamic_params_frame,
                    start_value=10,
                    min_value=2,
                    max_value=100
                    )
                self.lines_n_entry.grid(row=1, column=1, pady=5, sticky="ew")

            case SplittingMethod.POLYLINE_POLYGONS:
                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Number of polylines:"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

                self.lines_n_entry = CTkSpinbox(
                    self.dynamic_params_frame,
                    start_value=5,
                    min_value=2,
                    max_value=10
                    )
                self.lines_n_entry.grid(row=0, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of vertices:"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.points_k_entry = CTkSpinbox(
                    self.dynamic_params_frame,
                    start_value=2,
                    min_value=0,
                    max_value=5
                    )
                self.points_k_entry.grid(row=1, column=1, pady=5, sticky="ew")

            case SplittingMethod.VORONOI_POLYGONS:
                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Number of points:"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

                self.points_n_entry = CTkSpinbox(
                    self.dynamic_params_frame,
                    start_value=5,
                    min_value=2,
                    max_value=150
                    )
                self.points_n_entry.grid(row=0, column=1, pady=5, sticky="ew")

            case SplittingMethod.BEZIER_CURVES:
                ctk.CTkLabel(
                    self.dynamic_params_frame,
                    text="Number of curves:"
                ).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

                self.lines_n_entry = CTkSpinbox(
                    self.dynamic_params_frame,
                    start_value=5,
                    min_value=1,
                    max_value=15
                    )
                self.lines_n_entry.grid(row=0, column=1, pady=5, sticky="ew")

                ctk.CTkLabel(
                    self.dynamic_params_frame, 
                    text="Number of control points on the curve:"
                ).grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
                
                self.points_k_entry = CTkSpinbox(
                    self.dynamic_params_frame,
                    start_value=2,
                    min_value=1,
                    max_value=5
                    )
                self.points_k_entry.grid(row=1, column=1, pady=5, sticky="ew")
        
        pass
        
    def reset_params_action(self):
        """Resets parameters to their default state."""
        splitting_method = self.get_splitting_method()
        self.split_parameters_show(splitting_method)

    def get_split_parameters(self):
        """Retrieves the currently selected parameters."""
        current_method = self.split_opt_dropdown.get()
        params = {}
        params["warning_callback"] = self.warning_callback

        try:
            match current_method:
                case SplittingMethod.EVEN_VERTICAL:
                    val_n = self.strips_n_entry.get()
                    if val_n:
                        params["strips_vertical_n"] = int(val_n)
                        
                    val_width = self.strips_width_entry.get()
                    if val_width:
                        params["strips_width"] = int(val_width)

                case SplittingMethod.EVEN_HORIZONTAL:
                    val_n = self.strips_n_entry.get()
                    if val_n:
                        params["strips_horizontal_n"] = int(val_n)
                        
                    val_width = self.strips_width_entry.get()
                    if val_width:
                        params["strips_height"] = int(val_width)

                case SplittingMethod.RANDOM_VERTICAL:
                    val_n = self.strips_n_entry.get()
                    if val_n:
                        params["strips_vertical_n"] = int(val_n)

                case SplittingMethod.RANDOM_HORIZONTAL:
                    val_n = self.strips_n_entry.get()
                    if val_n:
                        params["strips_horizontal_n"] = int(val_n)

                case SplittingMethod.EVEN_RECTANGLES:
                    horizontal_n = self.strips_horizontal_n_entry.get()
                    if horizontal_n:
                        params["strips_horizontal_n"] = int(horizontal_n)

                    vertical_n = self.strips_vertical_n_entry.get()
                    if vertical_n:
                        params["strips_vertical_n"] = int(vertical_n)       

                    width = self.strips_width_entry.get()
                    if width:
                        params["strips_width"] = int(width)

                    height = self.strips_height_entry.get()
                    if height:
                        params["strips_height"] = int(height)  

                case SplittingMethod.RANDOM_RECTANGLES:
                    horizontal_n = self.strips_horizontal_n_entry.get()
                    if horizontal_n:
                        params["strips_horizontal_n"] = int(horizontal_n)

                    vertical_n = self.strips_vertical_n_entry.get()
                    if vertical_n:
                        params["strips_vertical_n"] = int(vertical_n)     

                case SplittingMethod.SEGMENTED_STRIPS:
                    horizontal_n = self.strips_horizontal_n_entry.get()
                    if horizontal_n:
                        params["strips_horizontal_n"] = int(horizontal_n)

                    vertical_n = self.strips_vertical_n_entry.get()
                    if vertical_n:
                        params["strips_vertical_n"] = int(vertical_n) 

                    even_width = self.even_strips_width.get()
                    params["even_width"] = bool(even_width)

                    equal_segments = self.equal_segments_strip_check.get()
                    params["equal_segments"] = bool(equal_segments)

                case SplittingMethod.STRAIGHT_POLYGONS:
                    lines_n = self.lines_n_entry.get()
                    if lines_n:
                        params["lines_n"] = int(lines_n)

                    hierarchical = self.recursive_cutting_check.get()
                    params["hierarchical"] = bool(hierarchical)

                case SplittingMethod.POLYLINE_POLYGONS | SplittingMethod.BEZIER_CURVES:
                    lines_n = self.lines_n_entry.get()
                    if lines_n:
                        params["lines_n"] = int(lines_n)   

                    points_k = self.points_k_entry.get()
                    if points_k:
                        params["points_k"] = int(points_k)  

                case SplittingMethod.VORONOI_POLYGONS:
                    points_n = self.points_n_entry.get()
                    if points_n:
                        params["points_n"] = int(points_n)


        except ValueError:
            print("Value error")
            
        return params