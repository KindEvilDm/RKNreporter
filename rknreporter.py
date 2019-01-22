#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

from reporter import Reporter


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--orgname", help="Название организации")
    parser.add_argument("--login", help="Логин на portal.rfc-revizor.ru")
    parser.add_argument("--password", help="Пароль на portal.rfc-revizor.ru")
    parser.add_argument("--date", help="Дата в формате 01.01.2018")
    parser.add_argument("--retry-count", help="Кол-во попыток.")
    parser.add_argument("--notify", help="Куда отправлять (telegram/email)")
    parser.add_argument("--contact", help="адрес (почта или tg-id)")
    parser.add_argument("--config", help="Файл конфигурации.")

    args = parser.parse_args()
    argsdict = vars(args)

    reporter = Reporter(**argsdict)
    is_ok = reporter.get_report()
    if is_ok:
        reporter.parse_and_send()
