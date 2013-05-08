# -*- coding: utf-8 -*-

'''

    apptools2: testsuite
    -------------------------------------------------
    |                                               |
    |   `apptools.tests`                            |
    |                                               |
    |   a suite of unit and integration testing     |
    |   tools and test cases for apptools and       |
    |   encapsulating apps.                         |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# Base Imports
import sys
import webapp2
import unittest

# App Engine API Imports
try:
    from google.appengine.ext import testbed

except ImportError as e:
    _APPENGINE = False

else:  # pragma: no cover
    _APPENGINE = True

    ## GAE Constants
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


# Builtin Test Paths
_TEST_PATHS = [
    'apptools.tests.test_model'  # Model API testsuite
]


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
                    stub_init = '_'.join([
                        'init',
                        _APPENGINE_SERVICE_BINDINGS.get(service),
                        'stub'
                    ])
                    if hasattr(self.testbed, stub_init):
                        getattr(self.testbed, stub_init)()
                    else:
                        raise RuntimeError('Could not init API "%s".' % service)
                else:
                    raise RuntimeError('Could not resolve API "%s".' % service)

        self.request = webapp2.Request.blank(self.path)

    def tearDown(self):

        ''' Tear down App Engine testbed stuff. '''

        if _APPENGINE and self.testbed:  # pragma: no cover
            self.testbed.deactivate()


## AppTest - Test case that originates from a concrete App.
class AppTest(AppToolsTestCase):
    pass


## AppToolsTest - Test case for a test that is part of AppTools.
class AppToolsTest(AppToolsTestCase):
    pass


## SampleTest - Example test case that uses the App Engine testbed.
class SampleTest(AppToolsTest):

    ''' Sample test that demonstrates usage of AppToolsTest. '''

    def test_multiply(self):

        self.assertEqual((10 * 10), 100)
        return


## `load_test_module` - Load a single testsuite module.
def load_test_module(path):

    ''' __main__ testing entrypoint for `apptools.model`. '''

    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(path))
    return suite


## `load_testsuite` - Gather AppTools testsuites.
def load_testsuite(paths=None):

    ''' __main__ entrypoint '''

    AppToolsTests = unittest.TestSuite()
    AppToolsTests.addTest(SampleTest('test_multiply'))

    if paths is None:
        paths = _TEST_PATHS[:]

    for path in paths:
        AppToolsTests.addTest(load_test_module(path))

    return AppToolsTests


## `run_testsuite` - Run a suite of tests loaded via `_load_testsuite`.
def run_testsuite(suite=None):

    ''' Optionally allow switching between XML or text output, if supported. '''

    if suite is None:
        suite = load_testsuite()
    if len(sys.argv) > 1:
        args = sys.argv[1:]  # slice off invocation

        if len(args) == 2:  # <format>, <output location>
            format, output = tuple(args)

            if format.lower().strip() == 'xml':
                try:
                    import xmlrunner
                except ImportError:
                    print "ERROR! XML testrunner (py module `xmlrunner`) could not be imported. Please run in text-only mode."
                    exit(1)
                xmlrunner.XMLTestRunner(output=output).run(suite)

            elif format.lower().strip() == 'text':
                return unittest.TestRunner(verbosity=5, output=output).run(suite)
        else:
            return unittest.TestRunner(verbosity=5, output=output).run(suite)  # text mode with

    return unittest.TestRunner(verbosity=5).run(suite)


if __name__ == '__main__':  # pragma: no cover
    run_testsuite(load_testsuite())
