#!/usr/bin/env python3
import asyncio
from twilio.rest import Client
import imaplib
import email
import re
import os
from datetime import datetime
import quopri
from email.header import decode_header
import time
from dotenv import load_dotenv
load_dotenv()


def decode_subject(encoded_subject):
    decoded_parts = decode_header(encoded_subject)
    decoded_text = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_text += part.decode(encoding or 'utf-8')
        else:
            decoded_text += part
    return decoded_text

# Function to check for specific keywords in email subject or body
def check_keywords(msg, keywords, sender_list):
    subject = msg['Subject']
    decoded_subject = decode_subject(subject)
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" not in content_disposition:
                body += str(part.get_payload(decode=True))
    else:
        body = str(msg.get_payload(decode=True))
    # print(body)
        
    for sender in sender_list:
        if re.search(sender, msg["From"], re.IGNORECASE):
            return True, sender
    for keyword in keywords:
        if re.search(keyword, str(subject), re.IGNORECASE) or re.search(keyword, body, re.IGNORECASE):
            return True, keyword
    return False, None

# Function to send WhatsApp notification
async def send_whatsapp_notification(account_sid, auth_token, from_whatsapp_number, to_whatsapp_number, message):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=message,
        from_='whatsapp:' + from_whatsapp_number,
        to='whatsapp:' + to_whatsapp_number
    )
    print("WhatsApp message sent:", message.sid)

# Function to connect to the IMAP server and check for new emails
async def check_email(server, username, password, keywords, sender_list, twilio_credentials, from_whatsapp_number, to_whatsapp_number):
    mail = imaplib.IMAP4_SSL(server)
    mail.login(username, password)
    mail.select('inbox')

    today = datetime.today()
    start_date = today.strftime('%d-%b-%Y')
    start_date_imap = start_date.replace(' ', '-').capitalize()

    # sender_criteria = ' OR '.join([f"""(FROM "{sender}" OR HEADER FROM "{sender}")""" for sender in sender_list])
    # keyword_criteria = ' OR '.join([f"""(SUBJECT "{keyword}") (BODY "{keyword}")""" for keyword in keywords])
    # criteria = f"(UNSEEN) (SINCE {start_date_imap}) (({sender_criteria}) OR ({keyword_criteria}))"
    criteria = f"""(UNSEEN) (SINCE "{start_date_imap}")"""
    # print(criteria)
    status, data = mail.search(None, criteria)

    if status == 'OK':
        print("len:",len(data[0].split()))
        for num in data[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            if status == 'OK':
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                subject = msg['Subject']
                sender=msg['From']
                # print(f"Sender: {sender}")
                decoded_subject = decode_subject(subject)
                # print("Subject:", decoded_subject)
                if_status,keyword = check_keywords(msg, keywords, sender_list)
                if if_status:
                    print("hello")
                    await send_whatsapp_notification(*twilio_credentials, from_whatsapp_number, to_whatsapp_number, f"Keyword: {keyword}\nSubject: {decoded_subject}\nSender: {sender}")
    mail.close()
    mail.logout()

# Example usage
async def main():
    server = 'imap.gmail.com'
    username = os.environ["MY_EMAIL"]
    password = os.environ["MY_PASSWORD"]
    account_sid = os.environ["ACCOUNT_SID"]
    token = os.environ["TOKEN"]
    keywords=os.environ["KEYWORDS"].split(",")
    keywords=[keyword.strip() for keyword in keywords]
    sender_list=os.environ["SENDERS"].split(",")
    sender_list=[sender.strip() for sender in sender_list]
    twilio_credentials = (account_sid, token)
    from_whatsapp_number = os.environ['BOT_NUMBER']
    to_whatsapp_number = os.environ['MY_NUMBER']
    await check_email(server, username, password, keywords, sender_list, twilio_credentials, from_whatsapp_number, to_whatsapp_number)

# Run the script

while True:
    try:
        asyncio.run(main())
    except:
        print("error occured")
    time.sleep(60)
