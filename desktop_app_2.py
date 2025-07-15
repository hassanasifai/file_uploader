#!/usr/bin/env python3
"""
Folder Uploader Desktop Application
A modern GUI application for uploading folders using the folder_uploader.py script
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys
from pathlib import Path
import queue
import json
from datetime import datetime

def run_upload_mp(args, output_queue):
    """Multiprocessing upload runner (for parallel uploads) - must be top-level for Windows"""
    import subprocess, sys, os
    try:
        python_exec = sys.executable
        cmd = [
            python_exec, args['script_path'],
            "--login", args['username'],
            "--password", args['password'],
            "--source", args['source'],
            "--warped", "1" if args.get('warped', False) else "0",
            "--name_as_userdata", "1" if args.get('name_as_userdata', False) else "0",
            "--descriptor", str(args['descriptor']),
            "--origin", args['origin'],
            "--avatar", str(args['avatar']),
            "--list_id", args['list_id'],
            "--multi_face_policy", str(args['multi_face_policy']),
            "--basic_attr", "1",
            "--score_threshold", "0.0",
            "--list_linked", "1"
        ]
        folder_path = args['folder_path']
        output_queue.put(('output', f"Starting upload from: {folder_path}"))
        output_queue.put(('output', f"Command: {' '.join(cmd)}"))
        # On Linux, ensure script is executable
        if os.name == 'posix' and not os.access(args['script_path'], os.X_OK):
            try:
                os.chmod(args['script_path'], 0o755)
            except Exception:
                pass
        proc = subprocess.Popen(
            cmd,
            cwd=folder_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        if proc.stdout is not None:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    output_queue.put(('output', line.strip()))
        proc.wait()
        if proc.returncode == 0:
            output_queue.put(('status', 'Upload completed successfully!'))
        else:
            output_queue.put(('status', f'Upload failed with code {proc.returncode}'))
    except Exception as e:
        output_queue.put(('error', f'Error running upload: {str(e)}'))
    finally:
        output_queue.put(('finished', None))

class FolderUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gelecek Folder Uploader - Professional Upload Tool")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Set window icon/logo if possible
        try:
            from tkinter import PhotoImage
            self.logo_img = PhotoImage(file="image.png")
            self.root.iconphoto(True, self.logo_img)
        except Exception as e:
            self.logo_img = None

        # Configure style
        self.setup_styles()

        # Variables
        self.selected_folder = tk.StringVar()
        # Username and Password fields (replace Account ID)
        self.username = tk.StringVar(value="")
        self.password = tk.StringVar(value="")
        self.warped = tk.BooleanVar(value=False)
        self.descriptor = tk.StringVar(value="1")
        self.origin = tk.StringVar(value="http://127.0.0.1:5000")
        self.avatar = tk.StringVar(value="1")
        self.list_id = tk.StringVar(value="90936600-d44b-4717-9b33-d685faf00616")
        self.name_as_userdata = tk.BooleanVar(value=False)

        # Process management
        self.upload_process = None
        self.output_queue = queue.Queue()
        # Job management
        self.jobs = []  # Each job: {'process', 'queue', 'folder', 'list_id', 'status'}

        # Create GUI
        self.create_widgets()

        # Load settings
        self.load_settings()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure ttk styles for modern appearance"""
        style = ttk.Style()
        
        # Configure colors
        bg_color = "#2c3e50"
        fg_color = "#ecf0f1"
        accent_color = "#3498db"
        
        self.root.configure(bg=bg_color)
        
        # Configure button style
        style.configure('Modern.TButton',
                       background=accent_color,
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(10, 5))
        
        style.map('Modern.TButton',
                 background=[('active', '#2980b9'),
                            ('pressed', '#21618c')])
    
    def create_widgets(self):
        """Create and arrange all GUI widgets"""
        # Main container (no canvas, no blue background)
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Centered Logo and Title
        logo_title_frame = ttk.Frame(main_frame)
        logo_title_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        main_frame.columnconfigure(0, weight=1)
        logo_title_frame.columnconfigure(0, weight=1)
        logo_title_frame.columnconfigure(1, weight=1)
        # Prepare logo
        if self.logo_img:
            try:
                self.smaller_logo = self.logo_img.subsample(6, 6)
            except Exception:
                self.smaller_logo = self.logo_img
            logo_label = tk.Label(logo_title_frame, image=self.smaller_logo)
            logo_label.grid(row=0, column=0, sticky="e", padx=(0, 10))
        title_label = ttk.Label(logo_title_frame, text="Gelecek Folder Uploader", font=('Arial', 22, 'bold'))
        title_label.grid(row=0, column=1, sticky="w")
        logo_title_frame.grid_columnconfigure(0, weight=1)
        logo_title_frame.grid_columnconfigure(1, weight=1)

        # Folder selection section
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)

        ttk.Label(folder_frame, text="Select Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        folder_entry = ttk.Entry(folder_frame, textvariable=self.selected_folder, font=('Arial', 10), width=50)
        folder_entry.grid(row=0, column=1, sticky="we", padx=(0, 10))

        browse_btn = ttk.Button(folder_frame, text="Browse", command=self.browse_folder, style='Modern.TButton')
        browse_btn.grid(row=0, column=2, sticky=tk.W)

        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Upload Configuration", padding="10")
        config_frame.grid(row=2, column=0, columnspan=3, sticky="we", pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)

        # Create configuration fields
        self.create_config_fields(config_frame)

        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))

        self.upload_btn = ttk.Button(button_frame, text="Start Upload", command=self.start_upload, style='Modern.TButton')
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.new_upload_btn = ttk.Button(button_frame, text="New Upload", command=self.new_upload, style='Modern.TButton')
        self.new_upload_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(button_frame, text="Stop All", command=self.stop_upload, style='Modern.TButton', state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        save_btn = ttk.Button(button_frame, text="Save Settings", command=self.save_settings, style='Modern.TButton')
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = ttk.Button(button_frame, text="Clear Log", command=self.clear_log, style='Modern.TButton')
        clear_btn.pack(side=tk.LEFT)

        # Job list UI
        joblist_frame = ttk.LabelFrame(main_frame, text="Running Upload Jobs", padding="10")
        joblist_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        joblist_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=0)
        self.joblist_box = tk.Listbox(joblist_frame, height=5, font=('Arial', 10))
        self.joblist_box.grid(row=0, column=0, sticky="nsew")
        joblist_frame.rowconfigure(0, weight=1)
        # Stop selected job button
        self.stop_job_btn = ttk.Button(joblist_frame, text="Stop Selected Job", command=self.stop_selected_job, style='Modern.TButton')
        self.stop_job_btn.grid(row=1, column=0, sticky="ew", pady=(5,0))
        self.stop_job_btn.config(state=tk.DISABLED)
        self.joblist_box.bind('<<ListboxSelect>>', self.on_job_select)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, mode='indeterminate')
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky="we", pady=(10, 0))

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=('Arial', 10))
        status_label.grid(row=5, column=0, columnspan=3, pady=(5, 0))

        # Output log with proper scrolling
        log_frame = ttk.LabelFrame(main_frame, text="Upload Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)

        log_scrollbar = tk.Scrollbar(log_frame)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=('Courier', 9), yscrollcommand=log_scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar.config(command=self.log_text.yview)

        # Add welcome message
        self.log_message("=== Gelecek Folder Uploader Initialized ===")
        self.log_message("Select a folder and configure settings to begin upload.")
    
    def create_config_fields(self, parent):
        """Create configuration input fields (with Username/Password and List dropdown)"""
        import threading
        configs = [
            ("Username:", self.username),
            ("Password:", self.password, True),
            ("Descriptor:", self.descriptor),
            ("Origin URL:", self.origin),
            ("Avatar:", self.avatar),
        ]
        row = 0
        for item in configs:
            label = item[0]
            var = item[1]
            is_pw = len(item) > 2 and item[2]
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            entry = ttk.Entry(parent, textvariable=var, font=('Arial', 9), width=40)
            if is_pw:
                entry.config(show='*')
            entry.grid(row=row, column=1, sticky="we", pady=2)
            row += 1

        # List dropdown (fetch from API)
        self.list_options = []  # (list_id, user_data)
        self.list_id_var = tk.StringVar()
        ttk.Label(parent, text="List:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        self.list_dropdown = ttk.Combobox(parent, textvariable=self.list_id_var, state="readonly", width=37)
        self.list_dropdown.grid(row=row, column=1, sticky="we", pady=2)
        self.list_dropdown['values'] = ["Loading..."]
        self.list_dropdown.set("Loading...")
        row += 1

        def fetch_lists():
            import requests
            try:
                resp = requests.get("http://192.168.18.70:5000/6/lists", timeout=5)
                data = resp.json()
                lists = data.get("lists", [])
                self.list_options = [(item["list_id"], item["user_data"]) for item in lists]
                values = [f"{name} ({lid})" for lid, name in self.list_options]
                if not values:
                    values = ["No lists found"]
                self.list_dropdown['values'] = values
                # Set default to first list
                if self.list_options:
                    self.list_id_var.set(values[0])
                    self.list_id.set(self.list_options[0][0])
                else:
                    self.list_id_var.set("")
            except Exception as e:
                self.list_dropdown['values'] = ["Failed to load lists"]
                self.list_dropdown.set("Failed to load lists")
        # Run fetch in background
        threading.Thread(target=fetch_lists, daemon=True).start()

        def on_list_select(event):
            idx = self.list_dropdown.current()
            if 0 <= idx < len(self.list_options):
                self.list_id.set(self.list_options[idx][0])
        self.list_dropdown.bind("<<ComboboxSelected>>", on_list_select)

        # Multi Face Policy (default 1)
        self.multi_face_policy = tk.IntVar(value=1)
        ttk.Label(parent, text="Multi Face Policy:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        multi_face_policy_entry = ttk.Entry(parent, textvariable=self.multi_face_policy, font=('Arial', 9), width=40)
        multi_face_policy_entry.grid(row=row, column=1, sticky="we", pady=2)
        row += 1
        # Checkboxes
        checkbox_frame = ttk.Frame(parent)
        checkbox_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        warped_cb = ttk.Checkbutton(checkbox_frame, text="Warped", variable=self.warped)
        warped_cb.pack(side=tk.LEFT, padx=(0, 20))
        userdata_cb = ttk.Checkbutton(checkbox_frame, text="Name as User Data", variable=self.name_as_userdata)
        userdata_cb.pack(side=tk.LEFT)
    
    def browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="Select Folder to Upload")
        if folder:
            self.selected_folder.set(folder)
            self.log_message(f"Selected folder: {folder}")
    
    def start_upload(self):
        """Start a new upload job (dedicated button, always enabled)"""
        self._launch_upload_job()

    def new_upload(self):
        """Explicitly launch a new upload job for another list/folder"""
        self._launch_upload_job()

    def _launch_upload_job(self):
        import multiprocessing
        if not self.selected_folder.get():
            messagebox.showerror("Error", "Please select a folder first!")
            return
        if not os.path.exists(self.selected_folder.get()):
            messagebox.showerror("Error", "Selected folder does not exist!")
            return
        script_path = self.find_uploader_script()
        if not script_path:
            messagebox.showerror("Error", "folder_uploader.py not found!\nPlease ensure it's in the same directory as this application.")
            return
        # Use selected list_id from dropdown if available
        list_id_val = self.list_id.get()
        if hasattr(self, 'list_id_var') and self.list_id_var.get():
            idx = self.list_dropdown.current()
            if hasattr(self, 'list_options') and 0 <= idx < len(self.list_options):
                list_id_val = self.list_options[idx][0]
        args = dict(
            script_path=script_path,
            folder_path=self.selected_folder.get(),
            username=self.username.get(),
            password=self.password.get(),
            source=self.selected_folder.get(),
            descriptor=self.descriptor.get(),
            origin=self.origin.get(),
            avatar=self.avatar.get(),
            list_id=list_id_val,
            warped=self.warped.get(),
            name_as_userdata=self.name_as_userdata.get(),
            multi_face_policy=self.multi_face_policy.get(),
        )
        output_queue = multiprocessing.Queue()
        p = multiprocessing.Process(target=run_upload_mp, args=(args, output_queue))
        p.start()
        job = {
            'process': p,
            'queue': output_queue,
            'folder': args['folder_path'],
            'list_id': args['list_id'],
            'status': 'Uploading...'
        }
        self.jobs.append(job)
        self.update_joblist_ui()
        self.progress_bar.start()
        self.status_var.set(f"{len(self.jobs)} job(s) running...")
        self.stop_btn.config(state=tk.NORMAL)
        self.monitor_all_outputs()
    
    def find_uploader_script(self):
        """Find the folder_uploader.py script (cross-platform, production-ready)"""
        # Check current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, "folder_uploader.py")
        if os.path.isfile(script_path):
            if os.name == 'posix':
                # Ensure executable permission
                if not os.access(script_path, os.X_OK):
                    try:
                        os.chmod(script_path, 0o755)
                    except Exception:
                        pass
            return script_path

        # Check common locations
        common_paths = [
            os.path.join(current_dir, "folder_uploader.py"),
            os.path.join(current_dir, "..", "folder_uploader.py"),
            os.path.join(current_dir, "../folder_uploader.py"),
            "folder_uploader.py",
            "./folder_uploader.py",
            "../folder_uploader.py",
            "/var/lib/luna/current/extras/utils/folder_uploader.py",
        ]
        if os.name == 'posix':
            common_paths.append("/var/lib/luna/current/extras/utils/folder_uploader.py")

        for path in common_paths:
            if os.path.isfile(path):
                if os.name == 'posix' and not os.access(path, os.X_OK):
                    try:
                        os.chmod(path, 0o755)
                    except Exception:
                        pass
                return os.path.abspath(path)
        return None
    
    # REMOVED: def run_upload_mp(self, ...) - now handled by top-level run_upload_mp
    
    def monitor_all_outputs(self):
        """Monitor all running jobs' output and update GUI"""
        import queue as mpqueue
        still_running = False
        for job in self.jobs:
            q = job['queue']
            try:
                while True:
                    msg_type, msg = q.get_nowait()
                    if msg_type == 'output':
                        self.log_message(f"[{job['folder']}] {msg}")
                    elif msg_type == 'error':
                        self.log_message(f"ERROR [{job['folder']}]: {msg}")
                    elif msg_type == 'status':
                        job['status'] = msg
                        self.status_var.set(msg)
                        self.log_message(f"STATUS [{job['folder']}]: {msg}")
                    elif msg_type == 'finished':
                        job['status'] = 'Finished'
            except mpqueue.Empty:
                pass
            if job['process'].is_alive():
                still_running = True
        # Remove finished jobs
        self.jobs = [j for j in self.jobs if j['process'].is_alive() or j['status'] != 'Finished']
        self.update_joblist_ui()
        if still_running:
            self.status_var.set(f"{len([j for j in self.jobs if j['process'].is_alive()])} job(s) running...")
            self.root.after(200, self.monitor_all_outputs)
        else:
            self.progress_bar.stop()
            self.status_var.set("Ready")
            self.stop_btn.config(state=tk.DISABLED)
            self.log_message("=== All Upload Jobs Finished ===")
    
    def upload_finished(self):
        """Handle upload completion"""
        self.upload_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.upload_process = None
        
        if self.status_var.get() == "Upload completed successfully!":
            self.log_message("=== Upload Completed Successfully ===")
        else:
            self.log_message("=== Upload Process Finished ===")
    
    def stop_upload(self):
        """Stop all running upload jobs"""
        stopped = 0
        for job in self.jobs:
            if job['process'].is_alive():
                try:
                    job['process'].terminate()
                    job['status'] = 'Stopped'
                    stopped += 1
                except Exception:
                    pass
        if stopped:
            self.log_message(f"Stopped {stopped} running upload job(s)")
            self.status_var.set("Upload stopped")
        else:
            self.log_message("No running jobs to stop.")
        self.update_joblist_ui()

    def stop_selected_job(self):
        """Stop the selected job from the job list UI"""
        sel = self.joblist_box.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.jobs):
            return
        job = self.jobs[idx]
        if job['process'].is_alive():
            try:
                job['process'].terminate()
                job['status'] = 'Stopped'
                self.log_message(f"Stopped job for folder: {job['folder']} (List ID: {job['list_id']})")
            except Exception:
                self.log_message(f"Failed to stop job for folder: {job['folder']}")
        else:
            self.log_message(f"Job already finished: {job['folder']}")
        self.update_joblist_ui()

    def update_joblist_ui(self):
        """Update the job list UI with current jobs and statuses"""
        self.joblist_box.delete(0, tk.END)
        for i, job in enumerate(self.jobs):
            status = job['status']
            folder = os.path.basename(job['folder'])
            listid = job['list_id']
            running = 'RUNNING' if job['process'].is_alive() else status.upper()
            self.joblist_box.insert(tk.END, f"[{i+1}] {folder} | List: {listid} | {running}")
        # Enable/disable stop selected job button
        if self.joblist_box.size() > 0:
            self.stop_job_btn.config(state=tk.NORMAL)
        else:
            self.stop_job_btn.config(state=tk.DISABLED)

    def on_job_select(self, event):
        sel = self.joblist_box.curselection()
        if sel and len(self.jobs) > 0:
            self.stop_job_btn.config(state=tk.NORMAL)
        else:
            self.stop_job_btn.config(state=tk.DISABLED)
    
    def log_message(self, message):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_msg)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log text"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Log cleared")
    
    def save_settings(self):
        """Save current settings to file (with username/password)"""
        settings = {
            'username': self.username.get(),
            'password': self.password.get(),
            'descriptor': self.descriptor.get(),
            'origin': self.origin.get(),
            'avatar': self.avatar.get(),
            'list_id': self.list_id.get(),
            'warped': self.warped.get(),
            'name_as_userdata': self.name_as_userdata.get(),
            'multi_face_policy': self.multi_face_policy.get(),
        }
        try:
            with open('uploader_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            self.log_message("Settings saved successfully")
            messagebox.showinfo("Success", "Settings for Gelecek Folder Uploader saved successfully!")
        except Exception as e:
            self.log_message(f"Error saving settings: {str(e)}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def load_settings(self):
        """Load settings from file (with username/password)"""
        try:
            if os.path.exists('uploader_settings.json'):
                with open('uploader_settings.json', 'r') as f:
                    settings = json.load(f)
                self.username.set(settings.get('username', self.username.get()))
                self.password.set(settings.get('password', self.password.get()))
                self.descriptor.set(settings.get('descriptor', self.descriptor.get()))
                self.origin.set(settings.get('origin', self.origin.get()))
                self.avatar.set(settings.get('avatar', self.avatar.get()))
                self.list_id.set(settings.get('list_id', self.list_id.get()))
                self.warped.set(settings.get('warped', self.warped.get()))
                self.name_as_userdata.set(settings.get('name_as_userdata', self.name_as_userdata.get()))
                self.multi_face_policy.set(settings.get('multi_face_policy', 1))
                self.log_message("Settings for Gelecek Folder Uploader loaded successfully")
        except Exception as e:
            self.log_message(f"Could not load settings: {str(e)}")
    
    def on_closing(self):
        """Handle application closing"""
        if self.upload_process:
            if messagebox.askokcancel("Quit", "Upload is in progress. Stop upload and quit?"):
                self.stop_upload()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    import multiprocessing
    multiprocessing.freeze_support()  # For Windows compatibility
    root = tk.Tk()
    app = FolderUploaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
