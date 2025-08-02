import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from constants import COLOR_TAUPE, COLOR_DARK

class ScheduledTasksPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.tasks = []
        self.tasks_listbox = None

    def build_panel(self):
        title = tk.Label(self, text="Scheduled Tasks", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        # Tasks list
        self.tasks_listbox = tk.Listbox(self, height=8)
        self.refresh_tasks_listbox()
        self.tasks_listbox.pack(anchor='nw', padx=20, pady=5)
        # Action buttons
        btn_frame = tk.Frame(self, bg=COLOR_TAUPE)
        btn_frame.pack(anchor='nw', padx=20, pady=5)
        ttk.Button(btn_frame, text="Add Task", command=self.add_task_dialog).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Remove Task", command=self.remove_task_dialog).pack(side='left', padx=2)

    def refresh_tasks_listbox(self):
        if self.tasks_listbox:
            self.tasks_listbox.delete(0, 'end')
            for task in self.tasks:
                self.tasks_listbox.insert('end', str(task))

    def add_task_dialog(self):
        task = simpledialog.askstring("Add Task", "Enter task description:", parent=self.parent)
        if task:
            self.tasks.append(task)
            self.refresh_tasks_listbox()
            print(f"[SCHEDULED TASKS PANEL] Added task: {task}")
            messagebox.showinfo("Add Task", f"Task added: {task}")

    def remove_task_dialog(self):
        idx = self.get_selected_task_index()
        if idx is None:
            messagebox.showinfo("Remove Task", "Select a task to remove.")
            return
        task = self.tasks[idx]
        confirm = messagebox.askyesno("Remove Task", f"Are you sure you want to remove the task: {task}?")
        if confirm:
            del self.tasks[idx]
            self.refresh_tasks_listbox()
            print(f"[SCHEDULED TASKS PANEL] Removed task: {task}")
            messagebox.showinfo("Remove Task", f"Task removed: {task}")

    def get_selected_task_index(self):
        if self.tasks_listbox:
            selection = self.tasks_listbox.curselection()
            if not selection:
                return None
            return selection[0]
        return None 