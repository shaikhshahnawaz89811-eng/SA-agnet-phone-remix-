import tkinter as tk
from core.git_ops import set_remote

class Menu:
    def __init__(self, root):
        self.root = root
        self.root.title("SA Agent Menu")
        self.github_settings_menu = tk.Menu(self.root)
        self.github_settings_menu.add_command(label="Set/Update Remote URL", command=self.set_remote_url)

    def set_remote_url(self):
        remote_url = input("Enter remote URL: ")
        project_dir = input("Enter project directory: ")
        ok, message = set_remote(project_dir, remote_url)
        if ok:
            print("Remote URL set successfully.")
        else:
            print("Error setting remote URL:", message)

    def display_menu(self):
        self.root.config(menu=self.github_settings_menu)
        self.root.mainloop()

