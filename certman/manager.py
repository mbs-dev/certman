import yaml
import os
import re
import sqlite3
import shutil
import time

from datetime import datetime, timedelta, date
from email.utils import parseaddr

from certman.settings import SETTINGS


def get_current_week():
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


class Certificate(object):
    def __init__(self, email, password=None, questions=None, enrollment_id=None, date_obtained=None):
        self.email = email
        self.password = password
        self.questions = questions
        self.enrollment_id = enrollment_id
        self.date_obtained = date_obtained or date.today()

    def __repr__(self):
        return '%s:%s / %s / %s' % (self.email, self.password, self.enrollment_id, self.date_obtained)

    def __eq__(self, obj):
        return self.__dict__ == obj.__dict__

    def is_bound(self):
        all_fields_not_empty = all((self.email, self.password, self.questions, self.enrollment_id))
        email_valid = re.search(r'[\w.-]+@[\w.-]+.\w+', self.email) is not None
        return all_fields_not_empty and email_valid


class CertificateFileStorage(object):
    def __init__(self, store_path):
        self.store_path = store_path

    def save(self, certificate):
        new_path = os.path.join(self.store_path, certificate.email)
        os.mkdir(new_path)
        with open(new_path + '/credentials.yaml', 'w') as f:
            store_obj = {
                'certificate': certificate.__dict__
            }
            f.write(yaml.dump(store_obj, default_flow_style=False))

    def delete(self, email):
        path = os.path.join(self.store_path, email)
        shutil.rmtree(path)

    def check_exist(self, certificate):
        new_path = os.path.join(self.store_path, certificate.email)
        return os.path.exists(new_path)


class CertificateDBStorage(object):
    def __init__(self, db):
        self.conn = sqlite3.connect(db)
        self._apply_schema()

    @classmethod
    def format_questions(cls, questions):
        result = ''.join(['question%s: "%s"\n' % (i, questions[i-1]) for i in range(1, len(questions) + 1)])
        return result

    @classmethod
    def parse_questions(cls, questions_str):
        return [m.group(1) for m in re.finditer(r'"([^"]+)"', questions_str)]

    def _apply_schema(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS certificates
            (id integer primary key, when_added date, email text, password text, enrollment_id text, questions text);''')
        self.conn.commit()

    def save(self, certificate):
        c = self.conn.cursor()
        if certificate.date_obtained:
            date_string = certificate.date_obtained.strftime('%Y-%m-%d')
        else:
            date_string = datetime.now().date().strftime('%Y-%m-%d')
        params = {
            'email': certificate.email,
            'password': certificate.password,
            'enrollment_id': certificate.enrollment_id,
            'questions': self.format_questions(certificate.questions),
            'date_string': date_string
        }
        c.execute("INSERT INTO certificates VALUES (NULL, date('%(date_string)s'), '%(email)s', '%(password)s', '%(enrollment_id)s', '%(questions)s');" % params)
        self.conn.commit()

    def _certificate_from_db(self, fetched):
        email, password, enrollment_id, questions_str, when_added = fetched
        questions = self.parse_questions(questions_str)
        when_added = datetime.strptime(when_added, '%Y-%m-%d').date()
        return Certificate(email, password, questions, enrollment_id, when_added)

    def get_by_email(self, email):
        if not email:
            return None

        c = self.conn.cursor()
        c.execute("SELECT email, password, enrollment_id, questions, when_added FROM certificates WHERE email='%s';" % email)
        db_row = c.fetchone()
        if not db_row:
            return None
        certificate = self._certificate_from_db(db_row)
        return certificate

    def get_by_id(self, cert_id):
        if not cert_id:
            return None

        c = self.conn.cursor()
        c.execute("SELECT email, password, enrollment_id, questions, when_added FROM certificates WHERE id='%s';" % cert_id)
        db_row = c.fetchone()
        if not db_row:
            return None
        certificate = self._certificate_from_db(db_row)
        return certificate

    def get_by_date(self, start, end):
        start_str = start.strftime('%Y-%m-%d')
        end_str = end.strftime('%Y-%m-%d')

        c = self.conn.cursor()

        c.execute("SELECT email, password, enrollment_id, questions, when_added FROM certificates WHERE when_added >= '%s' AND when_added <= '%s' ORDER BY when_added ASC;" % (start_str, end_str))
        records = c.fetchall()
        for record in records:
            yield self._certificate_from_db(record)

    def delete(self, id_num):
        try:
            certificate = self.get_by_id(id_num) or self.get_by_email(id_num)
            c = self.conn.cursor()
            c.execute("DELETE FROM certificates WHERE email='%s';" % certificate.email)
            self.conn.commit()
            return certificate
        except Exception as e:
            return None

    def check_exist(self, certificate):
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM certificates WHERE email='%s'" % certificate.email)
            certificate = c.fetchone()
            return certificate is not None
        except Exception as e:
            return None


class Reporter(object):
    def __init__(self, db_storage):
        self.storage = db_storage

    def generate_report(self):
        week_start, week_end = get_current_week()

        certificates = self.storage.get_by_date(week_start, week_end)
        result = [[cert.date_obtained.strftime('%d.%m.%Y'), cert.email, cert.password, cert.enrollment_id, CertificateDBStorage.format_questions(cert.questions)] for cert in certificates]
        total = len(result)
        return result, total


class Manager(object):
    def command_addcert(self):
        file_storage = CertificateFileStorage(store_path=SETTINGS['store_path'])
        db_storage = CertificateDBStorage(db=SETTINGS['db'])
        count = 0
        ask = True
        while ask:
            certificate = Certificate(email=(raw_input('E-mail: ')).strip(),
                                      questions=[raw_input('Question %s: ' % i) for i in range(1,5)],
                                      enrollment_id=raw_input('Enrollment: '),
                                      password=raw_input('Password: ') or SETTINGS['default_password'])
            if certificate.is_bound():
                if file_storage.check_exist(certificate) or db_storage.check_exist(certificate):
                    print "\tThis certificate is already exist in file system and/or database"
                else:
                    file_storage.save(certificate)
                    db_storage.save(certificate)
                    count += 1
                ask = raw_input('Add new one? (y/n): ') == 'y'
            else:
                print "\tInvalid input, try again"
        return count

    def command_report(self):
        db_storage = CertificateDBStorage(db=SETTINGS['db'])
        reporter = Reporter(db_storage)
        report_rows, total = reporter.generate_report()
        week_start, week_end = get_current_week()

        report_rows.insert(0, ['Date obtained', 'E-mail', 'Password', 'Enrollment ID', 'Answers to secret questions'])
        return report_rows, week_start, week_end, total

    def command_delete(self):
        email = raw_input("Please enter E-mail: ")

        db_storage = CertificateDBStorage(db=SETTINGS['db'])
        file_storage = CertificateFileStorage(store_path=SETTINGS['store_path'])

        exist = db_storage.check_exist(Certificate(email=email))
        if not exist:
            print "No certificates with E-mail '%s' found." % id_num
            return

        if raw_input('Are you sure that you want to delete the certificate? (y/n): ') == 'y':
            certificate = db_storage.delete(email)
            file_storage.delete(email)
            print "Certificate with e-mail '%s' deleted successfully." % email
