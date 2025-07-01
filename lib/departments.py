department_code_to_name = {
    "ART": "Art",
    "BUS": "Business",
    "CHEM": "Chemistry",
    "CHN": "Chinese",
    "CUL": "Culture",
    "ECE": "Electrical and Computer Engineering",
    "ENGL": "English",
    "ENGR": "Engineering",
    "GER": "German",
    "HIS": "History",
    "IE": "Industrial Engineering",
    "MATH": "Mathematics",
    "ME": "Mechanical Engineering",
    "MSE": "Materials Science and Engineering",
    "PHIL": "Philosophy",
    "PHYS": "Physics",
    "POL": "Political Science",
    "SOC": "Sociology",
    "STAT": "Statistics and Data Science",
    "TC": "Technical Communication",
    "VE": "[Graduate] Electrical and Computer Engineering",
    "VG": "[Graduate] Technical Communication",
    "VM": "[Graduate] Mechanical Engineering",
}


def get_department_name(department_code):
    return department_code_to_name.get(department_code)
