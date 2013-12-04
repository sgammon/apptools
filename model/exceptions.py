# -*- coding: utf-8 -*-

'''

    apptools model: exceptions

    holds core exceptions for the :py:mod:`apptools.model` API.

    :author: Sam Gammon <sam@momentum.io>
    :copyright: (c) momentum labs, 2013
    :license: The inspection, use, distribution, modification or implementation
              of this source code is governed by a private license - all rights
              are reserved by the Authors (collectively, "momentum labs, ltd")
              and held under relevant California and US Federal Copyright laws.
              For full details, see ``LICENSE.md`` at the root of this project.
              Continued inspection of this source code demands agreement with
              the included license and explicitly means acceptance to these terms.

'''

class Error(Exception): pass


class ModelException(Error):

    def __init__(self, *context):

        '''  '''

        self.message = self.message % context

    def __repr__(self):

        '''  '''

        return self.message

    __str__ = __unicode__ = __repr__


class AbstractConstructionFailure(ModelException, NotImplementedError):
    message = "Cannot directly instantiate abstract class `%s`."


class AdapterException(ModelException, RuntimeError):
    pass


class NoSupportedAdapters(AdapterException):
    message = "No valid model adapters found."


class InvalidExplicitAdapter(AdapterException):
    message = "Requested model adapter \"%s\" could not be found or is not supported in this environment."


class InvalidKey(ModelException, TypeError):
    message = "Cannot set model key to invalid type \"%s\" (for value \"%s\"). Expected `basestring`, `tuple` or `%s`."


class UndefinedKey(InvalidKey):
    message = "Could not operate on undefined key (value: \"%s\", kwargs: \"%s\")."


class MultipleKeyValues(ModelException, TypeError):
    message = "Cannot merge multiple key values/formats in `%s._set_key`. (got: value(%s), formats(%s))."


class MultipleKeyFormats(ModelException, TypeError):
    message = "Cannot provide multiple formats to `_set_key` (got: \"%s\")."


class PersistedKey(ModelException, AttributeError):
    message = "Cannot set property \"%s\" of an already-persisted key."


class InvalidAttributeWrite(ModelException, AttributeError):
    message = "Cannot %s property \"%s\" of model \"%s\" before instantiation."


class InvalidKeyAttributeWrite(ModelException, AttributeError):
    message = "Cannot %s property \"%s\" of key \"%s\" before instantiation."


class InvalidAttribute(ModelException, AttributeError):
    message = "Cannot %s nonexistent data property \"%s\" of model class \"%s\"."


class InvalidItem(ModelException, KeyError):
    message = "Cannot %s nonexistent data item \"%s\" of model class \"%s\"."


class KeySchemaMismatch(InvalidKey):
    message = "Key type \"%s\" takes a maximum of %s positional arguments to populate the format \"%s\"."


class ValidationError(ModelException, ValueError):
    pass


class PropertyPolicyViolation(ValidationError):
    pass


class PropertyBasetypeViolation(ValidationError):
    pass


class PropertyRequired(PropertyPolicyViolation):
    message = "Property \"%s\" of Model class \"%s\" is marked as `required`, but was left unset."


class PropertyRepeated(PropertyPolicyViolation):
    message = "Property \"%s\" of Model class \"%s\" is marked as iterable, and cannot accept non-iterable values."


class PropertyNotRepeated(PropertyPolicyViolation):
    message = "Property \"%s\" of Model class \"%s\" is not marked as repeated, and cannot accept iterable values."


class InvalidPropertyValue(PropertyBasetypeViolation):
    message = "Property \"%s\" of Model class \"%s\" cannot accept value of type \"%s\" (was expecting type \"%s\")."

