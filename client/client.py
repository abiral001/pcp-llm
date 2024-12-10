import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.filedialog import asksaveasfilename
import requests
import csv
SERVER_IP = "PLACEHOLDER"

SERVER_URL = f"http://{SERVER_IP}:5000"

def fetch_departments():
    """
    Fetches the list of departments and their subject code prefixes from the server.
    """
    try:
        response = requests.get(f"{SERVER_URL}/get_departments")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch departments: {str(e)}")
        return []

def fetch_courses(department):
    """
    Fetches the list of courses for a specific department from the server.
    """
    try:
        payload = {"Department": department}
        response = requests.post(f"{SERVER_URL}/get_courses", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch courses: {str(e)}")
        return []

def populate_departments():
    """
    Populates the department dropdown dynamically with filtering only when clicked.
    """
    global departments_data

    departments_data = fetch_departments()
    all_departments = [d["Department"] for d in departments_data]

    def filter_departments(event):
        user_input = department_selector.get()
        filtered_departments = [d for d in all_departments if user_input.lower() in d.lower()]
        department_selector["values"] = filtered_departments

    # Bind the dropdown to filter when clicked
    department_selector.bind("<Button-1>", filter_departments)

def add_course_row():
    """
    Adds a new row to the completed courses table with a course name dropdown 
    that filters options only when the dropdown button is clicked.
    """
    global course_rows

    selected_department = department_selector.get()
    if not selected_department:
        messagebox.showerror("Error", "Please select a department before adding courses!")
        return

    courses_data = fetch_courses(selected_department)
    if not courses_data:
        messagebox.showerror("Error", "Failed to fetch courses for the selected department!")
        return

    row_number = len(course_rows) + 1

    # Initialize the row data
    row_data = {
        "S.No": tk.Label(course_table, text=row_number),
        "Course Name": ttk.Combobox(course_table, width=20),
        "Course Code": tk.Entry(course_table, width=15),
        "Credits": tk.Entry(course_table, width=8),
        "Semester": tk.Entry(course_table, width=10),
        "Remove": tk.Button(course_table, text="Remove", width=10)
    }

    # Populate the initial dropdown with all course names
    all_course_names = [course["Course Name"] for course in courses_data]

    # Function to filter the dropdown when clicked
    def populate_dropdown(event, row=row_data):
        user_input = row["Course Name"].get()
        filtered_courses = [course for course in all_course_names if user_input.lower() in course.lower()]
        row["Course Name"]["values"] = filtered_courses

    # Function to autofill course code when a course is selected
    def on_course_selected(event, row=row_data):
        selected_course_name = row["Course Name"].get()
        for course in courses_data:
            if course["Course Name"] == selected_course_name:
                row["Course Code"].delete(0, tk.END)
                row["Course Code"].insert(0, course["Course Code"])
                break

    # Function to remove the current row
    def remove_row():
        for widget in row_data.values():
            widget.grid_forget()
        course_rows.remove(row_data)
        update_row_numbers()

    # Bind events
    row_data["Course Name"].bind("<Button-1>", populate_dropdown)  # Populate dropdown only when clicked
    row_data["Course Name"].bind("<<ComboboxSelected>>", on_course_selected)  # Autofill code on selection
    row_data["Remove"].config(command=remove_row)

    # Place widgets in the table
    row_data["S.No"].grid(row=row_number, column=0, padx=5, pady=2)
    row_data["Course Name"].grid(row=row_number, column=1, padx=5, pady=2)
    row_data["Course Code"].grid(row=row_number, column=2, padx=5, pady=2)
    row_data["Credits"].grid(row=row_number, column=3, padx=5, pady=2)
    row_data["Semester"].grid(row=row_number, column=4, padx=5, pady=2)
    row_data["Remove"].grid(row=row_number, column=5, padx=5, pady=2)

    course_rows.append(row_data)

def update_row_numbers():
    """
    Updates the row numbers (S.No) after a row is removed.
    """
    for i, row in enumerate(course_rows):
        row["S.No"].config(text=i + 1)

def display_academic_plan(plan):
    """
    Displays the academic plan as a single table and adds an Export button.
    """
    for widget in results_frame.winfo_children():
        widget.destroy()

    plan_label = tk.Label(results_frame, text="Academic Plan", font=("Arial", 14, "bold"))
    plan_label.pack(pady=5)

    plan_table = ttk.Treeview(
        results_frame,
        columns=("S.No.", "Course Name", "Course Code", "Credits", "Semester"),
        show="headings",
        height=15
    )
    plan_table.heading("S.No.", text="S.No.")
    plan_table.heading("Course Name", text="Course Name")
    plan_table.heading("Course Code", text="Course Code")
    plan_table.heading("Credits", text="Credits")
    plan_table.heading("Semester", text="Semester")
    plan_table.column("S.No.", width=50, anchor="center")
    plan_table.column("Course Name", width=300, anchor="center")
    plan_table.column("Course Code", width=150, anchor="center")
    plan_table.column("Credits", width=100, anchor="center")
    plan_table.column("Semester", width=100, anchor="center")
    plan_table.pack(pady=10, fill=tk.X, expand=True)

    s_no = 1
    for semester, details in plan.items():
        for course in details["Courses"]:
            plan_table.insert(
                "", "end",
                values=(
                    s_no,
                    course["Course Name"],
                    course["Course Code"],
                    course["Credits"],
                    semester
                )
            )
            s_no += 1

    export_button = tk.Button(results_frame, text="Export to CSV", command=lambda: export_to_csv(plan), bg="lightblue")
    export_button.pack(pady=10)

def export_to_csv(plan):
    """
    Exports the course plan to a CSV file.
    """
    if not plan:
        messagebox.showwarning("No Data", "No course plan available to export!")
        return

    file_path = asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        title="Save Course Plan as CSV"
    )

    if not file_path:
        return

    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["S.No.", "Course Name", "Course Code", "Credits", "Semester"])

            s_no = 1
            for semester, details in plan.items():
                for course in details["Courses"]:
                    writer.writerow([
                        s_no,
                        course["Course Name"],
                        course["Course Code"],
                        course["Credits"],
                        semester
                    ])
                    s_no += 1

        messagebox.showinfo("Success", f"Course plan successfully exported to {file_path}!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export course plan: {str(e)}")

def submit_selection():
    """
    Handles the submission of the form and sends data to the server.
    """
    global course_rows

    selected_department = department_selector.get()
    total_credits = credits_entry.get()
    program_of_study = program_of_study_entry.get().strip()
    has_masters = masters_completed.get()

    if not selected_department or not total_credits.isdigit() or not program_of_study:
        messagebox.showwarning("Input Error", "Please complete all fields!")
        return

    completed_courses = []
    for row in course_rows:
        course = {
            "Course Name": row["Course Name"].get().strip(),
            "Course Code": row["Course Code"].get().strip(),
            "Credits": row["Credits"].get().strip(),
            "Semester": row["Semester"].get().strip(),
        }
        if not all(course.values()):
            messagebox.showwarning("Incomplete Row", "Please fill all fields in the completed courses table!")
            return
        completed_courses.append(course)

    payload = {
        "Department": selected_department,
        "Total Credits": int(total_credits),
        "Program of Study": program_of_study,
        "Masters Completed": has_masters,
        "Completed Courses": completed_courses,
    }

    try:
        response = requests.post(f"{SERVER_URL}/generate_subjects", json=payload)
        response.raise_for_status()
        data = response.json()
        display_academic_plan(data)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to submit data: {str(e)}")

# Initialize Tkinter
root = tk.Tk()
root.title("Personalized Course Planner with Large Language Model")
root.geometry("900x600")

departments_data = []

department_selector = ttk.Combobox(root, state="normal", width=40)
populate_departments()
tk.Label(root, text="Select a Department:", font=("Arial", 12)).pack(pady=5)
department_selector.pack(pady=5)

tk.Label(root, text="Enter Total Credits:", font=("Arial", 12)).pack(pady=5)
credits_entry = tk.Entry(root, width=30)
credits_entry.pack(pady=5)

tk.Label(root, text="Enter Program of Study:", font=("Arial", 12)).pack(pady=5)
program_of_study_entry = tk.Entry(root, width=40)
program_of_study_entry.pack(pady=5)

masters_completed = tk.BooleanVar()
tk.Label(root, text="Have you completed a Master's degree?", font=("Arial", 12)).pack(pady=5)
masters_checkbox = tk.Checkbutton(root, text="Yes", variable=masters_completed)
masters_checkbox.pack(pady=5)

tk.Label(root, text="Completed Courses:", font=("Arial", 14, "bold")).pack(pady=10)

course_table = tk.Frame(root)
course_table.pack()

headers = ["S.No", "Course Name", "Course Code", "Credits", "Semester"]
for col, header in enumerate(headers):
    tk.Label(course_table, text=header, font=("Arial", 10, "bold")).grid(row=0, column=col, padx=5, pady=5)

course_rows = []
add_button = tk.Button(root, text="+ Add Course", command=add_course_row, bg="lightgreen")
add_button.pack(pady=10)

submit_button = tk.Button(root, text="Submit", command=submit_selection, bg="lightblue")
submit_button.pack(pady=20)

results_frame = tk.Frame(root)
results_frame.pack(pady=20)

root.mainloop()
