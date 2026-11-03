import customtkinter as ctk

class CTkSpinbox(ctk.CTkFrame):
    def __init__(self, master, start_value=2, step=1, min_value=2, max_value=10, command=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.step = step
        self.min_value = min_value
        self.max_value = max_value
        self.command = command
        self.default_start = start_value

        self.grid_columnconfigure((0, 2), weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Decrement button
        self.btn_minus = ctk.CTkButton(
            self, text="▼", width=28, height=28, 
            command=self._decrement
        )
        self.btn_minus.grid(row=0, column=0, padx=(3, 0), pady=3)

        # Main entry
        self.entry = ctk.CTkEntry(
            self, width=50, height=28, border_width=0, justify="center"
        )
        self.entry.grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        self.entry.insert(0, str(start_value))

        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Return>", self._validate_entry)
        self.entry.bind("<FocusOut>", self._validate_entry)

        # Increment button
        self.btn_plus = ctk.CTkButton(
            self, text="▲", width=28, height=28, 
            command=self._increment
        )
        self.btn_plus.grid(row=0, column=2, padx=(0, 3), pady=3)

    def _trigger_command(self):
        if self.command:
            self.command(self.entry.get())

    def _on_key_release(self, event):
        self._trigger_command()

    def _validate_entry(self, event=None):
        if self.entry.get().strip() == "":
            return
        try:
            val = int(self.entry.get())
            if self.min_value is not None and val < self.min_value:
                val = self.min_value
            elif self.max_value is not None and val > self.max_value:
                val = self.max_value
            self.set(val, trigger=False)
        except ValueError:
            self.clear()

    def _get_current_for_arrows(self):
        if self.entry.get().strip() == "":
            return self.default_start
        try:
            return int(self.entry.get())
        except ValueError:
            return self.default_start

    def _increment(self):
        val = self._get_current_for_arrows()
        if self.entry.get().strip() != "":
            val += self.step
            
        if self.max_value is not None and val > self.max_value:
            val = self.max_value
        self.set(val)

    def _decrement(self):
        val = self._get_current_for_arrows()
        if self.entry.get().strip() != "":
            val -= self.step
            
        if self.min_value is not None and val < self.min_value:
            val = self.min_value
        self.set(val)

    def get(self):
        try:
            return int(self.entry.get())
        except ValueError:
            return None

    def set(self, value, trigger=True):
        self.entry.delete(0, ctk.END)
        if self.min_value is not None and value < self.min_value:
            self.entry.insert(0, str(self.min_value))
        elif self.max_value is not None and value > self.max_value:
            self.entry.insert(0, str(self.max_value))
        else:
            self.entry.insert(0, str(value))
            
        if trigger:
            self._trigger_command()

    def block(self):
        self.btn_minus.configure(state="disabled")
        self.clear()
        self.btn_plus.configure(state="disabled")

    def unblock(self):
        self.btn_minus.configure(state="enabled")
        self.btn_plus.configure(state="enabled")
        val = self._get_current_for_arrows()
        self.set(val)

    def clear(self):
        self.entry.delete(0, ctk.END)