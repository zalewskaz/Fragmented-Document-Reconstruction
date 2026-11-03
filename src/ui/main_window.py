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
from models import SplittingMethod, ProjectSession, ImageFragment
from src.utils.io import get_valid_paths, read_image, save_image_as_png, InvalidImageInputError
from ui.module_1_sidebar import SidebarFrame

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class MainWindow(ctk.CTk):

    def __init__(self):
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
        self.grid_columnconfigure(1, weight=0)  

        self.setup_top_toolbar()
        self.setup_content_area()

        self.sidebar = SidebarFrame(master=self, cmd_preview_split=self.preview_split_action, cmd_run=self.run_action)
        self.sidebar.grid(row=1, column=1, sticky="nsew")

    def setup_top_toolbar(self):
        self.toolbar_frame = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("#2b2b2b", "#1f1f1f"))
        self.toolbar_frame.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.action_menu = ctk.CTkOptionMenu(
            self.toolbar_frame,
            values=[
                "Select File",
                "Select Directory",
                "Choose Save Location"
            ],
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

    def switch_view(self, view_name: str):
        pass

    def handle_menu_action(self, choice: str):
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
                        self.render_image_on_ui(opencv_image)
                        messagebox.showinfo("Folder Loaded", f"Loaded folder successfully. Found {len(valid_paths)} valid images.")

            elif choice == "Choose Save Location":
                self.choose_save_location()

        except Exception as e:
            messagebox.showerror("Error", str(e))

        self.action_menu.set("File Actions...")

    def choose_save_location(self) -> bool:
        """Lets the user pick a folder to save results in. Returns False if they closed the window without choosing."""
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        save_path = filedialog.askdirectory(
            initialdir=data_dir,
            title="Choose Save Directory",
            mustexist=True,
        )

        if save_path:
            self.save_location_path = Path(save_path)
            return True
        return False

    def ensure_image_loaded(self) -> bool:
        """Checks if there's an image to work on - if not, tells the user to load one first."""
        if ProjectSession.original_image is None:
            messagebox.showwarning(
                "No Image Loaded",
                "Please load an image first using File Actions → Select File / Select Directory.",
            )
            return False
        return True

    def ensure_save_location(self) -> bool:
        """If no save folder was chosen yet, asks the user to pick one. Returns False if they decide not to."""
        if self.save_location_path is not None:
            return True

        wants_to_choose = messagebox.askyesno(
            "No Save Location",
            "No save location has been selected. Do you want to choose one now?",
        )
        if not wants_to_choose:
            return False

        return self.choose_save_location()

    def render_image_on_ui(self, cv_img):
        """Converts an OpenCV matrix (BGR) into a format supported by CustomTkinter (RGB -> Pillow -> CTkImage) and displays it."""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)


        max_width, max_height = 800, 550
        pil_image.thumbnail((max_width, max_height))

        self.current_image_display = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)

        self.display_label.configure(text="", image=self.current_image_display)

    def preview_split_action(self):
        if not self.ensure_image_loaded():
            return

        image = ProjectSession.original_image.copy()
        height, width = image.shape[:2]
        dynamic_params = self.sidebar.get_split_parameters()

        ProjectSession.mask = mask_generator.generate_mask(ProjectSession.splitting_method, height, width, **dynamic_params)

        image[ProjectSession.mask == 1] = [0, 0, 255]

        self.render_image_on_ui(image)

    def fragment_image(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Cuts the image into pieces, rotates them (if the checkbox is on) and scatters them on a background."""
        height, width = image.shape[:2]

        # cut the image into pieces along the mask lines
        fragments_list = image_splitter.split_image(image, mask)

        # give every piece its own random rotation, if the user ticked the checkbox
        if self.sidebar.get_rotate_pieces():
            fragments_list = fragment_rotation.rotate_fragments_randomly(fragments_list)

        ProjectSession.fragments = fragments_list

        # scatter the pieces on a background that contrasts with the document
        bg_colour = background_arrange.pick_background_colour(image)
        pieces_on_background = background_arrange.arrange_on_background(height, width, fragments_list, bg_colour)
        ProjectSession.pieces_on_background = pieces_on_background

        return pieces_on_background

    def run_action(self):
        if not self.ensure_image_loaded():
            return

        image = ProjectSession.original_image.copy()
        height, width = image.shape[:2]

        # generate a mask if it hasn't been generated already
        if ProjectSession.mask is None:
            dynamic_params = self.sidebar.get_split_parameters()
            ProjectSession.mask = mask_generator.generate_mask(ProjectSession.splitting_method, height, width, **dynamic_params)

        pieces_on_background = self.fragment_image(image, ProjectSession.mask)

        # show the result right away - update_idletasks() makes sure it's drawn before any pop-up appears
        self.render_image_on_ui(pieces_on_background)
        self.update_idletasks()

        # we only ask where to save after the user has seen what came out
        if not self.ensure_save_location():
            return

        # save the result in the chosen folder
        try:
            saved_path = save_image_as_png(self.save_location_path, self.loaded_image_path, pieces_on_background)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save the image:\n{e}")
            return

        remaining_paths = self.loaded_image_paths[1:]
        if not remaining_paths:
            messagebox.showinfo("Image Saved", f"The fragmented image has been saved to:\n{saved_path}")
            return

        self.run_batch(remaining_paths)

    def run_batch(self, paths: list[Path]):
        """
        Batch mode - goes through the rest of the images in the folder using the same settings.

        The first image is already done at this point (using the mask from the preview). Every other
        image gets a fresh mask made with the same method and parameters, because the images
        can have different sizes, so one mask wouldn't fit them all.
        """
        saved_count = 1  # the first image was already saved in run_action
        failed = []
        total = len(paths) + 1

        for index, path in enumerate(paths, start=2):
            self.title(f"Fragmented Document Reconstruction — processing {index}/{total}: {path.name}")
            self.update()

            try:
                image = read_image(path)
                height, width = image.shape[:2]
                dynamic_params = self.sidebar.get_split_parameters()
                mask = mask_generator.generate_mask(ProjectSession.splitting_method, height, width, **dynamic_params)

                pieces_on_background = self.fragment_image(image, mask)
                save_image_as_png(self.save_location_path, path, pieces_on_background)
                saved_count += 1

                self.render_image_on_ui(pieces_on_background)
            except Exception as e:
                failed.append(f"{path.name}: {e}")

        self.title("Fragmented Document Reconstruction")

        summary = f"Saved {saved_count} of {total} images to:\n{self.save_location_path}"
        if failed:
            messagebox.showwarning("Batch Finished With Errors", summary + "\n\nFailed:\n" + "\n".join(failed))
        else:
            messagebox.showinfo("Batch Finished", summary)
