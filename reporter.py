#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import zipfile
import requests
import subprocess
import time
import re
import datetime
import csv
import logging
import configparser
import pytesseract
import sys
import smtplib

from email.mime.text import MIMEText
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.multipart import MIMEMultipart

from PIL import Image
from bs4 import BeautifulSoup
from distutils.version import LooseVersion
from pathlib import Path


class Reporter:
    def __init__(self, **kwargs):
        # logging settings
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)

        filehandler = logging.FileHandler('rknreporter.log')
        filehandler.setLevel(logging.INFO)
        filehandler.setFormatter(formatter)
        self.logger.addHandler(console)
        self.logger.addHandler(filehandler)
        # end of logging settings

        config = configparser.ConfigParser()
        if kwargs['config']:
            configfile = Path(kwargs['config'])
            if configfile.is_file():
                config.read(str(configfile))
            else:
                self.logger.warning("Файл конфигурации {} не найден!".format(configfile))
                self.logger.info("Пробуем конфгурацию по умолчанию.")
                configfile = Path('config')
                if configfile.is_file():
                    config.read(str(configfile))
                else:
                    self.logger.warning("Файл конфигурации {} не найден!".format(configfile))
                    sys.exit()
        else:
            configfile = Path('config')
            if configfile.is_file():
                config.read(str(configfile))
            else:
                self.logger.warning("Файл конфигурации {} не найден!".format(configfile))
                sys.exit()

        self.orgname = config['CREDENTIALS']['orgname']
        self.login = config['CREDENTIALS']['login']
        self.password = config['CREDENTIALS']['password']

        self.retry_count = int(config["DEFAULT"]['retry_count'])

        self.notify = config["DEFAULT"]['notify']

        self.telegram = config['CONTACTS']['telegram']
        self.email = config['CONTACTS']['email']

        self.telegram_bot_token = config['TELEGRAM']['telegram_bot_token']
        self.socks5 = config['TELEGRAM'].getboolean('socks5')
        self.socks5_address = config['TELEGRAM']['socks5_address']
        self.socks5_login = config['TELEGRAM']['socks5_login']
        self.socks5_password = config['TELEGRAM']['socks5_password']

        self.mutt_enabled = config['SMTP'].getboolean('mutt')
        self.smtp_login = config['SMTP']['smtp_login']
        self.smtp_passwd = config['SMTP']['smtp_passwd']
        self.smtp_port = config['SMTP']['smtp_port']
        self.smtp_server = config['SMTP']['smtp_server']

        if kwargs['orgname']:
            self.orgname = kwargs['orgname']
        if kwargs['login']:
            self.login = kwargs['login']
        if kwargs['password']:
            self.password = kwargs['password']
        if kwargs['retry_count']:
            self.retry_count = int(kwargs['retry_count'])
        if kwargs['date']:
            if kwargs['date'] == "today":
                self.date = datetime.datetime.now().strftime("%d.%m.%Y")
            elif kwargs['date'] == "yesterday":
                self.date = (datetime.datetime.now() - datetime.timedelta(1)).strftime("%d.%m.%Y")
            else:
                self.date = kwargs['date']
        else:
            self.date = (datetime.datetime.now() - datetime.timedelta(1)).strftime("%d.%m.%Y")
        if kwargs['notify']:
            self.notify = kwargs['notify']
            if self.notify == "telegram":
                self.telegram = kwargs['contact'] if kwargs['contact'] else config['CONTACTS']['telegram']
            elif self.notify == "email":
                self.email = kwargs['contact'] if kwargs['contact'] else config['CONTACTS']['email']

    def send_to_telegram(self, header):
        self.logger.info("Отправляем отчет в Telegram.")
        proxy = {}
        if self.socks5:
            if self.socks5_login and self.socks5_password:
                proxy = {
                    'https': 'socks5://{}:{}@{}'.format(self.socks5_login, self.socks5_password, self.socks5_address)}
            else:
                proxy = {
                    'https': 'socks5://{}'.format(self.socks5_address)}
        send_message_url = "https://api.telegram.org/bot{}/sendMessage".format(self.telegram_bot_token)
        payload = {'chat_id': self.telegram, 'text': header}
        requests.post(send_message_url, data=payload, proxies=proxy)

        if "Отчет не сгенерирован" or "Данные обрабатываются" not in header:
            send_file_url = "https://api.telegram.org/bot{}/sendDocument".format(self.telegram_bot_token)
            payload = {'chat_id': self.telegram}
            report = {'document': open('report/report.csv', 'rb')}
            temp = requests.post(send_file_url, data=payload, proxies=proxy, files=report)
            self.logger.debug(temp.text)

    def send_to_email(self, header, total_fails):
        self.logger.info("Отправляем отчет на email.")
        print(self.mutt_enabled)
        if self.mutt_enabled:
            if "Отчет не сгенерирован" or "Данные обрабатываются" not in header:
                attach_file = ''
            else:
                attach_file = '-a "report/report.csv"'
            mailsubject = "Отчет по {} за {}. (Пропусков: {})".format(self.orgname, self.date,
                                                                      total_fails)
            cmd_send_by_email = ' echo "{}" | mutt {} -s "{}" -- {}'.format(header,
                                                                            attach_file,
                                                                            mailsubject,
                                                                            self.email)
            temp = subprocess.getoutput(cmd_send_by_email)
            self.logger.debug(temp)
        else:
            mailsubject = "Отчет по {} за {}. (Пропусков: {})".format(self.orgname, self.date,
                                                                      total_fails)
            sender = self.smtp_login
            passwd = self.smtp_passwd
            receiver = self.email

            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = mailsubject

            if "Отчет не сгенерирован" or "Данные обрабатываются" not in header:
                with open('report/report.csv', encoding='cp1251') as f:
                    report_file = f.read()

                    attachment = MIMENonMultipart('text', 'csv', charset='cp1251')
                    attachment.add_header('Content-Disposition', 'attachment', filename='report.csv')

                    attachment.set_payload(report_file.encode('cp1251'))
                    msg.attach(attachment)

            msg_body = MIMEText(header)
            msg.attach(msg_body)

            smtp_server_name = self.smtp_server
            port = self.smtp_port

            if port == '465':
                server = smtplib.SMTP_SSL('{}:{}'.format(smtp_server_name, port))
            else:
                server = smtplib.SMTP('{}:{}'.format(smtp_server_name, port))
                server.starttls()  # this is for secure reason

            server.login(sender, passwd)
            server.send_message(msg)
            server.quit()

    def send_report(self, header, total_fails):
        if self.notify == "telegram":
            self.send_to_telegram(header)
        elif self.notify == "email":
            self.send_to_email(header, total_fails)

    def get_report(self):
        success = False
        i = 0
        cookies = ""
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/71.0.3578.98 Safari/537.36'}

        self.logger.info("Получение нового отчета для {}".format(self.orgname))

        while not success:

            url = "https://portal.rfc-revizor.ru"
            r = requests.get(url, headers=headers)

            # забираем куки
            cookies = r.cookies

            soup = BeautifulSoup(r.text, "lxml")
            secretcode_tag = soup.find(attrs={"name": "secretcodeId"})
            captcha_id = secretcode_tag['value']
            captcha_url = "https://portal.rfc-revizor.ru/captcha/{}".format(captcha_id)
            captcha_img = requests.get(captcha_url, cookies=cookies, headers=headers)

            if captcha_img.ok:
                with open(".tmp/rkncaptcha.png", 'wb') as f:
                    f.write(captcha_img.content)

            # конвертим капчу для улучшения распознавания
            conv = subprocess.getoutput('convert .tmp/rkncaptcha.png -median 4 -threshold 10% .tmp/rkncaptcha2.png')

            # tesseract
            tesseract_version = pytesseract.get_tesseract_version()
            if tesseract_version < LooseVersion("4.0.0"):
                tessdata_config = r'-psm 8 nobatch digits'
                ocr_result = pytesseract.image_to_string(Image.open('.tmp/rkncaptcha2.png'), config=tessdata_config)
            else:
                tessdata_dir_config = r'--tessdata-dir "tessdata"'
                ocr_result = pytesseract.image_to_string(Image.open('.tmp/rkncaptcha2.png'), lang='digits',
                                                         config=tessdata_dir_config)
            captcha = ""
            for char in ocr_result:
                if char.isdigit():
                    captcha += char

            if captcha and 100 < int(captcha) < 10000:
                self.logger.debug("Капча: {}".format(captcha))  # debug

                start_page_url = "https://portal.rfc-revizor.ru/login/"
                payload = {'email': self.login,
                           'password': self.password,
                           'secretcodeId': captcha_id,
                           'secretcodestatus': captcha}

                start_page = requests.post(start_page_url, data=payload, cookies=cookies, headers=headers).text

                if 'Неверные символы!' in start_page:
                    self.logger.info("Ошибка решения капчи - Неверное решение.")
                    i += 1
                    if i > 30:
                        self.logger.info("Каптча не решена за 30 попыток. Выход.")
                        return 0
                    time.sleep(2)
                elif 'Неверный пароль!' in start_page:
                    self.logger.warning("Неверный пароль.")
                    return 0
                elif 'Пользователя с таким e-mail не существует!' in start_page:
                    self.logger.warning("Пользователя с таким e-mail не существует.")
                    return 0
                elif 'Мои отчеты' in start_page:
                    self.logger.info("Авторизация пройдена. Запрашиваем отчет.")
                    success = True
            else:
                self.logger.info("Ошибка решения капчи - Слишком много символов.")
                time.sleep(2)

        # Запрашиваем новый отчет
        request_report_url = "https://portal.rfc-revizor.ru/cabinet/myclaims-reports/create"
        payload = {'reportDate': self.date}

        request_report_page = requests.post(request_report_url, data=payload, cookies=cookies, headers=headers)
        self.logger.debug(request_report_page.text)

        i = 1
        while i < self.retry_count + 1:
            self.logger.info("Попытка " + str(i) + "/{}...".format(self.retry_count))

            request_report_url = "https://portal.rfc-revizor.ru/cabinet/myclaims-reports/"
            answer = requests.get(request_report_url, cookies=cookies, headers=headers)
            soup = BeautifulSoup(answer.text, "lxml")

            if soup.find('tbody').find('tr').find('td', text=re.compile('новый')):
                self.logger.info('Отчет не готов. Ждем 20 сек...')
                time.sleep(20)
                i += 1
            if soup.find('tbody').find('tr').find('td', text=re.compile('результат готов')):
                self.logger.info('Отчет готов к загрузке')
                reportlink = soup.find('tbody').find('tr').find('a')['href']
                res = "Отчет загружен."
                i = 65

                downloadreportlink = 'https://portal.rfc-revizor.ru{}'.format(reportlink)
                report = requests.get(downloadreportlink, cookies=cookies, headers=headers, stream=True)

                if report.ok:
                    self.logger.info("Разархивируем в ./report")
                    z = zipfile.ZipFile(io.BytesIO(report.content))
                    z.extractall("report/")
                    self.logger.info("Отчет разархивирован.")
                    return 1
        res = "Время ожидания ({} мин.) истекло. Отчет не сгенерирован. ".format(
            str(self.retry_count * 20 / 60))
        self.logger.info(res)
        self.send_report(res, "Timeout")
        return 0

    def parse_and_send(self):
        total_fails = "0"
        with open('report/report.csv', 'r', encoding='cp1251') as report_csv:
            content = csv.reader(report_csv, delimiter=' ', quotechar='|')

            header = 'Отчет по "{}":\n'.format(self.orgname)
            headerlength = 0
            stop = False
            for row in content:
                if not stop:
                    header = header + '\n'
                    headerlength += 1
                else:
                    break
                for col in row:
                    if col == "Отчет" or col == '"Отчет' or col == "Категория;Количество":
                        break
                    if "проводился" in col:  # Монторинг в указанную дату не проводился
                        header = header + " " + col
                        total_fails = "N/A"
                        stop = True
                        break
                    if "нарушений" in col:  # Мониторинг не выявил нарушений
                        header = header + " " + col
                        total_fails = "0"
                        stop = True
                        break
                    if "позже." in col:  # Данные обрабатываются. Повторите запрос позже.
                        header = header + " " + col
                        total_fails = "N/A"
                        stop = True
                        break
                    if col != "Время":
                        header = header + " " + col
                    else:
                        stop = True
                        break

        report_csv.close()
        header = "\n".join([ll.rstrip() for ll in header.splitlines() if ll.strip()])
        header = header.replace('"', '')
        header = header.replace(';', ' ')

        for line in header.splitlines():
            if "Всего" in line:
                total_fails = line.split()[1]
        self.logger.debug(header)
        self.send_report(header, total_fails)
