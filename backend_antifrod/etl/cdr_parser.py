"""
Разбор и валидация строк CDR_OUT.

Формат строки (без заголовка, разделитель ';', 7 полей):
    type;imsi;num_a;num_b;date;duration;num_c
    type      — 01 | 02 | 03
    imsi      — 15 цифр (обязателен для 02, пуст для 01, опционален для 03)
    num_a     — 10 цифр, инициатор
    num_b     — 10 цифр, адресат
    date      — YYYYmmddHHMMSS, локальное время оператора (CDR_TIMEZONE)
    duration  — секунды, 0..86400
    num_c     — 10 цифр или пусто, номер переадресации

Модуль не зависит от БД — его используют загрузчик, API загрузки и тесты.
"""
import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime

from core import telecom

EXPECTED_FIELDS = 7
ALLOWED_TYPES = {"01", "02", "03"}
MIN_DURATION = 0
MAX_DURATION = 86400

DIRECTION_BY_TYPE = {"01": "outgoing", "02": "incoming", "03": "forwarded"}

E_FIELD_COUNT = "field_count"
E_TYPE = "invalid_type"
E_DATE = "invalid_date"
E_DURATION = "invalid_duration"
E_NUM_A = "invalid_num_a"
E_NUM_B = "invalid_num_b"
E_NUM_C = "invalid_num_c"
E_IMSI_MISSING = "imsi_missing"
E_IMSI_FORBIDDEN = "imsi_not_allowed"
E_IMSI = "invalid_imsi"
E_SAME_NUMBER = "same_number"
E_ENCODING = "bad_encoding"

ERROR_LABELS = {
    E_FIELD_COUNT: "Неверное число полей",
    E_TYPE: "Неизвестный тип записи",
    E_DATE: "Некорректная дата",
    E_DURATION: "Некорректная длительность",
    E_NUM_A: "Некорректный номер A",
    E_NUM_B: "Некорректный номер B",
    E_NUM_C: "Некорректный номер переадресации",
    E_IMSI_MISSING: "Нет IMSI для типа 02",
    E_IMSI_FORBIDDEN: "IMSI указан для типа 01",
    E_IMSI: "Некорректный IMSI",
    E_SAME_NUMBER: "Номер A совпадает с номером B",
    E_ENCODING: "Битая кодировка строки",
}


@dataclass(frozen=True)
class CdrError:
    code: str
    reason: str
    fields_found: int | None = None


@dataclass(frozen=True)
class CdrRecord:
    type: str
    imsi: str | None
    num_a: str
    num_b: str
    num_c: str | None
    started_at: datetime
    duration: int

    @property
    def direction(self) -> str:
        return DIRECTION_BY_TYPE[self.type]

    @property
    def hung_up_first_second(self) -> bool:
        return self.duration <= 1

    @property
    def time_bucket(self) -> str:
        h = self.started_at.hour
        if h < 6:
            return "night"
        if h < 12:
            return "morning"
        if h < 18:
            return "day"
        return "evening"

    @property
    def source_operator(self) -> str | None:
        return telecom.prefix(self.num_a)

    @property
    def foreign_origin(self) -> bool:
        return not telecom.is_home_number(self.num_a)

    @property
    def source_country(self) -> str:
        return telecom.UNKNOWN_COUNTRY if self.foreign_origin else telecom.HOME_COUNTRY

    @property
    def connection_type(self) -> str:
        if self.imsi:
            return "mobile"
        group = telecom.operator_group(self.num_a)
        if group == "city":
            return "pstn"
        if group is not None:
            return "mobile"
        # Источник вне известных сетей — вызов пришёл через внешний шлюз
        return "sip_gateway"

    def row_hash(self) -> str:
        """Ключ дедупликации: одинаковые записи из разных файлов/повторных загрузок совпадут."""
        return row_hash(self.type, self.imsi, self.num_a, self.num_b, self.started_at, self.duration, self.num_c)


def row_hash(type_: str, imsi: str | None, num_a: str, num_b: str,
             started_at: datetime, duration: int, num_c: str | None) -> str:
    # Канонический формат хеша для дедупликации нормализованных CDR.
    key = "|".join([
        type_, imsi or "", num_a, num_b,
        started_at.strftime("%Y%m%d%H%M%S"), str(duration), num_c or "",
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _is_digits(value: str, length: int) -> bool:
    return len(value) == length and value.isascii() and value.isdigit()


def _err(code: str, detail: str = "", fields_found: int | None = None) -> CdrError:
    reason = ERROR_LABELS[code] + (f": {detail}" if detail else "")
    return CdrError(code=code, reason=reason[:200], fields_found=fields_found)


def parse_line(line: str) -> CdrRecord | CdrError | None:
    """None — пустая строка (пропускается), CdrError — невалидная, CdrRecord — валидная."""
    line = line.rstrip("\r\n")
    if not line.strip():
        return None
    if "�" in line or "\x00" in line:
        return _err(E_ENCODING)

    parts = [p.strip() for p in next(csv.reader([line], delimiter=";"))]
    if len(parts) != EXPECTED_FIELDS:
        return _err(E_FIELD_COUNT, f"ожидалось {EXPECTED_FIELDS}, найдено {len(parts)}", len(parts))

    type_, imsi, num_a, num_b, date_s, dur_s, num_c = parts

    if type_ not in ALLOWED_TYPES:
        return _err(E_TYPE, f"'{type_[:20]}'", EXPECTED_FIELDS)

    if not _is_digits(date_s, 14):
        return _err(E_DATE, f"'{date_s[:20]}'", EXPECTED_FIELDS)
    try:
        started_at = datetime.strptime(date_s, "%Y%m%d%H%M%S")
    except ValueError:
        return _err(E_DATE, f"'{date_s}'", EXPECTED_FIELDS)

    if not (dur_s.isascii() and dur_s.isdigit()) or not (MIN_DURATION <= int(dur_s) <= MAX_DURATION):
        return _err(E_DURATION, f"'{dur_s[:20]}'", EXPECTED_FIELDS)

    if not _is_digits(num_a, 10):
        return _err(E_NUM_A, f"'{num_a[:20]}'", EXPECTED_FIELDS)
    if not _is_digits(num_b, 10):
        return _err(E_NUM_B, f"'{num_b[:20]}'", EXPECTED_FIELDS)
    if num_c and not _is_digits(num_c, 10):
        return _err(E_NUM_C, f"'{num_c[:20]}'", EXPECTED_FIELDS)
    if num_a == num_b:
        return _err(E_SAME_NUMBER, num_a, EXPECTED_FIELDS)

    if type_ == "01" and imsi:
        return _err(E_IMSI_FORBIDDEN, fields_found=EXPECTED_FIELDS)
    if type_ == "02" and not imsi:
        return _err(E_IMSI_MISSING, fields_found=EXPECTED_FIELDS)
    if imsi and not _is_digits(imsi, 15):
        return _err(E_IMSI, f"'{imsi[:20]}'", EXPECTED_FIELDS)

    return CdrRecord(
        type=type_,
        imsi=imsi or None,
        num_a=num_a,
        num_b=num_b,
        num_c=num_c or None,
        started_at=started_at,
        duration=int(dur_s),
    )
