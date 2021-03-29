from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import ssl
from logging import getLogger


log = getLogger(__name__)


def send_mail(receiver_email, subject, body, config):
    message = MIMEMultipart()
    message["From"] = config['smtpsender']
    message["Subject"] = subject
    if isinstance(receiver_email, list):
        message["To"] = '"Undisclosed Recipients"'
        message["Bcc"] = ", ".join(receiver_email)
    else:
        message["To"] = receiver_email

    message.attach(MIMEText(body, "plain"))
    message = message.as_string()
    if config.get('smtptls'):
        # Create a secure SSL context
        context = ssl.create_default_context()
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_default_certs()
        if config['smtp_cafile']:
            context.load_verify_locations(cafile=config['smtp_cafile'])
        with smtplib.SMTP_SSL(config['smtphost'], config['smtpport'],
                              context=context) as server:
            if config['smtpuser'] and config['smtppass']:
                server.login(config['smtpuser'], config['smtppass'])
            server.sendmail(config['smtpsender'],
                            receiver_email,
                            message)
    else:
        with smtplib.SMTP(config['smtphost'], config['smtpport']) as server:
            if config['smtpuser'] and config['smtppass']:
                server.login(config['smtpuser'], config['smtppass'])
            server.sendmail(config['smtpsender'],
                            receiver_email,
                            message)


def send_mails(addresses, subject, body, config):
    try:
        send_mail(addresses, subject, body, config)
    except Exception as e:
        log.error("Sending mail failed: %s" % e)
        log.exception(e)
