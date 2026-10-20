from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Appearance settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Window configuration & centering
        self.title("Fragmented Document Reconstruction")

        width, height = 1200, 750
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1000, 650)

        # State management
        self.loaded_image_path = None

        # Main grid setup
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  # Content area
        self.grid_columnconfigure(1, weight=0)  # Sidebar

        # Initialize interface components
        self.setup_system_menu()
        self.setup_content_area()
        self.setup_sidebar()

    def setup_system_menu(self):
        """Creates the native system menu bar."""
        self.menubar = tk.Menu(self)

        # --- MENU "FILE" ---
        self.file_menu = tk.Menu(self.menubar, tearoff=0)

        # Submenu: Source (2 choices)
        self.source_submenu = tk.Menu(self.file_menu, tearoff=0)
        self.source_submenu.add_command(
            label="Single Image File",
            command=lambda: self.load_data("Single Image File"),
        )
        self.source_submenu.add_command(
            label="Image Folder", command=lambda: self.load_data("Image Folder")
        )

        # Add Source submenu to File
        self.file_menu.add_cascade(label="Source", menu=self.source_submenu)
        self.file_menu.add_separator()

        # Save & Save As (Disabled by default)
        self.file_menu.add_command(
            label="Save", command=self.save_file, state=tk.DISABLED
        )
        self.file_menu.add_command(
            label="Save As...", command=self.save_file_as, state=tk.DISABLED
        )

        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit)

        # Add File menu to MenuBar
        self.menubar.add_cascade(label="File", menu=self.file_menu)

        # Apply MenuBar to Window
        self.config(menu=self.menubar)

    def setup_sidebar(self):
        """Creates the right sidebar with module navigation."""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=1, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(3, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Fragmented Docs",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_cutter = ctk.CTkButton(
            self.sidebar_frame,
            text="Module 1: Cutter",
            command=lambda: self.switch_view("Module 1: Cutter"),
        )
        self.btn_cutter.grid(row=1, column=0, padx=20, pady=10)

        self.btn_assembler = ctk.CTkButton(
            self.sidebar_frame,
            text="Module 2: Assembler",
            command=lambda: self.switch_view("Module 2: Assembler"),
        )
        self.btn_assembler.grid(row=2, column=0, padx=20, pady=10)

    def setup_content_area(self):
        """Creates the main workspace."""
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.welcome_label = ctk.CTkLabel(
            self.content_frame,
            text="Go to File -> Source to select your document file or folder.",
            font=ctk.CTkFont(size=16),
            justify="center",
        )
        self.welcome_label.grid(row=0, column=0)

    def switch_view(self, view_name: str):
        """Switches active module view."""
        self.welcome_label.configure(text=f"Active View: {view_name}")

    def load_data(self, source_type: str):
        """Handles opening files/folders with root/data default directory."""
        project_root = Path(__file__).resolve().parent.parent.parent
        data_dir = project_root / "data"

        # Ensure data directory exists so tkinter doesn't complain about invalid initialdir
        data_dir.mkdir(parents=True, exist_ok=True)

        if source_type == "Single Image File":
            file_path = filedialog.askopenfilename(
                initialdir=data_dir,
                filetypes=[
                    (
                        "Image / Document Files",
                        "*.png *.jpg *.jpeg *.bmp *.tif *.tiff",
                    ),
                    ("All Files", "*.*"),
                ],
            )
            if file_path:
                self.loaded_image_path = file_path
                self.welcome_label.configure(
                    text=f"Loaded Image:\n{file_path}"
                )
                self.enable_save_options()

        elif source_type == "Image Folder":
            folder_path = filedialog.askdirectory(initialdir=data_dir)
            if folder_path:
                self.loaded_image_path = folder_path
                self.welcome_label.configure(
                    text=f"Loaded Folder:\n{folder_path}"
                )
                self.enable_save_options()

    def enable_save_options(self):
        """Enables Save and Save As in File menu."""
        self.file_menu.entryconfig("Save", state=tk.NORMAL)
        self.file_menu.entryconfig("Save As...", state=tk.NORMAL)

    def save_file(self):
        """Save action handler."""
        messagebox.showinfo("Save", "Document saved successfully!")

    def save_file_as(self):
        """Save As action handler."""
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg"),
                ("TIFF Image", "*.tif *.tiff"),
            ],
        )
        if save_path:
            messagebox.showinfo(
                "Save As", f"Document saved as:\n{save_path}"
            )