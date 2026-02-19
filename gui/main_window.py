import tkinter as tk
from tkinter import Toplevel, Text, Button

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Main Window")

        # Create sidebar
        self.sidebar = tk.Frame(self.root)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Create Event Log Button
        self.event_log_button = Button(self.sidebar, text="Event Log", command=self.open_event_log)
        self.event_log_button.pack(pady=10)

        # Placeholder for other main window components
        # ...

    def open_event_log(self):
        event_log_dialog = Toplevel(self.root)
        event_log_dialog.title("Event Log")

        text_area = Text(event_log_dialog, wrap='word')
        text_area.pack(expand=True, fill='both')

        # Add event log content here (this could be updated or read from a log file)
        text_area.insert(tk.END, "Log entries go here...")


if __name__ == '__main__':
    root = tk.Tk()
    main_window = MainWindow(root)
    root.mainloop()