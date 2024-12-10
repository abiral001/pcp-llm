import requests

BASE_URL = "https://uri.kuali.co/api/v1/catalog/courses/65269fc6daaf7e001cdeda4c"
COURSE_DETAILS_URL = "https://uri.kuali.co/api/v1/catalog/course/65269fc6daaf7e001cdeda4c"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Origin": "https://web.uri.edu",
    "DNT": "1",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Referer": "https://web.uri.edu/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

def fetch_all_courses():
    """Fetches all courses from the API."""
    response = requests.get(BASE_URL, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def fetch_course_details(pid):
    """Fetches detailed information for a specific course using its PID."""
    url = f"{COURSE_DETAILS_URL}/{pid}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_courses_by_department(department):
    """
    Fetches and filters courses dynamically based on the selected department.
    :param department: Department name to filter courses (e.g., 'Electrical Engineering').
    """
    all_courses = fetch_all_courses()

    # Filter courses based on the department description
    filtered_courses = [
        course for course in all_courses
        if course.get("subjectCode", {}).get("description") == department
    ]

    # Fetch detailed information for each filtered course
    detailed_courses = []
    for course in filtered_courses:
        pid = course.get("pid")
        if pid:
            course_details = fetch_course_details(pid)
            detailed_courses.append({
                "Course Name": course.get("title"),
                "Course Code": course.get("__catalogCourseId"),
                "Credits": course_details.get("credits"),
                "Semester": course_details.get("semester", "Unknown"),
            })

    return detailed_courses

def get_departments():
    """
    Extracts unique departments and their subject code prefixes from the API.
    :return: List of dictionaries with Department names and Prefixes.
    """
    all_courses = fetch_all_courses()
    departments = {}
    for course in all_courses:
        subject = course.get("subjectCode", {})
        department_name = subject.get("description")
        subject_code = subject.get("name")
        if department_name and subject_code:
            departments[department_name] = subject_code

    # Convert to list of dictionaries
    return [{"Department": name, "Prefix": prefix} for name, prefix in departments.items()]
