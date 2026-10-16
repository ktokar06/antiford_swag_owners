"""Справочник префиксов номеров (первые 3 цифры) — общий для ETL, скоринга и API."""

CITY_CODES = {"842": "Регион 842", "499": "Москва 499", "892": "Регион 892"}
OPERATOR_GROUPS = {
    "alpha": {"025", "026", "027"},
    "barbetta": {"899", "810", "834"},
    "bellka": {"210", "214", "200"},
}
OPERATOR_NAMES = {
    "025": "Альфа-025", "026": "Альфа-026", "027": "Альфа-027",
    "899": "Барбетта-899", "810": "Барбетта-810", "834": "Барбетта-834",
    "210": "Bell-ka-210", "214": "Bell-ka-214", "200": "Bell-ka-200",
}
MOBILE_CODES = set().union(*OPERATOR_GROUPS.values())
HOME_CODES = set(CITY_CODES) | MOBILE_CODES

HOME_COUNTRY = "RU"
UNKNOWN_COUNTRY = "ZZ"


def prefix(number: str | None) -> str | None:
    return number[:3] if number and len(number) >= 3 else None


def operator_group(number: str | None) -> str | None:
    p = prefix(number)
    if p in CITY_CODES:
        return "city"
    for group, codes in OPERATOR_GROUPS.items():
        if p in codes:
            return group
    return None


def is_home_number(number: str | None) -> bool:
    return prefix(number) in HOME_CODES


def region_name(code: str | None) -> str | None:
    if not code:
        return None
    return CITY_CODES.get(code) or OPERATOR_NAMES.get(code) or f"Префикс {code}"


def operator_name(code: str | None) -> str | None:
    if not code:
        return None
    if code in CITY_CODES:
        return "Городская сеть"
    return OPERATOR_NAMES.get(code) or "Внешний оператор"
