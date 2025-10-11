import html
import json
import urllib.request as urllib_request

from bs4 import BeautifulSoup

DEPARTMENT_CORRECTIONS = {"M&SS": "QSS", "WGST": "WGSS"}


def clean_department_code(department):
    department = html.unescape(department.strip()).upper()
    return DEPARTMENT_CORRECTIONS.get(department, department)


def int_or_none(string):
    return int(string) if string else None


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(",", ": "))


# def parse_number_and_subnumber(numbers_text):
#     numbers = numbers_text.split(".")
#     if len(numbers) == 2:
#         return (int(n) for n in numbers)
#     else:
#         assert len(numbers) == 1
#         return int(numbers[0]), None


def retrieve_soup(url, data=None, preprocess=lambda x: x):
    print(url)
    if data is not None:
        data = data.encode("utf-8")
    with urllib_request.urlopen(url, data=data) as response:
        return BeautifulSoup(preprocess(response.read().decode("utf-8")), "html.parser")


def extract_prerequisites(pre_requisites):
    """Process prerequisite string format (legacy function)"""
    result = pre_requisites

    result = result.replace("Pre-requisites:", "").strip()
    result = result.replace("Obtained Credit", "obtained_credit").strip()
    result = result.replace("Credits Submitted", "credits_submitted").strip()
    result = result.replace("&&", " && ").strip()
    result = result.replace("||", " || ").strip()

    return result
