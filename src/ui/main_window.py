from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
import cv2  
from src.utils.io import get_valid_paths, read_image, InvalidImageInputError

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
        self.save_location_path = None
        self.current_image_display = None 

        self.grid_rowconfigure(0, weight=0)  
        self.grid_rowconfigure(1, weight=1)  
        self.grid_columnconfigure(0, weight=1)  
        self.grid_columnconfigure(1, weight=0)  

        self.setup_top_toolbar()
        self.setup_content_area()
        self.setup_sidebar()

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

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=1, column=1, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(1, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Fragmented Docs",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 15))

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
                        self.loaded_image_path = valid_paths[0]
                        opencv_image = read_image(self.loaded_image_path)
                        self.render_image_on_ui(opencv_image)

            elif choice == "Select Directory":
                folder_path = filedialog.askdirectory(initialdir=data_dir)
                if folder_path:
                    valid_paths = get_valid_paths(folder_path)
                    if valid_paths:
                        self.loaded_image_path = valid_paths[0]
                        opencv_image = read_image(self.loaded_image_path)
                        self.render_image_on_ui(opencv_image)
                        messagebox.showinfo("Folder Loaded", f"Loaded folder successfully. Found {len(valid_paths)} valid images.")

            elif choice == "Choose Save Location":
                save_path = filedialog.asksaveasfilename(
                    initialdir=data_dir,
                    defaultextension=".png",
                    filetypes=[
                        ("PNG Image", "*.png"),
                        ("JPEG Image", "*.jpg"),
                        ("TIFF Image", "*.tif *.tiff"),
                    ],
                )
                if save_path:
                    self.save_location_path = save_path

        except Exception as e:
            messagebox.showerror("Error", str(e))

        self.action_menu.set("File Actions...")

    def render_image_on_ui(self, cv_img):
        """Konwertuje macierz OpenCV (BGR) na format obsługiwany przez CustomTkinter (RGB -> Pillow -> CTkImage) i wyświetla."""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)


        max_width, max_height = 800, 550
        pil_image.thumbnail((max_width, max_height))

        self.current_image_display = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)

        self.display_label.configure(text="", image=self.current_image_display)