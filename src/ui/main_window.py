from pathlib import Path
import queue
import threading
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
from src.utils.io import get_valid_paths, read_image, save_image_as_png, InvalidImageInputError
from ui.module_1_sidebar import SidebarFrame

# params
STATUS_HIDE_AFTER_MS = 5000
CHECK_MESSAGES_EVERY_MS = 50  # how often the UI thread checks for messages from the worker thread
STOPPING_MESSAGE_DELAY_MS = 300  # "Stopping..." is shown only if stopping takes longer than this
SELECT_SAVE_LOCATION = "Select Save Location"
CHANGE_SAVE_LOCATION = "Change Save Location"


class ProcessingStopped(Exception):
    """Raised in the worker thread when the user pressed Stop and there's no partial result worth keeping."""


def raise_if_stopped(stop_callback):
    """Raises ProcessingStopped if the user pressed Stop (stop_callback returns True)."""
    if stop_callback is not None and stop_callback():
        raise ProcessingStopped

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

        # messages from the worker thread to the UI thread, e.g. ("done", result) or ("warning", text);
        # the worker thread can't change the window itself, so it puts messages here
        # and the UI thread reads them every CHECK_MESSAGES_EVERY_MS in check_messages
        self.messages = queue.Queue()

        # set when the user presses Stop; the worker thread checks it and ends early
        self.stop_event = threading.Event()
        self.busy = False  # whether a computation is running in the worker thread

        self.grid_rowconfigure(0, weight=0)  
        self.grid_rowconfigure(1, weight=1)  
        self.grid_columnconfigure(0, weight=1)  
        self.grid_columnconfigure(1, weight=0, minsize=650)  

        self.setup_top_toolbar()
        self.setup_content_area()
        self.setup_status_bar()

        self.sidebar = SidebarFrame(master=self, cmd_preview_split=self.preview_split_action, cmd_run=self.run_action, cmd_save=self.save_action, cmd_stop=self.stop_action, warning_callback=self.show_warning, stop_callback=self.stop_event.is_set)
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

    def set_busy(self, busy: bool):
        """Locks the buttons and the file menu while the worker thread is running, and unlocks them when it ends."""
        self.busy = busy
        self.sidebar.set_busy(busy)
        self.action_menu.configure(state="disabled" if busy else "normal")

    def run_in_background(self, work, on_done, stopped_message: str = "Stopped."):
        """
        Runs a long computation in a worker thread, so the window doesn't freeze.

        The UI is locked until the work ends. `work` must not touch the UI - everything it needs
        from the sidebar has to be read before. When it ends, `on_done` is called in the UI thread
        with the value `work` returned; if `work` raised an exception, an error pop-up is shown instead.
        If `work` raised ProcessingStopped (the user pressed Stop), only `stopped_message` is shown in the status bar.

        Args:
            work (callable): Function without arguments doing the computations, run in the worker thread.
            on_done (callable): Function taking the result of `work`, run in the UI thread.
            stopped_message (str, optional): Status bar message shown when `work` was stopped.
        """
        self.stop_event.clear()  # a Stop pressed during an earlier computation mustn't stop this one
        self.set_busy(True)

        def worker():
            try:
                self.messages.put(("done", work()))
            except ProcessingStopped:
                self.messages.put(("stopped", None))
            except Exception as e:
                self.messages.put(("error", e))

        # daemon=True so that closing the window doesn't wait for the computation to end
        threading.Thread(target=worker, daemon=True).start()
        self.after(CHECK_MESSAGES_EVERY_MS, self.check_messages, on_done, stopped_message)

    def check_messages(self, on_done, stopped_message: str):
        """
        Handles the messages the worker thread put into the queue.

        Checks the queue again every CHECK_MESSAGES_EVERY_MS milliseconds until the work ends.
        """
        while not self.messages.empty():
            kind, value = self.messages.get()

            if kind == "warning":
                messagebox.showwarning("Time limit reached", value)
            elif kind == "status":
                self.set_status(value, auto_hide=False)
            elif kind == "image":
                self.render_image_on_ui(value)
            elif kind == "done":
                self.set_busy(False)
                # Stop was pressed, but the work ended before it noticed - don't leave "Stopping..." in the status bar
                if self.stop_event.is_set():
                    self.set_status("Finished before it could be stopped.")
                on_done(value)
                return
            elif kind == "stopped":
                # nothing to show - the screen keeps what it showed before
                self.set_busy(False)
                self.set_status(stopped_message)
                return
            elif kind == "error":
                self.set_busy(False)
                # Stop was pressed, but an error ended the work first - don't leave "Stopping..." in the status bar
                if self.stop_event.is_set():
                    self.set_status("Stopped.")
                messagebox.showerror("Error", str(value))
                return

        self.after(CHECK_MESSAGES_EVERY_MS, self.check_messages, on_done, stopped_message)

    def preview_split_action(self):
        """
        Generates and renders a visual preview of the calculated cut lines on the source image.

        The mask is generated in the worker thread, so the window doesn't freeze for long methods.
        """
        if not self.ensure_image_loaded():
            return

        # read everything from the UI before starting the worker thread
        image = ProjectSession.original_image.copy()
        height, width = image.shape[:2]
        dynamic_params = self.sidebar.get_split_parameters()
        current_method = self.sidebar.split_opt_dropdown.get()

        def work():
            mask = mask_generator.generate_mask(current_method, height, width, **dynamic_params)
            return mask, draw_preview_lines(image, mask)

        def on_done(result):
            ProjectSession.mask, preview = result
            self.render_image_on_ui(preview)
            # the screen now shows the preview instead of the result, so there's nothing to save until the next Run
            self.sidebar.set_save_enabled(False)

            # after Stop the mask has only the lines drawn so far - it can still be used in Run
            if self.stop_event.is_set():
                self.set_status("Stopped. The preview shows the lines drawn before stopping.")

        self.run_in_background(work, on_done)

    def fragment_image(self, image: np.ndarray, mask: np.ndarray, edge_pixel_option: str,
                       rotation_option: str, stop_callback=None) -> tuple[list[ImageFragment], np.ndarray]:
        """
        Executes the full fragmentation pipeline on a single image: cuts the image into pieces, rotates them (if such option is selected) and scatters them on a background.

        It doesn't read anything from the UI and doesn't change ProjectSession, so it can run in the worker thread.

        Args:
            image (np.ndarray): The original source image matrix.
            mask (np.ndarray): The binary cut mask.
            edge_pixel_option (str): The selected EdgePixelAttributionOption value.
            rotation_option (str): The selected RotationOption value.
            stop_callback (callable, optional): Function returning True if the user pressed Stop - checked between the steps.

        Returns:
            tuple[list[ImageFragment], np.ndarray]: The fragments and the finalized, composited image of the scattered fragments.

        Raises:
            ProcessingStopped: If the user pressed Stop.
        """

        height, width = image.shape[:2]

        # cut the image into pieces along the mask lines
        fragments_list = image_splitter.split_image(image, mask, edge_pixel_option)
        raise_if_stopped(stop_callback)

        # rotate pieces according to the selected dropdown option
        if rotation_option == RotationOption.ROTATION_RANDOM.value:
            fragments_list = fragment_rotation.rotate_fragments_randomly(fragments_list)
        elif rotation_option == RotationOption.ROTATION_90DEG.value:
            fragments_list = fragment_rotation.rotate_fragments_90deg(fragments_list)
        elif rotation_option == RotationOption.ROTATION_180DEG.value:
            fragments_list = fragment_rotation.rotate_fragments_180deg(fragments_list)
        raise_if_stopped(stop_callback)

        # scatter the pieces on a background that contrasts with the document
        bg_colour = background_arrange.pick_background_colour(image)
        pieces_on_background = background_arrange.arrange_on_background(height, width, fragments_list, bg_colour)

        return fragments_list, pieces_on_background

    def run_action(self):
        """
        Executes the fragmentation task based on the current UI parameters.

        In single-file mode, it renders the result to the screen, pending manual save.
        In batch mode, it triggers `run_batch` to process and save all the images automatically.
        In both modes the computations run in the worker thread, so the window doesn't freeze.
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

        # read everything from the UI before starting the worker thread
        image = ProjectSession.original_image.copy()
        height, width = image.shape[:2]
        mask = ProjectSession.mask  # the mask from Preview, or None if there was no preview
        dynamic_params = self.sidebar.get_split_parameters()
        current_method = self.sidebar.split_opt_dropdown.get()
        edge_pixel_option = self.sidebar.get_edge_pixel_option()
        rotation_option = self.sidebar.get_rotation_option()

        # single mode: compute in the worker thread and just show the result - saving is done separately with the Save button
        if not is_batch:
            # after Stop nothing is shown - the screen keeps the previous image
            stop_callback = self.stop_event.is_set

            def work():
                # generate a mask if it hasn't been generated already
                result_mask = mask
                if result_mask is None:
                    result_mask = mask_generator.generate_mask(current_method, height, width, **dynamic_params)
                    raise_if_stopped(stop_callback)
                fragments, pieces_on_background = self.fragment_image(image, result_mask, edge_pixel_option,
                                                                      rotation_option, stop_callback)
                raise_if_stopped(stop_callback)
                return result_mask, fragments, pieces_on_background

            def on_done(result):
                ProjectSession.mask, ProjectSession.fragments, ProjectSession.pieces_on_background = result
                self.render_image_on_ui(ProjectSession.pieces_on_background)
                self.sidebar.set_save_enabled(True)

            # Save is enabled only when a Run result is on the screen - after Stop it stays there
            if self.sidebar.save_enabled:
                stopped_message = "Stopped. The previous result is kept."
            else:
                stopped_message = "Stopped. Nothing was processed."

            self.run_in_background(work, on_done, stopped_message)
            return

        # batch mode: process and save all the images in the worker thread
        self.run_batch(image, mask, current_method, dynamic_params, edge_pixel_option, rotation_option)

    def stop_action(self):
        """
        Asks the worker thread to stop the current computation.

        The thread can't be stopped from outside - it checks stop_event itself and ends early,
        so it may take a moment until the computation really stops.
        """
        self.stop_event.set()
        self.sidebar.stop_button.configure(state="disabled")  # pressing it again wouldn't change anything

        # usually it stops in a fraction of a second - "Stopping..." is shown only if it takes longer,
        # so it doesn't just flash before "Stopped."
        self.after(STOPPING_MESSAGE_DELAY_MS, self.show_stopping_status)

    def show_stopping_status(self):
        """Shows "Stopping..." if the computation is still running some time after Stop was pressed."""
        if self.busy and self.stop_event.is_set():
            self.set_status("Stopping...", auto_hide=False)

    def save_action(self):
        """Handles manual save requests for the currently processed single image."""

        if ProjectSession.pieces_on_background is None:
            return

        if not self.ensure_save_location():
            return

        try:
            saved_path = save_image_as_png(self.save_location_path, self.loaded_image_path, ProjectSession.pieces_on_background)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save the image:\n{e}")
            return

        self.set_status(f"Image saved to: {saved_path}")

    def run_batch(self, first_image: np.ndarray, first_mask: np.ndarray | None, method: str, params: dict,
                  edge_pixel_option: str, rotation_option: str):
        """
        Masks, fragments and saves all the loaded images, one by one, in the worker thread.

        The first image is the one already loaded (and possibly previewed) - it uses the mask from Preview
        if there is one. Every other image is read from disk and gets its own fresh mask using the selected
        method and parameters, ensuring accurate splitting across varying document dimensions within the directory.
        A failed image doesn't stop the batch - it's listed in the summary at the end.
        After Stop, the images saved so far are kept and the image being processed is skipped.

        Args:
            first_image (np.ndarray): A copy of the first, already loaded image.
            first_mask (np.ndarray | None): The mask from Preview for the first image, or None if there was no preview.
            method (str): The selected splitting method.
            params (dict): The splitting parameters read from the sidebar.
            edge_pixel_option (str): The selected EdgePixelAttributionOption value.
            rotation_option (str): The selected RotationOption value.
        """
        # read everything from the UI before starting the worker thread
        paths = list(self.loaded_image_paths)
        save_dir = self.save_location_path
        total = len(paths)
        stop_callback = self.stop_event.is_set

        def work():
            saved_count = 0
            failed = []
            stopped = False
            mask_of_first = first_mask
            fragments = pieces_on_background = None

            for index, path in enumerate(paths, start=1):
                if stop_callback():
                    stopped = True
                    break

                self.messages.put(("status", f"Processing {index}/{total}: {path.name}"))

                try:
                    if index == 1:
                        image, mask = first_image, first_mask
                    else:
                        image, mask = read_image(path), None

                    if mask is None:
                        height, width = image.shape[:2]
                        mask = mask_generator.generate_mask(method, height, width, **params)
                        raise_if_stopped(stop_callback)
                    if index == 1:
                        mask_of_first = mask

                    image_fragments, image_result = self.fragment_image(image, mask, edge_pixel_option,
                                                                        rotation_option, stop_callback)
                    raise_if_stopped(stop_callback)
                    save_image_as_png(save_dir, path, image_result)
                    saved_count += 1
                    fragments, pieces_on_background = image_fragments, image_result

                    # show each result as soon as it's ready
                    self.messages.put(("image", pieces_on_background))
                except ProcessingStopped:
                    # the image being processed is skipped, the ones saved before are kept
                    stopped = True
                    break
                except Exception as e:
                    failed.append(f"{path.name}: {e}")

            return saved_count, failed, stopped, mask_of_first, fragments, pieces_on_background

        def on_done(result):
            saved_count, failed, stopped, mask_of_first, fragments, pieces_on_background = result
            ProjectSession.mask = mask_of_first
            ProjectSession.fragments = fragments
            ProjectSession.pieces_on_background = pieces_on_background

            summary = f"Saved {saved_count} of {total} images to: {save_dir}"
            if stopped:
                summary = "Stopped. " + summary
            self.set_status(summary)

            title = "Batch Stopped" if stopped else "Batch Finished"
            if failed:
                messagebox.showwarning(title + " With Errors", summary + "\n\nFailed:\n" + "\n".join(failed))
            else:
                messagebox.showinfo(title, summary)

        self.run_in_background(work, on_done)

    def show_warning(self, message):
        """
        Displays a warning dialog to the user.

        Called from the worker thread, it can't open the dialog itself,
        so it passes the message to the UI thread, which shows it in check_messages.
        """
        if threading.current_thread() is not threading.main_thread():
            self.messages.put(("warning", message))
            return
        messagebox.showwarning("Time limit reached", message)


def draw_preview_lines(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Draws the cut lines from the mask on the image in red, thickened so they're visible on screen.

    Args:
        image (np.ndarray): The source image; it's modified in place.
        mask (np.ndarray): The binary cut mask.

    Returns:
        np.ndarray: The image with the cut lines drawn on it.
    """
    height, width = image.shape[:2]

    # big images are shrunk more on screen so they get a bigger kernel
    kernel_size = (5, 5) if max(height, width) > 1500 else (3, 3)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, kernel_size)
    preview_lines = cv2.dilate(mask.astype(np.uint8), kernel)

    image[preview_lines == 1] = [0, 0, 255]
    return image
