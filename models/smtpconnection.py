import smtplib
import logger
from socket import gaierror
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

COMMASPACE = ', '

class SMTPConnection:
    def __init__(self, host, port):
        self._host = host
        self._port  = port
        self._socket  = host + ':' + port
        self._server  = None
        self._sender = None
        self._recipients = None

        self.__connect()
        self.__start_tls()
        self.__eval_server_features()

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def server(self):
        return self._server

    @property
    def socket(self):
        return self._socket

    @property
    def sender(self):
        return self._sender

    @property
    def recipients(self):
        return self._recipients

    def __ehlo(self):
        try:
            self.server.ehlo()
            if not self.server.does_esmtp:
                logger.error('The server does not support ESMTP')
                exit(1)
        except smtplib.SMTPHeloError:
            logger.error('The server did not reply properly to the EHLO/HELO greeting.')
            exit(1)

    def __connect(self):
        try:
            logger.info('Connecting to SMTP socket (' + self.socket + ')...')
            self._server = smtplib.SMTP(self.host, self.port)
            logger.success('Connected to SMTP server')
        except (gaierror, OSError):
            logger.error('Unable to establish connection to SMTP socket.')
            exit(1)

    def __start_tls(self):
        self.__ehlo()
        if not self.server.has_extn('starttls'):
            logger.error('SMTP server does not support TLS.')
            exit(1)
        else:
            try:
                logger.info('Starting TLS session...')
                self.server.starttls()
                logger.success('Started TLS session')
            except RuntimeError:
                logger.error('SSL/TLS support is not available to your Python interpreter.')
                exit(1)

    def __eval_server_features(self):
        self.__ehlo()

        if not self.server.has_extn('auth'):
            logger.error('No AUTH types detected.')
            exit(1)

        server_auth_features = self.server.esmtp_features.get('auth').strip().split()
        support_auth_features = { auth_type for auth_type in {'PLAIN', 'LOGIN'} if auth_type in server_auth_features }

        if not support_auth_features:
            logger.error('SMTP server does not support AUTH PLAIN or AUTH LOGIN.')
            exit(1)

    def login(self, username, password):
        try:
            return self.server.login(username, password)
        except smtplib.SMTPAuthenticationError:
            logger.error('The server did not accept the username/password combination.')
            return False
        except smtplib.SMTPNotSupportedError:
            logger.error('The AUTH command is not supported by the server.')
            exit(1)
        except smtplib.SMTPException:
            logger.error('Encountered an error during authentication.')
            exit(1)

    def compose_message(self, sender, name, recipients, subject, html):
        self._sender = sender
        self._recipients = recipients

        message = MIMEMultipart('alternative')
        message.set_charset("utf-8")

        message["From"] = name + "<" + sender + ">"
        message['Subject'] = subject
        message["To"] = COMMASPACE.join(recipients)

        body = MIMEText(html, 'html')
        message.attach(body)
        return message;

    def send_mail(self, message):
        try:
            logger.info('Sending spoofed message...')
            self.server.sendmail(self.sender, self.recipients, message.as_string())
            logger.success('Sent message')
        except smtplib.SMTPException:
            logger.error('Unable to send message. Check sender, recipients and message body')
            exit(1)