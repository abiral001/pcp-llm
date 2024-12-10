from flask import Flask, request, jsonify
from modules.course_scraper import get_departments, get_courses_by_department
import requests
import json

app = Flask(__name__)

# Enable Flask's hot reloading
app.config["DEBUG"] = True

# Ollama API URL
OLLAMA_URL = "http://localhost:11434/api/chat"

# Initialize conversation history
conversation_history = [{"role": "system", "content": "You are a helpful academic advisor."}]

@app.route("/get_departments", methods=["GET"])
def get_departments_api():
    """
    Returns a list of available departments and their subject code prefixes.
    """
    try:
        departments = get_departments()
        return jsonify(departments)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/get_courses", methods=["POST"])
def get_courses_api():
    """
    Fetches and returns courses dynamically based on the selected department.
    Expects a JSON body with a "Department" key.
    """
    try:
        data = request.get_json()
        department = data.get("Department")
        if not department:
            return jsonify({"error": "Department is required"}), 400

        courses = get_courses_by_department(department)
        return jsonify(courses)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/generate_subjects", methods=["POST"])
def generate_subjects():
    """
    Generates subject suggestions using the Ollama model based on client input.
    """
    global conversation_history

    try:
        # Parse input JSON
        data = request.get_json()
        department = data.get("Department")
        program_of_study = data.get("Program of Study")
        masters_completed = data.get("Masters Completed", False)
        completed_courses = data.get("Completed Courses")
        completed_credits = sum(int(course["Credits"]) for course in completed_courses)
        ms_needed = not masters_completed and completed_credits < 30
        ms_credits_required = 30 - completed_credits if ms_needed else 0

        # Step 1: Send Initial Rules and Context
        initial_rules = """
        Rules:
        - Minimum of 72 credits in engineering, mathematics, and/or science courses.
        - The M. S. degree may count for up to 30 of the 72 credits required for the Ph. D.
        - Minimum of 18 credits, beyond the first 30 credits, in formal graduate engineering, 
        mathematics, and/or science courses. 
        - Up to three credits of special problems (ELE 591 and/or ELE 691), sometimes called 
        “independent study,” may be counted toward this requirement. 
        - Maximum of nine credits of special problems (ELE 591 and/or ELE 691) and special topics 
        (ELE 594 and/or ELE 694) may be counted toward this requirement. Department seminar (ELE 601 and ELE 602) may not be counted
        toward this requirement.
        - At least 18, but no more than 24, credits of dissertation (ELE 699). Additional ELE 699 credits may be completed for no program credit.
        - All full-time graduate students (M. S. or Ph. D.) are required to enroll in ELE 601 every semester the course offered. (It is offered only on Fall Semesters)
        - Minimum of two credits of departmental seminar (ELE 601 and ELE 602). These credits may not be counted toward the 42 credits required beyond the first 30 credits (or the M. S. degree).

        If a student has not completed M.S. there are more rules for the initial 30 credits: 
        - Complete a minimum of 30 credits, which include engineering mathematics and/or science courses. 
        - At least 16 credits must be from formal graduate electrical engineering (ELE) courses, excluding ELE 601 and ELE 602 (departmental seminars).
        - The Course Restrictions are: 
            - A maximum of 12 credits can be taken from senior undergraduate (400-level) courses in engineering, mathematics and/or science.
            - Up to three credits can be from special problems or independent study courses (ELE 591/592/691/692).
            - All full-time graduate students are required to enroll in the departmental seminar ELE 601 every semester it is offered.
        - Can pick 6-9 credits of thesis research (ELE 599), where six credits are standard. More than six credits require approval from your thesis committee and the Graduate Director/Department Chair.
        
        For students that have not yet completed their M.S. degree, the courses they pick should comprise of both the M.S. and Ph.D. requirements. 
        For students that have completed M.S. degree, only 42 credits need to be planned. 
        Only 8 credits of Doctoral Dissertation can be taken per semester. 
        Only courses of 500 level or higher can be taken.
        Each seminar is 1 credit. 
        Students must have Doctoral Dissertation credits in their plan every semester even during their masters requirements.  
        """
        conversation_history.append({"role": "assistant", "content": initial_rules})
        # Step 2: Provide User-Specific Details
        user_details = f""" This is the detail of the student: 
        - Program of Study: {program_of_study}
        - Department: {department}
        - Total Credits Completed: {completed_credits}
        - Master's Degree Completed: {"Yes" if masters_completed else "No"}
        - Credits Remaining for MS: {ms_credits_required if ms_needed else 0}
        - Completed Courses: {json.dumps(completed_courses, indent=2)}
        """
        conversation_history.append({"role": "user", "content": user_details})

        # Step 3: Request Academic Plan
        prompt_request = """
        Based on the provided details, generate a structured academic plan in JSON format:
        {{
            "Semester 1": {{
                "Total Credits": integer,
                "Courses": [
                    {{
                        "Course Name": string,
                        "Course Code": string,
                        "Credits": integer
                    }}
                ]
            }},
            "Semester 2": {{
                "Total Credits": integer,
                "Courses": [
                    {{
                        "Course Name": string,
                        "Course Code": string,
                        "Credits": integer
                    }}
                ]
            }},
        }}
        - Don't add any comments. Just provide the full 72 credit plan for all semesters. 
        """
        conversation_history.append({"role": "user", "content": prompt_request})
        # print(conversation_history)
        # Send the request to Ollama API with streaming enabled
        response = requests.post(
            OLLAMA_URL,
            json={"model": "llama3.3", "messages": conversation_history},
            stream=True,
            headers={"Content-Type": "application/json"}
        )
        
        # Collect and consolidate the streamed response
        full_response = ""
        if response.status_code == 200:
            for chunk in response.iter_lines():
                if chunk:
                    data = json.loads(chunk.decode("utf-8"))
                    message_content = data.get("message", {}).get("content", "")
                    full_response += message_content
                    if data.get("done", False):
                        break
        else:
            return jsonify({"error": "Failed to connect to Ollama API"}), response.status_code

        # Add assistant response to conversation history
        # conversation_history.append({"role": "assistant", "content": full_response})
        # Extract and validate the JSON part
        try:
            json_start = full_response.find("{")
            json_end = full_response.rfind("}")
            json_part = full_response[json_start:json_end + 1]
            json_response = json.loads(json_part)
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            print("Raw Output:", full_response)
            return jsonify({"error": "Invalid JSON format in Ollama response"}), 500

        return jsonify(json_response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Enable hot reloading
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
