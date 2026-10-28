from datetime import date, datetime


def parse_request_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%d/%m/%Y").date()


def parse_response_date(value: str) -> date:
    value = str(value).strip()
    if not value:
        raise ValueError("Date value is empty")
    return datetime.strptime(value, "%m/%d/%Y").date()


def parse_expiry_date(value: str) -> date:
    value = str(value).strip().upper()
    if not value:
        raise ValueError("Expiry value is empty")
    return datetime.strptime(value, "%d%b%Y").date()


def normalize_symbol(value: str) -> str:
    return str(value).strip().upper()

