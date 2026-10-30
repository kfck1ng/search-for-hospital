#!/usr/bin/env python3
"""Надсилає digest.md на список адрес через Gmail (SMTP).

Потрібні секрети репозиторію:
  MAIL_USER          адреса Gmail, з якої надсилаємо
  MAIL_APP_PASSWORD  пароль застосунку Google (не звичайний пароль)
  MAIL_TO            адреси отримувачів через кому

Коди виходу: 0 лист надіслано, 2 секрети не задані, 1 помилка надсилання.
Workflow у разі коду, відмінного від 0, створює Issue на GitHub.
"""
import html
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    user = os.environ.get("MAIL_USER", "").strip()
    password = os.environ.get("MAIL_APP_PASSWORD", "").strip()
    to = [a.strip() for a in os.environ.get("MAIL_TO", "").split(",") if a.strip()]
    if not (user and password and to):
        print("Секрети MAIL_USER, MAIL_APP_PASSWORD, MAIL_TO не задані: лист не надсилаємо.")
        return 2
    try:
        with open(os.path.join(HERE, "digest.md"), encoding="utf-8") as f:
            body = f.read().strip()
    except OSError:
        body = ""
    if not body:
        print("Нових записів немає, лист не потрібен.")
        return 0

    dash = os.environ.get("DASHBOARD_URL", "").strip()
    m = re.search(r"\((\d+)\)", body.splitlines()[0])
    count = m.group(1) if m else "нові"
    subject = "Можливості для лікарні: %s нових записів" % count

    link_re = re.compile(r"\*\*\[(.*?)\]\((.*?)\)\*\*")
    text = link_re.sub(lambda mm: "%s\n  %s" % (mm.group(1), mm.group(2)), body)
    if dash:
        text += "\n\nДашборд: " + dash

    h = html.escape(body)
    h = re.sub(r"\*\*\[(.*?)\]\((.*?)\)\*\*", r'<a href="\2"><b>\1</b></a>', h)
    h = h.replace("\n", "<br>")
    if dash:
        h += '<br><br><a href="%s">Відкрити дашборд</a>' % html.escape(dash)

    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, ", ".join(to)
    msg.set_content(text)
    msg.add_alternative("<html><body style=\"font-family:sans-serif\">%s</body></html>" % h, subtype="html")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as s:
            s.login(user, password)
            s.send_message(msg, to_addrs=to)
    except Exception as e:
        print("Не вдалося надіслати лист:", e, file=sys.stderr)
        return 1
    print("Лист надіслано:", len(to), "отримувачів")
    return 0


if __name__ == "__main__":
    sys.exit(main())
