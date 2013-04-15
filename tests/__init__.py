# -*- coding: utf-8 -*-

'''

	apptools2: testsuite
	-------------------------------------------------
	|												|	
	|	`apptools.tests`							|
	|												|
	|	a suite of unit and integration testing 	|
	|	tools and test cases for apptools and		|
	|	encapsulating apps.							|
	|												|	
	-------------------------------------------------
	|	authors:									|
	|		-- sam gammon (sam@momentum.io)			|
	-------------------------------------------------	
	|	changelog:									|
	|		-- apr 1, 2013: initial draft			|
	-------------------------------------------------

'''

# Base Imports
import webapp2
import unittest

# App Engine API Imports
try:
	from google.appengine.ext import db

except ImportError as e:
	_APPENGINE = False

else:  # pragma: no cover
	_APPENGINE = True
	from google.appengine.ext import testbed
	from google.appengine.api import memcache

	## Constants
	_APPENGINE_SERVICE_BINDINGS = {
		'mail': 'mail',
		'user': 'user',
		'xmpp': 'xmpp',
		'images': 'images',
		'channel': 'channel',
		'urlfetch': 'urlfetch',
		'memcache': 'memcache',
		'blobstore': 'blobstore',
		'taskqueue': 'taskqueue',
		'identity': 'app_identity',
		'capability': 'capability',
		'logservice': 'logservice',
		'datastore': 'datastore_v3'
	}
	_APPENGINE_SERVICES = frozenset(_APPENGINE_SERVICE_BINDINGS.keys())


## AppToolsTestCase - Parent class for AppTools and Application-level tests.
class AppToolsTestCase(unittest.TestCase):

	''' A test case compatible with vanilla WSGI or GAE. '''

	## == Testbed / APIs == ##
	testbed = None

	## == Request / Handler == ##
	path = '/'
	request = None
	handler = None

	## == Services / Flags == ##
	services = ('datastore', 'memcache', 'urlfetch')

	def setUp(self):

		''' Set up an App Engine testbed, with related tools. '''

		## Construct + activate testbed
		if _APPENGINE:  # pragma: no cover
			if hasattr(self, 'services') and len(self.services) > 0:
				self.testbed = testbed.Testbed()
				self.testbed.activate()

			## Construct stubs
			for service in self.services:
				if service in _APPENGINE_SERVICES:
					stub_init = '_'.join(['init', _APPENGINE_SERVICE_BINDINGS.get(service), 'stub'])
					if hasattr(self.testbed, stub_init):
						getattr(self.testbed, stub_init)()
					else:
						raise RuntimeError('Could not init API by the name of "%s".' % service)
				else:
					raise RuntimeError('Could not resolve API by the name of "%s".' % service)

		self.request = webapp2.Request.blank(self.path)

	def tearDown(self):

		''' Tear down App Engine testbed stuff. '''

		if _APPENGINE and self.testbed:  # pragma: no cover
			self.testbed.deactivate()


## AppTest - Test case that originates from a concrete App, making use of AppTools for testing.
class AppTest(AppToolsTestCase): pass


## AppToolsTest - Test case for a test that is part of AppTools.
class AppToolsTest(AppToolsTestCase): pass


## SampleTest - Example test case that uses the App Engine testbed.
class SampleTest(AppToolsTest):

	''' Sample test that demonstrates usage of AppToolsTest. '''

	def test_multiply(self):

		self.assertEqual((10 * 10), 100)
		return


## AppToolsTests - Gather AppTools testsuites.
AppToolsTests = unittest.TestSuite()
AppToolsTests.addTest(SampleTest('test_multiply'))
