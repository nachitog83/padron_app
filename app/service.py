import concurrent.futures
import logging
import os
from ast import Bytes
from dataclasses import fields
from datetime import date
from io import BytesIO
from typing import List, Union

import pandas as pd
from imap_tools import MailMessage

from dtos import ParsedRow
from utils import parse_error

logger = logging.getLogger("PARSER")


class ParseService:

    ALLOWED_SENDERS = {"nachitogrosso@gmail.com", "celinalosano@gmail.com", "candelarialosano@gmail.com"}
    ALLOWED_SUBJECT = "[PADRON {}]"
    ALLOWED_FILENAME = "PADRON_{}"
    ALLOWED_EXTENSIONS = {"xlsx", "xls"}
    REQUIRED_FIELDS = {
        "TIPODOC",
        "NRODOC",
        "NOMBRECOMPLETO",
        "RIESGO",
        "CALLE",
        "NUMERO",
        "PISO",
        "DEPTO",
        "BARRIO",
        "LOCALIDAD",
        "POSTAL",
        "PROVINCIA",
        "TEL_PARTICULAR",
        "TEL_LABORAL",
        "TEL_ALTERNATIVO",
        "TEL_CR_PARTICULAR",
        "TEL_CR_LABORAL",
        "TEL_CR_ALTERNATIVO",
        "EMAIL",
    }

    def _validate_msgs(self, msgs: List[MailMessage]) -> List[dict]:
        month = date.today().strftime("%B").upper()
        parsed_msgs = []
        for msg in msgs:
            if msg.from_ not in self.ALLOWED_SENDERS or msg.subject.upper() != self.ALLOWED_SUBJECT.format(month):
                continue
            parsed = dict(msg_from=msg.from_, subject=msg.subject, valid_attachments=[])
            for att in msg.attachments:
                fname, ext = att.filename.split(".")
                if fname.upper() != self.ALLOWED_FILENAME.format(month) or ext.lower() not in self.ALLOWED_EXTENSIONS:
                    continue
                parsed["valid_attachments"].append(att)
            if parsed["valid_attachments"]:
                parsed_msgs.append(parsed)
        return parsed_msgs

    def _parse_row(self, row: pd.Series) -> List[dict]:
        parsed_row = ParsedRow.build(row)
        new_rows = []
        for phone in parsed_row.TELEFONOS:
            new_row = {}
            new_row = {
                field.name: getattr(parsed_row, field.name) for field in fields(parsed_row) if field.name != "TELEFONOS"
            }
            new_row.update({field.name: getattr(phone, field.name) for field in fields(phone)})
            new_rows.append(new_row)

        return new_rows

    def _convert_to_BytesIO(self, df: pd.DataFrame) -> BytesIO:
        output = BytesIO()
        try:
            writer = pd.ExcelWriter(output, engine="xlsxwriter")
            df.to_excel(writer, sheet_name="Sheet1", index=False)
            writer.save()
        except Exception as e:
            logger.error(parse_error(e))
            output = None
        return output

    def _load_dataframe(self, data: Union[Bytes, str], skip_rows: List = None) -> Union[pd.DataFrame, None]:
        skip_rows = []
        if skip_rows and skip_rows[0] == 3:
            return None
        df = pd.read_excel(data, skiprows=skip_rows)
        df.columns = df.columns.str.strip()
        if not all(col in df.columns for col in self.REQUIRED_FIELDS):
            if not skip_rows:
                skip_rows.append(0)
            else:
                skip_rows.append(skip_rows[-1] + 1)
            df = self._load_dataframe(data, skip_rows)
        if isinstance(df, pd.DataFrame):
            df = df[list(self.REQUIRED_FIELDS)]
        return df

    def run_parse(self, data: Union[Bytes, str]) -> Union[pd.DataFrame, None]:
        padron = self._load_dataframe(data)
        if not isinstance(padron, pd.DataFrame):
            logger.error(f"Missing required field in padron")
            return
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for _, row in padron.iterrows():
                future = executor.submit(self._parse_row, row)
                results.extend(future.result())
        output_df = pd.DataFrame(results)
        output_df = output_df.sort_values(by="NOMBRECOMPLETO").reset_index(drop=True)
        return output_df

    def execute(self, msgs: List[MailMessage]) -> List[dict]:
        parsed_msgs = self._validate_msgs(msgs)
        if not parsed_msgs:
            logger.info("No padron excel files found in messages")
            return
        for parsed_msg in parsed_msgs:
            new_attachments = []
            for attachment in parsed_msg["valid_attachments"]:
                output_df = self.run_parse(attachment.payload)
                new_filename = "{}_procesado.{}".format(*list(attachment.filename.split(".")))
                new_attachment = dict(file_name=new_filename, data=self._convert_to_BytesIO(output_df))
                new_attachments.append(new_attachment)
            parsed_msg["new_attachments"] = new_attachments
        return parsed_msgs


parser = ParseService()
