import yaml
import os
import sqlite3
from datetime import datetime, timedelta

from terminaltables import AsciiTable

from certman.settings import SETTINGS


def format_questions(questions):
    result = ['question%s: "%s"\n' % (i, questions[i-1]) for i in range(1, len(questions) + 1)]
    return result


def get_current_week():
    today = datetime.now()
    start = today - timedelta(days = today.weekday())
    end = start + timedelta(days = 6)
    return start, end


class Certificate(object):
    def __init__(self, email, password, questions, enrollment_id):
        self.email = email
        self.password = password
        self.questions = questions
        self.enrollment_id = enrollment_id

    def is_bound(self):
        return True


class CertificateFileStorage(object):
    def __init__(self, store_path):
        self.store_path = store_path

    def save(self, certificate):
        new_path = os.path.join(os.path.dirname(self.store_path), certificate.email)
        os.mkdir(new_path)
        with open(new_path + '/credentials.yaml', 'w') as f:
            store_obj = {
                'certificate': certificate.__dict__
            }
            f.write(yaml.dump(store_obj, default_flow_style=False))

    def check_exist(self, certificate):
        new_path = os.path.join(os.path.dirname(self.store_path), certificate.email)
        return os.path.exists(new_path)


class CertificateDBStorage(object):
    def __init__(self, db):
        self.conn = sqlite3.connect(db)
        self.apply_schema()

    def apply_schema(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS certificates
            (id integer primary key, when_added date, email text, password text, enrollment_id text, questions text);''')
        self.conn.commit()

    def save(self, certificate):
        c = self.conn.cursor()
        params = {
            'email': certificate.email,
            'password': certificate.password,
            'enrollment_id': certificate.enrollment_id,
            'questions': ''.join(format_questions(certificate.questions))
        }
        c.execute("INSERT INTO certificates VALUES (NULL, date('now'), '%(email)s', '%(password)s', '%(enrollment_id)s', '%(questions)s');" % params)
        self.conn.commit()


class Reporter(object):
    def __init__(self, db_storage):
        self.conn = db_storage.conn
    
    def generate_report(self):
        c = self.conn.cursor()
        week_start, week_end = get_current_week()
        params = {
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': week_end.strftime('%Y-%m-%d')
        }
        c.execute("SELECT * FROM certificates WHERE when_added >= '%(start_date)s' AND when_added <= '%(end_date)s';" % params)
        certificates = c.fetchall()
        result = []
        for cert in certificates:
            row = []
            for val in cert:
                row.append(unicode(val))

            result.append(row)

        total = len(certificates)
        return result, total




class Manager(object):
    COMMANDS = (
        ('addcert', 'add new certificate today'),
        ('report', 'generate this week report'),
        ('exit', 'exit')
    )

    def print_banner(self):
        print "Certificates Manager v.0.1"
        print "Builds.io Team. This is proprietary software."
        print
        print "Send bugs to: <ya.na.pochte@gmail.com> Vladimir Ignatev"
        print "==="

    def print_help(self):
        for command in self.COMMANDS:
            print "%s - %s" % command

    def input(self):
        user_input = ''
        while not user_input:
            user_input = raw_input('> ').strip().lower()

        return user_input

    def run(self):
        self.print_banner()
        self.print_help()
        
        while True:
            command = self.input()

            if command == 'addcert':
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
                        if file_storage.check_exist(certificate):
                            print "\t This certificate is already exist in file system"
                            ask = raw_input('Add new one? (y/n): ') == 'y'
                        else:
                            file_storage.save(certificate)
                            db_storage.save(certificate)
                            count += 1
                            ask = raw_input('Add new one? (y/n): ') == 'y'
                    else:
                        print "\tInvalid input, try again"

                print "Successfully added %s certificates" % count

            elif command == 'report':
                db_storage = CertificateDBStorage(db=SETTINGS['db'])
                reporter = Reporter(db_storage)
                certificates, total = reporter.generate_report()
                week_start, week_end = get_current_week()

                certificates.insert(0, ['# ID', 'Date obtained', 'E-mail', 'Password', 'Enrollment ID', 'Answers to secret questions'])

                table = AsciiTable(certificates, 'Certificates obtained %s-%s' % (week_start, week_end))
                table.outer_border = False
                print table.table
                print
                print "Total certificates obtained: %s" % total
            elif command == 'exit':
                return 0
            else:
                pass


