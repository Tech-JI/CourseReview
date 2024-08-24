from bs4 import BeautifulSoup
from html.parser import HTMLParser
import json
import urllib.request as urllib_request

DEPARTMENT_CORRECTIONS = {
    "M&SS": "QSS",
    "WGST": "WGSS"
}

def clean_department_code(department):
    department = HTMLParser().unescape(department.strip()).upper()
    return (
        DEPARTMENT_CORRECTIONS.get(department, department)
    )

def int_or_none(string):
    return int(string) if string else None

def pretty_json(data):
    return json.dumps(
        data, sort_keys=True, indent=4, separators=(',', ': ')
    )

def parse_number_and_subnumber(numbers_text):
    numbers = numbers_text.split(".")
    if len(numbers) == 2:
        return (int(n) for n in numbers)
    else:
        assert len(numbers) == 1
        return int(numbers[0]), None

def retrieve_soup(url, data=None, preprocess=lambda x: x):
    with urllib_request.urlopen(url, data=data) as response:
        return BeautifulSoup(
            preprocess(response.read().decode('utf-8')), "html.parser"
        )
