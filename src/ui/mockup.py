"""Mockup GUI aplikacji Fragmented Document Reconstruction (CustomTkinter).
Uruchom:  ten kod i widoki zmieniaj klikajac w przelacznik w górnym pasku."""
import sys, textwrap
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
 
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
 
W, H = 600, 848  # A4 w px
S = W / 210     
CUTS = [[(80,0),(70,110),(95,190),(60,297)],
        [(150,0),(130,85),(150,210),(140,297)],
        [(0,95),(70,110),(130,85),(210,100)],
        [(0,200),(95,190),(150,210),(210,195)]]
 
def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try: return ImageFont.truetype(name, size)
    except OSError: return ImageFont.load_default()
 
SENTENCES = [
    "This is a sample document used to test the application.",
    "It contains a title, a few paragraphs of text and one picture.",
    "The text is written in a simple font so that it is easy to read.",
    "The document can be cut into many small pieces.",
    "The pieces can be mixed up, turned around and placed on a dark background.",
    "The application then tries to put all the pieces back together.",
    "It looks at the shape of each piece and at the text near its edges.",
    "When the work is done, the page should look the same as the original.",
    "The result can be saved as an image file.",
    "Thank you for reading this document.",
]
 
def make_document():
    """Przykładowy dokument A4 z prostą treścią po angielsku."""
    img = Image.new("L", (W, H), 250)
    d = ImageDraw.Draw(img)
    d.text((W/2, 70), "SAMPLE DOCUMENT", font=font(32, True), fill=30, anchor="mm")
    d.text((W/2, 110), "Introduction", font=font(16), fill=80, anchor="mm")
    def para(text, x, y, width):
        for line in textwrap.wrap(text, width):
            d.text((x, y), line, font=font(15), fill=45); y += 24
        return y
    y = para(" ".join(SENTENCES[0:2]), 50, 160, 62)
    d.rectangle((50, y + 14, 290, y + 182), fill=185)
    para(SENTENCES[2], 310, y + 14, 28)
    y = para(" ".join(SENTENCES[3:7]), 50, y + 210, 62)
    para(" ".join(SENTENCES[7:]), 50, y + 20, 62)
    d.text((W-50, H-40), "1", font=font(13), fill=110, anchor="rm")
    return img.convert("RGB")
 
def doc_with_cuts():
    img = make_document(); d = ImageDraw.Draw(img)
    for line in CUTS:
        d.line([(x*S, y*S) for x, y in line], fill=(229, 72, 77), width=3, joint="curve")
    return img
 
PIECES = [[(0,0),(80,0),(70,110),(0,95)], [(80,0),(150,0),(130,85),(70,110)],
          [(150,0),(210,0),(210,100),(130,85)], [(0,95),(70,110),(95,190),(0,200)],
          [(70,110),(130,85),(150,210),(95,190)], [(130,85),(210,100),(210,195),(150,210)],
          [(0,200),(95,190),(60,297),(0,297)], [(95,190),(150,210),(140,297),(60,297)],
          [(150,210),(210,195),(210,297),(140,297)]]
 
def pieces_on_background(borders=True, seed=7):
    """Dokument pocięty na kawałki, losowo obrócone i rozrzucone na czarnym tle."""
    import random
    rnd = random.Random(seed)
    doc = make_document().convert("RGBA")
    cuts = []
    for poly in PIECES:
        pts = [(x*S, y*S) for x, y in poly]
        mask = Image.new("L", doc.size, 0); ImageDraw.Draw(mask).polygon(pts, fill=255)
        piece = doc.copy(); piece.putalpha(mask)
        if borders:
            ImageDraw.Draw(piece).line(pts + [pts[0]], fill=(229, 72, 77, 255), width=4)
        piece = piece.crop(mask.getbbox())
        cuts.append(piece.rotate(rnd.uniform(0, 360), expand=True, resample=Image.BICUBIC))
    rnd.shuffle(cuts)
    cols, rows, cell = 3, 3, 420
    bg = Image.new("RGBA", (cols*cell, rows*cell), (0, 0, 0, 255))
    for i, p in enumerate(cuts):
        cx = (i % cols) * cell + cell // 2 + rnd.randint(-15, 15)
        cy = (i // cols) * cell + cell // 2 + rnd.randint(-15, 15)
        x = min(max(cx - p.width // 2, 20), bg.width - p.width - 20)
        y = min(max(cy - p.height // 2, 20), bg.height - p.height - 20)
        bg.alpha_composite(p, (x, y))
    return bg.convert("RGB")
 
class App(ctk.CTk):
    def __init__(self, screen="cut"):
        super().__init__()
        self.title("Fragmented Document Reconstruction")
        self.geometry("1280x760")
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
 
        top = ctk.CTkFrame(self, corner_radius=0, fg_color="#1f1f1f")
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        menu = ctk.CTkOptionMenu(top, values=["Select file…", "Select directory…",
                                              "Choose save location…"], width=230)
        menu.set("File Actions…"); menu.pack(side="left", padx=20, pady=14)
 
        self.seg = ctk.CTkSegmentedButton(top, values=["Module 1: Cutter", "Module 2: Assembler"],
                                          command=self.on_module_change)
        self.seg.pack(side="left", padx=8)
 
        self.view = None; self.side = None
        self.show(screen)
 
    def on_module_change(self, value):
        self.show("cut" if value == "Module 1: Cutter" else "assemble")
 
    def show(self, screen):
        self.seg.set("Module 1: Cutter" if screen == "cut" else "Module 2: Assembler")
        for w in (self.view, self.side):      
            if w is not None: w.destroy()
        self.build_view(screen)
        self.build_side(screen)
 
    def build_view(self, screen):
        self.view = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self.view.grid(row=1, column=0, sticky="nsew")
        pil = doc_with_cuts() if screen == "cut" else pieces_on_background()
        h = 600
        self.img = ctk.CTkImage(pil, size=(int(h * pil.width / pil.height), h))
        ctk.CTkLabel(self.view, image=self.img, text="").place(relx=.5, rely=.5, anchor="center")
 
    def build_side(self, screen):
        side = self.side = ctk.CTkFrame(self, corner_radius=0, width=420, fg_color="#242424")
        side.grid(row=1, column=1, sticky="ns"); side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(side, text="Fragmented Docs", font=ctk.CTkFont(size=24, weight="bold")
                     ).grid(row=0, column=0, pady=(40, 24))
        box = ctk.CTkFrame(side, fg_color="#2b2b2b")
        box.grid(row=1, column=0, sticky="ew", padx=28)
        box.grid_columnconfigure(1, weight=1)
 
        if screen == "cut":
            ctk.CTkLabel(box, text="Cutting parameters", font=ctk.CTkFont(size=16, weight="bold")
                         ).grid(row=0, column=0, columnspan=2, pady=(18, 14))
            self.row(box, 1, "Splitting method:", ctk.CTkOptionMenu(box, values=["Irregular pieces"]))
            e = ctk.CTkEntry(box); e.insert(0, "9"); self.row(box, 2, "Number of pieces:", e)
            self.buttons(box, 3, "Reset", "Set")
            ctk.CTkButton(side, text="Preview split", width=200, height=36
                          ).grid(row=2, column=0, pady=(28, 10))
            ctk.CTkButton(side, text="Run", width=200, height=36).grid(row=3, column=0)
        else:
            ctk.CTkLabel(box, text="Assembly parameters", font=ctk.CTkFont(size=16, weight="bold")
                         ).grid(row=0, column=0, columnspan=2, pady=(18, 14))
            self.row(box, 1, "Match pieces by:", ctk.CTkOptionMenu(box, values=["Shape and content"]))
            self.buttons(box, 2, "Reset", "Set")
            ctk.CTkButton(side, text="Assemble", width=200, height=36
                          ).grid(row=2, column=0, pady=(28, 10))
            ctk.CTkButton(side, text="Save", width=200, height=36).grid(row=3, column=0)
 
    def row(self, box, r, label, widget):
        ctk.CTkLabel(box, text=label, anchor="w").grid(row=r, column=0, sticky="w", padx=(18, 12), pady=8)
        widget.grid(row=r, column=1, sticky="ew", padx=(0, 18), pady=8)
 
    def buttons(self, box, r, a, b):
        f = ctk.CTkFrame(box, fg_color="transparent")
        f.grid(row=r, column=0, columnspan=2, sticky="ew", padx=18, pady=(14, 18))
        f.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(f, text=a).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(f, text=b).grid(row=0, column=1, padx=(8, 0), sticky="ew")
 
if __name__ == "__main__":
    screen = sys.argv[1] if len(sys.argv) > 1 else "cut"
    app = App(screen)
    if "--shot" in sys.argv:
        from PIL import ImageGrab
        def shot():
            app.update()
            x, y = app.winfo_rootx(), app.winfo_rooty()
            ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())
                           ).save(f"screen_{screen}.png"); app.destroy()
        app.after(1500, shot)
    app.mainloop()