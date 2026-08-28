from datetime import datetime


def get_current_term():
    now = datetime.now()
    year = str(now.year)[2:]  # Get last 2 digits of year
    month = now.month

    if 2 <= month <= 4:
        term = "SP"  # Spring
    elif 5 <= month <= 8:
        term = "SU"  # Summer
    else:
        term = "FA"  # Fall

    return f"{year}{term}"


CURRENT_TERM = get_current_term()
# CURRENT_TERM = os.environ["CURRENT_TERM"]  # e.g. 16S
SUPPORT_EMAIL = "support@layuplist.com"
REC_UPVOTE_REQ = 2
