"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import SimpleTestCase
#from tapiriik.testing.testtools import TestTools, TapiriikTestCase
from tapiriik.database import db


class SimpleTest(SimpleTestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

    def test_home_page(self):
        print('******************test_home_page()**********************')
        # send GET request.
        response = self.client.get('/')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)
        #self.assertTemplateUsed(response, 'dept_emp/home_page.html')

    def test_faq_page(self):
        print('******************test_faq_page()**********************')
        # send GET request.
        response = self.client.get('/faq')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)

    def test_privacy_page(self):
        print('******************test_privacy_page()**********************')
        # send GET request.
        response = self.client.get('/privacy')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)

    def test_credits_page(self):
        print('******************test_credits_page()**********************')
        # send GET request.
        response = self.client.get('/credits')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)

    def test_contact_page(self):
        print('******************test_contact_page()**********************')
        # send GET request.
        response = self.client.get('/contact')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)


    def test_diag_page(self):
        print('******************test_diag_page()**********************')
        # send GET request.
        response = self.client.get('/diagnostics')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 301)

    def test_status_page(self):
        print('******************test_status_page()**********************')
        # send GET request.
        response = self.client.get('/status')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 301)

    def test_statuselb_page(self):
        print('******************test_statuselb_page()**********************')
        # send GET request.
        response = self.client.get('/status_elb/')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)

    def test_404_page(self):
        print('******************test_404_page()**********************')
        # send GET request.
        response = self.client.get('/abracadabra')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 404)

    def test_securitytxt_page(self):
        print('******************test_security_page()**********************')
        # send GET request.
        response = self.client.get('/.well-known/security.txt')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)



'''
class ViewTest(TestCase):
    def test_home_page(self):
        print('******************test_home_page()**********************')
        # send GET request.
        response = self.client.get('/dept_emp/')
        print('Response status code : ' + str(response.status_code))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dept_emp/home_page.html')
'''
