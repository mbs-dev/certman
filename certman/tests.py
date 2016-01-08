#!coding: utf-8
import unittest
import datetime
import tempfile
import shutil
import os
import yaml

from freezegun import freeze_time

from certman.manager import Certificate, CertificateFileStorage, \
 CertificateDBStorage, Reporter, Manager, get_current_week

class TestCertificate(unittest.TestCase):
    def test_certificate_should_bound(self):
        good_certificate = Certificate(
            email='someemail@mail.ru',
            password='somepassword',
            questions='...lot of text...',
            enrollment_id='123ENROLLE'
            )

        self.assertTrue(good_certificate.is_bound())

    def test_certificate_with_bad_email_shouldnt_bound(self):
        bad_certificate = Certificate(
            email='not an email @ all',
            password='somepassword',
            questions='...lot of text...',
            enrollment_id='123ENROLLE'
            )

        self.assertFalse(bad_certificate.is_bound())

    def test_certificate_shouldnt_bound_if_email_is_empty(self):
        bad_certificate = Certificate(
            email='',
            password='somepassword',
            questions='...lot of text...',
            enrollment_id='123ENROLLE'
            )

        self.assertFalse(bad_certificate.is_bound())

    def test_certificate_shouldnt_bound_if_password_is_empty(self):
        bad_certificate = Certificate(
            email='someemail@mail.ru',
            password='',
            questions='...lot of text...',
            enrollment_id='123ENROLLE'
            )

        self.assertFalse(bad_certificate.is_bound())

    def test_certificate_shouldnt_bound_if_questions_is_empty(self):
        bad_certificate = Certificate(
            email='someemail@mail.ru',
            password='somepassword',
            enrollment_id='123ENROLLE',
            questions=''
            )

        self.assertFalse(bad_certificate.is_bound())

    def test_certificate_shouldnt_bound_if_enrollment_is_empty(self):
        bad_certificate = Certificate(
            email='someemail@mail.ru',
            password='somepassword',
            questions='...lot of text...',
            enrollment_id=''
            )

        self.assertFalse(bad_certificate.is_bound())


class TestUtils(unittest.TestCase):
    @freeze_time("2016-01-07")
    def test_get_current_week_is_calendar_week(self):
        start, end = get_current_week()
        self.assertEqual(datetime.datetime(year=2016, month=1, day=4), start)
        self.assertEqual(datetime.datetime(year=2016, month=1, day=10), end)

    @freeze_time("2016-01-04")
    def test_get_current_week_is_calendar_week_top_boundary(self):
        start, end = get_current_week()
        self.assertEqual(datetime.datetime(year=2016, month=1, day=4), start)
        self.assertEqual(datetime.datetime(year=2016, month=1, day=10), end)

    @freeze_time("2016-01-10")
    def test_get_current_week_is_calendar_week_top_boundary(self):
        start, end = get_current_week()
        self.assertEqual(datetime.datetime(year=2016, month=1, day=4), start)
        self.assertEqual(datetime.datetime(year=2016, month=1, day=10), end)


class TestCertificateFileStorage(unittest.TestCase):
    def setUp(self):
        self.store_path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.store_path)

    def createValidCertificate(self):
        return Certificate(email='testemail@mail.ru',
                           password='default_password',
                           enrollment_id='123abc',
                           questions=['answer1', 'answer2', 'answer3']
                           )

    def assertYamlIsCorrect(self, path, certificate):
        with open(path, 'r') as f:
            y = yaml.load(f)
            assert y['certificate']['email'] == certificate.email
            assert y['certificate']['enrollment_id'] == certificate.enrollment_id
            assert y['certificate']['password'] == certificate.password
            assert y['certificate']['questions'] == certificate.questions
            assert y['certificate']['date_obtained'] == certificate.date_obtained

    @freeze_time("2016-01-07")
    def test_should_save_certificate_credentials(self):
        # Given
        storage = CertificateFileStorage(store_path=self.store_path)
        certificate = self.createValidCertificate()

        # When
        storage.save(certificate)

        # Then
        self.assertTrue(os.path.isdir(os.path.join(self.store_path, 'testemail@mail.ru')))
        self.assertTrue(os.path.isfile(os.path.join(self.store_path, 'testemail@mail.ru', 'credentials.yaml')))
        self.assertYamlIsCorrect(os.path.join(self.store_path, 'testemail@mail.ru', 'credentials.yaml'), certificate)

    def test_should_delete_certificate_dir(self):
        # Given
        storage = CertificateFileStorage(store_path=self.store_path)
        certificate = self.createValidCertificate()

        # When
        storage.save(certificate)
        self.assertTrue(os.path.isdir(os.path.join(self.store_path, 'testemail@mail.ru')))

        # Then
        storage.delete(certificate.email)
        self.assertFalse(os.path.isdir(os.path.join(self.store_path, 'testemail@mail.ru')))

    def test_check_exist_should_be_true(self):
        # Given
        storage = CertificateFileStorage(store_path=self.store_path)
        certificate = self.createValidCertificate()

        # When
        storage.save(certificate)

        # Then
        self.assertTrue(storage.check_exist(certificate))

    def test_check_exist_should_be_false(self):
        # Given
        storage = CertificateFileStorage(store_path=self.store_path)
        certificate = self.createValidCertificate()
        # When
        pass

        # Then
        self.assertFalse(storage.check_exist(certificate))

    def test_check_file_storage_deals_with_trailing_slash(self):
        # Given
        path_with_trailing_slash = os.path.join(self.store_path, '')
        self.assertTrue(path_with_trailing_slash[-1] == '/' or path_with_trailing_slash[-1] == '\\')

        storage = CertificateFileStorage(store_path=path_with_trailing_slash)
        certificate = self.createValidCertificate()

        self.assertFalse(storage.check_exist(certificate))
        storage.save(certificate)
        self.assertTrue(storage.check_exist(certificate))
        storage.delete(certificate.email)
        self.assertFalse(storage.check_exist(certificate))


class TestCertificateDBStorage(unittest.TestCase):
    def setUp(self):
        _, self.db_file = tempfile.mkstemp()

    def tearDown(self):
        os.remove(self.db_file)

    def createValidCertificate(self, email=None, date_obtained=None):
        return Certificate(email=email or 'testemail@mail.ru',
                           password='default_password',
                           enrollment_id='123abc',
                           questions=['answer1', 'answer2', 'answer3'],
                           date_obtained=date_obtained or datetime.date.today()
                           )

    @freeze_time("2016-01-07")
    def test_should_save_certificate_credentials(self):
        # Given
        storage = CertificateDBStorage(self.db_file)
        certificate = self.createValidCertificate()

        # When
        storage.save(certificate)

        # Then
        from_db = storage.get_by_email('testemail@mail.ru')
        self.assertIsNotNone(from_db)
        self.assertEqual(from_db.email, certificate.email)
        self.assertEqual(from_db.password, certificate.password)
        self.assertEqual(from_db.enrollment_id, certificate.enrollment_id)
        self.assertEqual(from_db.questions, certificate.questions)
        self.assertEqual(from_db.date_obtained, certificate.date_obtained)

    def test_parse_questions_format_questions(self):
        # Given
        questions = ['Job name? some answer1', 'You dad name? some answer2',
                     'EIN of your spurse? some answer3']

        # When
        formatted = CertificateDBStorage.format_questions(questions)

        # Then
        self.assertEqual(CertificateDBStorage.parse_questions(formatted), questions)

    def test_check_exist_should_be_true(self):
        # Given
        storage = CertificateDBStorage(self.db_file)
        certificate = self.createValidCertificate()

        # When
        storage.save(certificate)

        # Then
        self.assertTrue(storage.check_exist(certificate))

    def test_check_exist_should_be_false(self):
        # Given
        storage = CertificateDBStorage(self.db_file)
        certificate = self.createValidCertificate()

        # When
        pass

        # Then
        self.assertFalse(storage.check_exist(certificate))

    def test_should_delete_certificate(self):
        # Given
        storage = CertificateDBStorage(self.db_file)
        certificate = self.createValidCertificate()

        # When
        self.assertFalse(storage.check_exist(certificate))
        storage.save(certificate)
        self.assertTrue(storage.check_exist(certificate))
        storage.delete(certificate.email)

        # Then
        self.assertFalse(storage.check_exist(certificate))

    def test_should_select_all_certificates_by_date(self):
        # Given
        storage = CertificateDBStorage(self.db_file)
        certificate1 = self.createValidCertificate(email='first@mail.ru')
        certificate2 = self.createValidCertificate(email='second@mail.ru')

        # When
        storage.save(certificate1)
        storage.save(certificate2)
        certificates = [c for c in storage.get_by_date(datetime.datetime.now() - datetime.timedelta(days=1), datetime.datetime.now())]

        # Then
        self.assertEqual(len(certificates), 2)
        self.assertEqual(certificates, [certificate1, certificate2])

    def test_should_select_zero_certificates_by_date(self):
        # Given
        storage = CertificateDBStorage(self.db_file)
        certificate1 = self.createValidCertificate(email='first@mail.ru')
        certificate2 = self.createValidCertificate(email='second@mail.ru')

        past_start = datetime.datetime.now() - datetime.timedelta(days=11)
        past_end = datetime.datetime.now() - datetime.timedelta(days=10)
        future_start = datetime.datetime.now() + datetime.timedelta(days=1)
        future_end = datetime.datetime.now() + datetime.timedelta(days=10)

        # When
        storage.save(certificate1)
        storage.save(certificate2)

        certificates_in_past = [c for c in storage.get_by_date(past_start, past_end)]
        certificates_in_future = [c for c in storage.get_by_date(future_start, future_end)]

        # Then
        self.assertEqual(len(certificates_in_future), 0)
        self.assertEqual(len(certificates_in_past), 0)





if __name__=='__main__':
    unittest.main()
