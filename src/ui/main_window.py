from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
import cv2
import numpy as np  
import processing.mask_generator as mask_generator
import processing.image_splitter as image_splitter
import processing.background_arrange as background_arrange
import processing.fragment_rotation as fragment_rotation
from models import SplittingMethod, ProjectSession, ImageFragment, RotationOption
from src.ui.module_2_sidebar import SidebarFrameModule2
from src.utils.io import get_valid_paths, read_image, save_image_as_png, InvalidImageInputError
from ui.module_1_sidebar import SidebarFrameModule1

# params
STATUS_HIDE_AFTER_MS = 5000  
SELECT_SAVE_LOCATION = "Select Save Location"
CHANGE_SAVE_LOCATION = "Change Save Location"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class MainWindow(ctk.CTk):
    """
    The main application window for the document fragmentation tool.

    Manages the overall layout including the top toolbar, central content 
    display area, sidebar for parameter configuration, and status bar. It 
    maintains the global state of the loaded images and save directories, 
    and drives the image processing pipeline.
    """

    def __init__(self):
        """
        Initializes the main window, configures grid layouts, sets up UI 
        components, and establishes the initial session state.
        """

        super().__init__()

        self.title("Fragmented Document Reconstruction")

        width, height = 1200, 750
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1000, 650)

        self.loaded_image_path = None
        self.loaded_image_paths = []  # images to process: just one for a single file, all of them when a folder was picked
        self.save_location_path = None
        self.current_image_display = None 

        self.grid_rowconfigure(0, weight=0)  
        self.grid_rowconfigure(1, weight=1)  
        self.grid_columnconfigure(0, weight=1)  
        self.grid_columnconfigure(1, weight=0, minsize=650)  

        self.setup_top_toolbar()
        self.setup_content_area()
        self.setup_status_bar()

        self.sidebar = SidebarFrameModule1(master=self, cmd_preview_split=self.preview_split_action, cmd_run=self.run_action_splitting, cmd_save=self.save_action_module_1, warning_callback=self.show_warning)
        self.sidebar.grid(row=1, column=1, sticky="nsew")

    def setup_top_toolbar(self):
        """Builds and grids the top toolbar containing file actions and module switching."""

        self.toolbar_frame = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("#2b2b2b", "#1f1f1f"))
        self.toolbar_frame.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.action_menu = ctk.CTkOptionMenu(
            self.toolbar_frame,
            values=self.menu_options(),
            command=self.handle_menu_action,
            width=180
        )
        self.action_menu.set("File Actions...")
        self.action_menu.pack(side="left", padx=(20, 10), pady=15)

        self.module_switch = ctk.CTkSegmentedButton(
            self.toolbar_frame,
            values=["Module 1: Cutter", "Module 2: Assembler"],
            command=self.switch_view
        )
        self.module_switch.pack(side="left", padx=10, pady=15)
        self.module_switch.set("Module 1: Cutter")

    def setup_content_area(self):
        """Initializes the central viewing area for image previews and final results."""

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.display_label = ctk.CTkLabel(
            self.content_frame,
            text="Use the top toolbar to select files/directories and switch between modules.",
            font=ctk.CTkFont(size=16),
            justify="center",
        )
        self.display_label.grid(row=0, column=0)

    def setup_status_bar(self):
        """Sets up the lower status bar for displaying temporary info messages."""

        self.status_frame = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=("#2b2b2b", "#1f1f1f"))
        self.status_frame.pack_propagate(False)
        self.status_label = ctk.CTkLabel(self.status_frame, text="", anchor="w", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left", fill="x", expand=True, padx=20, pady=2)

    def set_status(self, text: str, auto_hide: bool = True):
        """
        Displays a message in the status bar with an optional auto-hide timer.

        Args:
            text (str): The message to display.
            auto_hide (bool, optional): If True, hides the message after a set delay 
                (STATUS_HIDE_AFTER_MS). If False, persists until overwritten. Defaults to True.
        """
        
        start_height = self.status_frame.cget("height") if self.status_frame.winfo_manager() else 0

        self.status_label.configure(text=text)
        self.status_frame.configure(height=start_height)
        self.status_frame.place(relx=0, rely=1, anchor="sw", relwidth=1)
        self.status_frame.lift()  # make sure it's drawn above the other widgets
        self.show_status(text, start_height)

        if auto_hide:
            # self.after(ms, function) is a Tkinter widget method; it calls the function after ms milliseconds 
            self.after(STATUS_HIDE_AFTER_MS, lambda: self.hide_status(text))

    def show_status(self, text: str, height: int):
        """Animates the appearance of the status bar."""
        
        # stop if a newer message has replaced this one 
        if self.status_label.cget("text") != text:
            return

        height = min(height + 2, 28)
        self.status_frame.configure(height=height)
        if height < 28:
            self.after(15, self.show_status, text, height)

    def hide_status(self, text: str, height: int = 28):
        """Animates the disappearance of the status bar."""
        
        # hide the bar only if no newer message has replaced this one in the meantime
        if self.status_label.cget("text") != text:
            return

        if height <= 0:
            self.status_frame.place_forget()
            return

        self.status_frame.configure(height=height)
        self.after(15, self.hide_status, text, height - 2)

    def switch_view(self, view_name: str):
        """Switches the UI context between different application modules."""
        if hasattr(self, 'sidebar') and self.sidebar is not None:
            self.sidebar.destroy()
            self.sidebar = None

        if view_name == "Module 1: Cutter":
            self.sidebar = SidebarFrameModule1(master=self, cmd_preview_split=self.preview_split_action, cmd_run=self.run_action_splitting, cmd_save=self.save_action_module_1, warning_callback=self.show_warning)
            self.sidebar.grid(row=1, column=1, sticky="nsew")
        elif view_name == "Module 2: Assembler":
            self.sidebar = SidebarFrameModule2(master=self, cmd_run_extract=self.run_action_extract, cmd_run_reconstruct=self.run_action_reconstructing, cmd_save=self.save_action_module_2)
            self.sidebar.grid(row=1, column=1, sticky="nsew")
        else:
            pass


    def handle_menu_action(self, choice: str):
        """
        Handles dropdown menu selections for loading files, directories, 
        or updating the designated save path.

        Args:
            choice (str): The menu option selected by the user.
        """
        
        project_root = Path(__file__).resolve().parent.parent.parent
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        try:
            if choice == "Select File":
                file_path = filedialog.askopenfilename(
                    initialdir=data_dir,
                    filetypes=[
                        ("Image / Document Files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                        ("All Files", "*.*"),
                    ],
                )
                if file_path:
                    valid_paths = get_valid_paths(file_path)
                    if valid_paths:
                        self.loaded_image_paths = valid_paths
                        self.loaded_image_path = valid_paths[0]
                        opencv_image = read_image(self.loaded_image_path)
                        ProjectSession.original_image = opencv_image
                        ProjectSession.mask = None
                        ProjectSession.pieces_on_background = None
                        self.sidebar.set_batch_mode(False)
                        self.render_image_on_ui(opencv_image)
                        if hasattr(self.sidebar, 'set_reconstruct_enabled'):
                            self.sidebar.set_reconstruct_enabled(False)

            elif choice == "Select Directory":
                folder_path = filedialog.askdirectory(initialdir=data_dir)
                if folder_path:
                    valid_paths = sorted(get_valid_paths(folder_path))
                    if valid_paths:
                        self.loaded_image_paths = valid_paths
                        self.loaded_image_path = valid_paths[0]
                        opencv_image = read_image(self.loaded_image_path)
                        ProjectSession.original_image = opencv_image
                        ProjectSession.mask = None
                        ProjectSession.pieces_on_background = None
                        # a folder with just one image works like a single file
                        self.sidebar.set_batch_mode(len(valid_paths) > 1)
                        self.render_image_on_ui(opencv_image)
                        messagebox.showinfo("Folder Loaded", f"Loaded folder successfully. Found {len(valid_paths)} valid images.")
                        if hasattr(self.sidebar, 'set_reconstruct_enabled'):
                            self.sidebar.set_reconstruct_enabled(False)

            elif choice in (SELECT_SAVE_LOCATION, CHANGE_SAVE_LOCATION):
                self.choose_save_location()

        except Exception as e:
            messagebox.showerror("Error", str(e))

        self.action_menu.set("File Actions...")

    def menu_options(self) -> list[str]:
        """Generates dynamic menu options based on current UI state."""
        
        save_option = CHANGE_SAVE_LOCATION if self.save_location_path is not None else SELECT_SAVE_LOCATION
        return ["Select File", "Select Directory", save_option]

    def choose_save_location(self) -> bool:
        """Prompts the user to select an output directory for saved files."""
        
        if self.save_location_path is not None and self.save_location_path.is_dir():
            initial_dir = self.save_location_path
        else:
            initial_dir = Path(__file__).resolve().parent.parent.parent / "data"

        save_path = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Choose Save Directory",
            mustexist=True,
        )

        if save_path:
            self.save_location_path = Path(save_path)
            self.action_menu.configure(values=self.menu_options())
            return True
        return False

    def ensure_image_loaded(self) -> bool:
        """
        Validates that an image has been successfully loaded into the session.

        Returns:
            bool: True if an image is loaded, False otherwise (triggers a UI warning to load an image first).
        """
        
        if ProjectSession.original_image is None:
            messagebox.showwarning(
                "No Image Loaded",
                "Please load an image first using File Actions → Select File / Select Directory.",
            )
            return False
        return True

    def ensure_save_location(self) -> bool:
        """
        Validates that a save directory is selected, displaying a pop-up that leads to folder picker if not.

        Returns:
            bool: True if a save path exists or is newly selected, False if the user cancels folder selection.
        """
        
        if self.save_location_path is not None:
            return True

        return self.choose_save_location()

    def render_image_on_ui(self, cv_img):
        """
        Converts an OpenCV BGR array into a format supported by CustomTkinter (RGB -> Pillow -> CTkImage) and displays it.

        Args:
            cv_img (np.ndarray): The OpenCV image matrix to render.
        """
        
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)


        max_width, max_height = 800, 550
        pil_image.thumbnail((max_width, max_height))

        self.current_image_display = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)

        self.display_label.configure(text="", image=self.current_image_display)

    def preview_split_action(self):
        """
        Generates and renders a visual preview of the calculated cut lines on the source image.
        """
        if not self.ensure_image_loaded():
            return

        image = ProjectSession.original_image.copy()
        height, width = image.shape[:2]
        dynamic_params = self.sidebar.get_split_parameters()
        current_method = self.sidebar.split_opt_dropdown.get()

        ProjectSession.mask = mask_generator.generate_mask(current_method, height, width, **dynamic_params)

        # for the preview we thicken lines
        # big images are shrunk more on screen so they get a bigger kernel
        kernel_size = (5, 5) if max(height, width) > 1500 else (3, 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, kernel_size)
        preview_lines = cv2.dilate(ProjectSession.mask.astype(np.uint8), kernel)

        image[preview_lines == 1] = [0, 0, 255]

        self.render_image_on_ui(image)
        # the screen now shows the preview instead of the result, so there's nothing to save until the next Run
        self.sidebar.set_save_enabled(False)

    def fragment_image(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Executes the full fragmentation pipeline on a single image: cuts the image into pieces, rotates them (if such option is selected) and scatters them on a background.

        Args:
            image (np.ndarray): The original source image matrix.
            mask (np.ndarray): The binary cut mask.

        Returns:
            np.ndarray: The finalized, composited image of the scattered fragments.
        """
        
        height, width = image.shape[:2]

        # cut the image into pieces along the mask lines
        edge_pixel_option = self.sidebar.get_edge_pixel_option()
        fragments_list = image_splitter.split_image(image, mask, edge_pixel_option)

        # rotate pieces according to the selected dropdown option
        if self.sidebar.get_rotation_option() == RotationOption.ROTATION_RANDOM.value:
            fragments_list = fragment_rotation.rotate_fragments_randomly(fragments_list)
        elif self.sidebar.get_rotation_option() == RotationOption.ROTATION_90DEG.value:
            fragments_list = fragment_rotation.rotate_fragments_90deg(fragments_list)
        elif self.sidebar.get_rotation_option() == RotationOption.ROTATION_180DEG.value:
                    fragments_list = fragment_rotation.rotate_fragments_180deg(fragments_list)

        ProjectSession.fragments = fragments_list

        # scatter the pieces on a background that contrasts with the document
        bg_colour = background_arrange.pick_background_colour(image)
        pieces_on_background = background_arrange.arrange_on_background(height, width, fragments_list, bg_colour)
        ProjectSession.pieces_on_background = pieces_on_background

        return pieces_on_background

    def run_action_splitting(self):
        """
        Executes the fragmentation task based on the current UI parameters.

        In single-file mode, it renders the result to the screen, pending manual save.
        In batch mode, it processes and saves the first image, then triggers `run_batch` 
        to process the remaining queue automatically.
        """
        
        if not self.ensure_image_loaded():
            return

        is_batch = len(self.loaded_image_paths) > 1
        if is_batch and not self.ensure_save_location():
            # the user cancelled the folder picker so we stop the run
            messagebox.showwarning(
                "Directory Not Selected",
                "No save directory was selected, so nothing was processed or saved.",
            )
            return

        image = ProjectSession.original_image.copy()
        height, width = image.shape[:2]

        # generate a mask if it hasn't been generated already
        if ProjectSession.mask is None:
            dynamic_params = self.sidebar.get_split_parameters()
            current_method = self.sidebar.split_opt_dropdown.get()
            ProjectSession.mask = mask_generator.generate_mask(current_method, height, width, **dynamic_params)

        pieces_on_background = self.fragment_image(image, ProjectSession.mask)

        # show the result right away - update_idletasks() makes sure it's drawn before we continue
        self.render_image_on_ui(pieces_on_background)
        self.update_idletasks()

        # single mode: just show the result - saving is done separately with the Save button
        if not is_batch:
            self.sidebar.set_save_enabled(True)
            return

        # batch mode: save the first image, then go through the rest
        try:
            save_image_as_png(self.save_location_path, self.loaded_image_path, pieces_on_background)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save the image:\n{e}")
            return

        # lock Run, Preview and the file menu while the batch runs and unlock them again when the batch ends
        self.sidebar.set_batch_running(True)
        self.action_menu.configure(state="disabled")
        try:
            self.run_batch(self.loaded_image_paths[1:])
        finally:
            self.sidebar.set_batch_running(False)
            self.action_menu.configure(state="normal")

    def run_action_extract(self):
        if not self.ensure_image_loaded():
            return

        image = ProjectSession.original_image.copy()
        height, width = image.shape[:2]

        mask = image_splitter.get_fragment_contours(image)

        # for the preview we thicken lines
        # big images are shrunk more on screen so they get a bigger kernel
        kernel_size = (5, 5) if max(height, width) > 1500 else (3, 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, kernel_size)
        preview_lines = cv2.dilate(mask.astype(np.uint8), kernel)

        image[preview_lines == 1] = [0, 0, 255]

        self.render_image_on_ui(image)

        self.sidebar.set_reconstruct_enabled(True)

    def run_action_reconstructing(self):
        pass

    def save_action(self, obj):
        """Handles manual save requests for the currently processed single image."""

        if ProjectSession.pieces_on_background is None:
            return

        if not self.ensure_save_location():
            return

        try:
            saved_path = save_image_as_png(self.save_location_path, self.loaded_image_path, obj)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save the image:\n{e}")
            return

        self.set_status(f"Image saved to: {saved_path}")

    def save_action_module_1(self):
        self.save_action(ProjectSession.pieces_on_background)

    def save_action_module_2(self):
        self.save_action(ProjectSession.reconstructed_image)

    def run_batch(self, paths: list[Path]):
        """
        Iterates over a queue of images to dynamically mask, fragment, and save them automatically.

        Each queued image generates its own fresh mask using the currently selected 
        method and parameters, ensuring accurate splitting across varying document 
        dimensions within the directory.

        Args:
            paths (list[Path]): A list of pathlib.Path objects pointing to the remaining images in the batch queue.
        """
        
        saved_count = 1  # the first image was already saved in run_action
        failed = []
        total = len(paths) + 1

        for index, path in enumerate(paths, start=2):
            self.set_status(f"Processing {index}/{total}: {path.name}", auto_hide=False)
            self.update()

            try:
                image = read_image(path)
                height, width = image.shape[:2]
                dynamic_params = self.sidebar.get_split_parameters()
                current_method = self.sidebar.split_opt_dropdown.get()
                mask = mask_generator.generate_mask(current_method, height, width, **dynamic_params)

                pieces_on_background = self.fragment_image(image, mask)
                save_image_as_png(self.save_location_path, path, pieces_on_background)
                saved_count += 1

                self.render_image_on_ui(pieces_on_background)
            except Exception as e:
                failed.append(f"{path.name}: {e}")

        summary = f"Saved {saved_count} of {total} images to: {self.save_location_path}"
        self.set_status(summary)

        if failed:
            messagebox.showwarning("Batch Finished With Errors", summary + "\n\nFailed:\n" + "\n".join(failed))
        else:
            messagebox.showinfo("Batch Finished", summary)

    def show_warning(self, message):
        """Displays a warning dialog to the user."""
        messagebox.showwarning("Time limit reached", message)