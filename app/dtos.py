import logging
import math
import re
from dataclasses import dataclass, fields
from typing import List, Optional

import pandas as pd
import phonenumbers

from utils import parse_error

logger = logging.getLogger("DATA")


@dataclass
class Phones:
    TIPO_TELEFONO: Optional[str] = None
    TELEFONO: Optional[str] = None

    @classmethod
    def build(cls, data: dict) -> "Phones":
        data["TELEFONO"] = cls._convert_phone_number(data["TELEFONO"])
        return cls(**data)

    @staticmethod
    def _convert_phone_number(number: str) -> Optional[int]:
        number = str(number)
        number = re.sub("[^0-9]+", "", number)  # leave numbers only
        number = number.lstrip("0")  # remove all leading zeroes
        try:
            number = phonenumbers.parse(number, "AR")
        except Exception as e:
            return None
        number = str(number.national_number)
        if number[0] == "9":
            number = number[1:]
        return number


@dataclass
class ParsedRow:
    TIPODOC: str
    NRODOC: int
    NOMBRECOMPLETO: str
    TELEFONOS: List[Phones]
    RIESGO: Optional[str] = None
    CALLE: Optional[str] = None
    NUMERO: Optional[int] = None
    PISO: Optional[str] = None
    DEPTO: Optional[str] = None
    BARRIO: Optional[str] = None
    LOCALIDAD: Optional[str] = None
    POSTAL: Optional[int] = None
    PROVINCIA: Optional[str] = None
    EMAIL: Optional[str] = None

    @classmethod
    def build(cls, row: pd.Series) -> "ParsedRow":
        try:
            data = row.to_dict()
            cls._sanitize_fields(data)
            phone_data = [dict(TIPO_TELEFONO=k, TELEFONO=v) for k, v in data.items() if k.startswith("TEL_") and v]
            # Placeholder in case we want to add client data for those without phone information
            # if not phone_data:
            #     phone_data.append(dict(TIPO_TELEFONO="Not found", TELEFONO=""))
            phones = [Phones.build(phone) for phone in phone_data]
            kwargs = {field.name: data.get(field.name, None) for field in fields(cls)}
            kwargs.update(TELEFONOS=phones)
            return cls(**kwargs)
        except Exception as e:
            logger.error(f"{parse_error(e)} - {row}")

    @staticmethod
    def _sanitize_fields(data):
        for k, v in data.items():
            if isinstance(v, str):
                v = v.strip()
                if v in {"nan", ""}:
                    data[k] = None
            elif isinstance(v, (float, int)):
                if math.isnan(v):
                    data[k] = None
        return data
