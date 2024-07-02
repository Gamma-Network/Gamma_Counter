import customtkinter as ctk
import sqlite3
import time
import psutil
import threading
import os
from tkinter import filedialog, messagebox

local_app_data = os.getenv('LOCALAPPDATA')
if not local_app_data:
    messagebox.showerror("Error", "Unable to retrieve local app data directory.")
    exit()

db_path = os.path.join(local_app_data, 'time_tracker.db')
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS time_tracking
             (id INTEGER PRIMARY KEY, program_name TEXT UNIQUE, total_duration REAL)''')
conn.commit()
tracked_program = None
start_time = None

def get_saved_total_duration(program_name):
    c.execute("SELECT total_duration FROM time_tracking WHERE program_name=?", (program_name,))
    result = c.fetchone()
    if result:
        return result[0]
    return 0.0

def track_program_usage():
    global tracked_program, start_time
    while True:
        try:
            if tracked_program:
                running_programs = [proc.name() for proc in psutil.process_iter(['name'])]
                if tracked_program['name'] in running_programs:
                    current_time = time.time()
                    elapsed_time = current_time - start_time
                    total_duration = get_saved_total_duration(tracked_program['name']) + elapsed_time
                    c.execute("UPDATE time_tracking SET total_duration=? WHERE program_name=?", 
                              (total_duration, tracked_program['name']))
                    conn.commit()
                    seconds_elapsed = int(total_duration)
                    elapsed_time_str = "{:0>2}:{:0>2}:{:0>2}".format(seconds_elapsed // 3600, (seconds_elapsed // 60) % 60, seconds_elapsed % 60)
                    countdown_label.configure(text=f"Countdown: {elapsed_time_str}")
                    countdown_label.pack()  
                    start_time = current_time
                    countdown_label.configure(text=f"Countdown: {elapsed_time_str}")
                    program_label.configure(text=f"Countdown Program: {tracked_program['name']}")
                    if not program_label.winfo_viewable():
                        program_label.pack()
                    if not countdown_label.winfo_viewable():
                        countdown_label.pack()
                else:
                    messagebox.showwarning("Warning", f"The program '{tracked_program['name']}' has ended or closed.")
                    tracked_program = None
                    countdown_label.configure(text="Countdown: --:--:--")
                    program_label.configure(text="Countdown Program: ")
                    select_button.configure(state="normal")
                    remove_button.configure(state="disabled")
                    if program_label.winfo_viewable():
                        program_label.pack_forget()
                    if countdown_label.winfo_viewable():
                        countdown_label.pack_forget()
        except Exception as e:
            print(f"Error tracking programs: {e}")
        time.sleep(1)


def select_program():
    global tracked_program, start_time
    if tracked_program:
        messagebox.showinfo("Info", "A program is already selected.")
        return
    file_path = filedialog.askopenfilename(filetypes=[("Executable files", "*.exe")])
    if file_path:
        program_name = os.path.basename(file_path)
        running_programs = [proc.name() for proc in psutil.process_iter(['name'])]
        if program_name not in running_programs:
            messagebox.showwarning("Warning", f"The program '{program_name}' is not currently running.")
            return
        tracked_program = {'name': program_name, 'path': file_path}
        start_time = time.time()
        print(f"Started tracking time for {program_name}")
        select_button.configure(state="disabled")
        remove_button.configure(state="normal")
        c.execute("INSERT OR IGNORE INTO time_tracking (program_name, total_duration) VALUES (?, ?)", (program_name, 0.0))
        conn.commit()


def stop_program():
    global tracked_program, start_time
    if not tracked_program:
        messagebox.showinfo("Info", "No program is currently selected.")
        return
    tracked_program = None
    countdown_label.configure(text="Countdown: --:--:--")
    program_label.configure(text="Countdown Program: ")
    print("Stopped tracking program.")
    select_button.configure(state="normal")
    remove_button.configure(state="disabled")

def view_countdowns():
    c.execute("SELECT * FROM time_tracking ORDER BY total_duration DESC")
    results = c.fetchall()
    if not results:
        messagebox.showinfo("Info", "No countdowns tracked yet.")
        return
    top = ctk.CTk()
    top.title("All Countdowns")
    top.geometry("400x300")
    top.resizable(False, False)
    for result in results:
        program_name = result[1]
        total_duration = result[2]
        seconds_elapsed = int(total_duration)
        duration_str = "{:0>2}:{:0>2}:{:0>2}".format(seconds_elapsed // 3600, (seconds_elapsed // 60) % 60, seconds_elapsed % 60)
        program_info_label = ctk.CTkLabel(top, text=f"{program_name} : {duration_str}")
        program_info_label.pack(pady=5)
    top.mainloop()

app = ctk.CTk()
app.title("Gamma Countdown")
app.geometry("300x300")
app.resizable(False, False)
select_button = ctk.CTkButton(app, text="Start Countdown", command=select_program)
select_button.pack(pady=10)
remove_button = ctk.CTkButton(app, text="Stop Countdown", command=stop_program, state="disabled")
remove_button.pack(pady=10)
view_button = ctk.CTkButton(app, text="View All Countdowns", command=view_countdowns)
view_button.pack(pady=10)
program_label = ctk.CTkLabel(app, text="Countdown Program: ")
program_label.pack()
countdown_label = ctk.CTkLabel(app, text="Countdown: --:--:--")
countdown_label.pack()
tracking_thread = threading.Thread(target=track_program_usage, daemon=True)
tracking_thread.start()
app.mainloop()
conn.close()
