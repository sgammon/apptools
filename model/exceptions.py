# -*- coding: utf-8 -*-

"""
Model API: Exceptions

Holds core exceptions for the :py:mod:`apptools.model` API.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""


class AbstractConstructionFailure(NotImplementedError):
    message = "Cannot directly instantiate abstract class `%s`."


class AdapterException(RuntimeError):
    pass


class NoSupportedAdapters(AdapterException):
    message = "No valid model adapters found."


class InvalidExplicitAdapter(AdapterException):
    message = "Requested model adapter \"%s\" could not be found or is not supported in this environment."


class InvalidKey(TypeError):
    message = "Cannot set model key to invalid type \"%s\" (for value \"%s\"). Expected `basestring`, `tuple` or `%s`."


class UndefinedKey(InvalidKey):
    message = "Could not operate on undefined key (value: \"%s\", kwargs: \"%s\")."


class MultipleKeyValues(TypeError):
    message = "Cannot merge multiple key values/formats in `%s._set_key`. (got: value(%s), formats(%s))."


class MultipleKeyFormats(TypeError):
    message = "Cannot provide multiple formats to `_set_key` (got: \"%s\")."


class PersistedKey(AttributeError):
    message = "Cannot set property \"%s\" of an already-persisted key."


class InvalidAttributeWrite(AttributeError):
    message = "Cannot %s property \"%s\" of model \"%s\" before instantiation."


class InvalidKeyAttributeWrite(AttributeError):
    message = "Cannot %s property \"%s\" of key \"%s\" before instantiation."


class InvalidAttribute(AttributeError):
    message = "Cannot %s nonexistent data property \"%s\" of model class \"%s\"."


class InvalidItem(KeyError):
    message = "Cannot %s nonexistent data item \"%s\" of model class \"%s\"."


class KeySchemaMismatch(InvalidKey):
    message = "Key type \"%s\" takes a maximum of %s positional arguments to populate the format \"%s\"."


class ValidationError(ValueError):
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

