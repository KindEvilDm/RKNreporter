
### **RknReporter**

RknReporter - скрипт для автоматизированного получения отчетов по ревизору с сайта https://portal.rfc-revizor.ru/ и отправки их на email/в telegram.

Скрипт работает уже больше года, никаких прецендентов или вопросов от Великих и Ужасных не возникало.

_Да, код не идеален, но он дорабатывается по мере возможности и при наличии времени. На данный момент все работает стабильно._

**Зависимости**:
* Python3 (тестировалось минимум на 3.5.2)
* <a href="https://github.com/tesseract-ocr/">Tesseract</a><br>
`sudo apt install tesseract-ocr
`<br>
*По ощущениям 4 версия справляется лучше, но работает и с 3.<br>
*Для 4 версии используется <a href="https://github.com/Shreeshrii/tessdata_shreetest/blob/master/digits1.traineddata">digits.traineddata</a>

* <a href="https://github.com/ImageMagick">ImageMagick</a><br>
`sudo apt install imagemagick
`<br>

* <a href="https://gitlab.com/muttmua/mutt">mutt</a> (Опционально)<br>
`sudo apt install mutt
`<br>
*естественно его нужно настроить по инструкциям в гуглах.


Клонируем репозиторий, копируем config.default и правим:
`````
cp config.default config
nano config
`````

`````
[DEFAULT]
# Notify может быть telegram или email (в зависимости от того, куда хотим отправлять отчеты)
notify: telegram
# время ожидания отчета (по дефолту 20 мин.)
retry_count: 60

[TELEGRAM]
# Токен бота, котоый будет слать отчеты. https://core.telegram.org/bots#creating-a-new-bot
# Выглядит примерно так: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
telegram_bot_token: token
# Настройки SOCKS5. (бывает нужен для Telegram)
socks5: no
# адрес proxy-сервера в формате <ip_or_hostname>:<port>
socks5_address:
# логин/пароль можно оставить пустыми, если прокси без авторизации
socks5_login:
socks5_password:

[SMTP]
# Использовать mutt для отправки (должен быть заранее настроен)
mutt = no
# Логин/пароль для отправки почты
smtp_login: test@nettools.club
smtp_passwd: supersecret1234
# smtp-сервер (smtp.gmail.com, smtp.yandex.ru, etc...
smtp_server: smtp.gmail.com
# Порт (465 для SSL или 587 для обычного)
smtp_port: 465

[CONTACTS]
# Контакты для отправки отчетов
email: test@nettools.club
# Для отправки в телеграм нужен именно id человека или группы, куда будет отправляться отчет
telegram: userid

[CREDENTIALS]
#  Название организации
orgname: TestOrganization
# Логин/пароль на сайте portal.rfc-revizor.ru
login: test@isp.org
password: secret


``````
Ставим нужные библиотеки:

`pip3 install -r requirements.txt
`

Для удобства:

`chmod +x rknreporter.py
`

Можно сделать несколько конфигурационных файлов (если нужно проверять отчеты по нескольким органзациям) и передавать конфиг в качестве аргумента `--config`:
`````
./rknreporter.py --config config.isp1
./rknreporter.py --config config.isp2
`````
Либо воспользоваться параметрами:

`````
  -h, --help                    show this help message and exit
  --orgname ORGNAME             Название организации
  --login LOGIN                 Логин на portal.rfc-revizor.ru
  --password PASSWORD           Пароль на portal.rfc-revizor.ru
  --date DATE                   Дата в формате 01.01.2018
  --retry-count RETRY_COUNT     Кол-во попыток.
  --notify NOTIFY               Куда отправлять (telegram/email)
  --contact CONTACT             адрес (почта или tg-id)
  --config CONFIG               Файл конфигурации.
`````

Примеры использования:

`./rknreporter.py` - отправит отчет за предыдущий день (в данный момент за текущий день в отчетах всегда написано "Данные обрабатываются..." и толковой информации нет)

`./rknreporter.py --date today` - если все-таки нужно (или если вдруг заработает нормально)

`./rknreporter.py --date 01.01.2019` - на определенную дату

`./rknreporter.py --notify email --contact revizor@yoursuperisp.com` - отправить отчет определенному адресату (даже если в конфиге указан другой)

Высказать мнение/пожелания/реквесты можно сюда:<br>
 <a href="mailto:admin@nettools.club">ds@nettools.club</a><br>
или сюда:<br>
https://t.me/KindEvil <br>

Материально поддержать проект (ну а вдруг?):<br>
<a href="https://paypal.me/kindevildm?locale.x=en_US">paypal.me/kindevildm</a>