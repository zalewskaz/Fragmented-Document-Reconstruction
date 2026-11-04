import customtkinter as ctk

class CTkSpinbox(ctk.CTkFrame):
    """
    A custom spinbox widget for CustomTkinter with increment and decrement arrows.

    This widget combines a standard text entry with 'up' and 'down' buttons 
    to easily adjust integer values within a specified range. It supports
    validation, manual entry, and executing a callback function on change.

    Args:
        master (Any): The parent widget to which this spinbox belongs.
        start_value (int, optional): The initial value displayed in the entry. Defaults to 2.
        step (int, optional): The amount by which the value changes when buttons are clicked. Defaults to 1.
        min_value (int, optional): The minimum allowed integer value. Defaults to 2.
        max_value (int, optional): The maximum allowed integer value. Defaults to 10.
        command (callable, optional): A callback function triggered whenever the value changes.
        **kwargs: Additional keyword arguments passed to the underlying CTkFrame.
    """
    
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
        """
        Executes the assigned callback function with the current entry value.
        """

        if self.command:
            self.command(self.entry.get())

    def _on_key_release(self, event):
        """
        Event handler for key release. Triggers the callback as the user types.

        Args:
            event (tk.Event): The Tkinter event object containing details about the keystroke.
        """

        self._trigger_command()

    def _validate_entry(self, event=None):
        """
        Validates the text entry upon pressing Enter or losing focus. 
        Clamps the value within the allowed min/max range or clears it if invalid.

        Args:
            event (tk.Event, optional): The Tkinter event object triggering the validation. Defaults to None.
        """

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
        """
        Safely retrieves the current integer value from the entry for arrow operations.

        Returns:
            int: The current integer value, or the default start value if the entry is empty or invalid.
        """

        if self.entry.get().strip() == "":
            return self.default_start
        try:
            return int(self.entry.get())
        except ValueError:
            return self.default_start

    def _increment(self):
        """
        Increases the current value by the defined step, up to the maximum value.
        """

        val = self._get_current_for_arrows()
        if self.entry.get().strip() != "":
            val += self.step
            
        if self.max_value is not None and val > self.max_value:
            val = self.max_value
        self.set(val)

    def _decrement(self):
        """
        Decreases the current value by the defined step, down to the minimum value.
        """
        
        val = self._get_current_for_arrows()
        if self.entry.get().strip() != "":
            val -= self.step
            
        if self.min_value is not None and val < self.min_value:
            val = self.min_value
        self.set(val)

    def get(self):
        """
        Retrieves the current integer value from the spinbox.

        Returns:
            int or None: The current value as an integer, or None if the entry is empty or invalid.
        """

        try:
            return int(self.entry.get())
        except ValueError:
            return None

    def set(self, value, trigger=True):
        """
        Sets a new integer value in the spinbox.

        Args:
            value (int): The new value to set. Will be clamped if it exceeds min_value or max_value.
            trigger (bool, optional): Whether to trigger the assigned command callback. Defaults to True.
        """

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
        """
        Disables the spinbox, clearing its entry and deactivating the arrow buttons.
        """

        self.btn_minus.configure(state="disabled")
        self.clear()
        self.entry.configure(state="disabled")
        self.btn_plus.configure(state="disabled")

    def unblock(self):
        """
        Enables the spinbox, restoring the arrow buttons and the entry field.
        """

        self.btn_minus.configure(state="enabled")
        self.btn_plus.configure(state="enabled")
        self.entry.configure(state="normal")
        val = self._get_current_for_arrows()
        self.set(val)

    def clear(self):
        """
        Clears the entry field completely, leaving it empty.
        """

        self.entry.delete(0, ctk.END)