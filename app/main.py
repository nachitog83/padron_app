import argparse
import locale
import logging
import os
import sys

from schedule import every, repeat, run_pending

from infrastructure import imap, smtp
from service import parser
from utils import parse_error

locale.setlocale(locale.LC_TIME, "es_AR.UTF-8")
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S %Z",
    format="%(levelname)-8s %(asctime)-s %(name)-8s %(funcName)-13s %(message)s",
)
logger = logging.getLogger("APP")


@repeat(every(5).seconds)
def main_email():
    logger.info("Started")
    try:
        with imap as imap_service:
            imap_service.connect()
            msgs = imap_service.fetch_emails()
        if not msgs:
            logger.info("No messages found - Exiting")
            return
        parsed_files = parser.execute(msgs)
        if not parsed_files:
            logger.info("No excel files found - Exiting")
            return
        with smtp as smtp_service:
            smtp_service.connect()
            for file in parsed_files:
                smtp.send_email(file["msg_from"], file["subject"], file["new_attachments"])
    except ConnectionError as e:
        logger.error(parse_error(e))
        return
    logger.info("Stopped")


def main_file(filename: str):
    input_path = os.path.join(os.getcwd(), "input", filename)
    output_filename = "{}_procesado.{}".format(*list(filename.split(".")))
    output_path = os.path.join(os.getcwd(), "output", output_filename)
    output_df = parser.run_parse(input_path)
    logger.info(f"Escribiendo resultado en {output_filename}")
    output_df.to_excel(output_path, index=False, engine="xlsxwriter")
    logger.info("PROCESO FINALIZADO")


if __name__ == "__main__":
    argparser = argparse.ArgumentParser("Run Parser App")
    argparser.add_argument("--source", help="Port to run app on", default="email", type=str)
    args = argparser.parse_args()

    if args.source == "email":
        logger.info("INICIANDO PADRON APP")
        while True:
            run_pending()
    else:
        logger.info("FILE PARSER")
        main_file(args.source)
