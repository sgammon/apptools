# -*- coding: utf-8 -*-

"""
This module provides functionality to the :py:mod:`apptools` model layer
for querying across datastores and adapters that support the interface
:py:class:`IndexedModelAdapter`.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

__version__ = 'v2'

# stdlib
import abc

# apptools utils
from apptools.util import datastructures


## Globals / Constants
_TARGET_KEY = datastructures.Sentinel('KEY')

# Filter components
PROPERTY = datastructures.Sentinel('PROPERTY')
KEY_KIND = datastructures.Sentinel('KEY_KIND')
KEY_ANCESTOR = datastructures.Sentinel('KEY_ANCESTOR')

# Sort directions
ASCENDING = ASC = datastructures.Sentinel('ASCENDING')
DESCENDING = DSC = datastructures.Sentinel('DESCENDING')

# Query operators
EQUALS = EQ = datastructures.Sentinel('EQUALS')
NOT_EQUALS = NEQ = datastructures.Sentinel('NOT_EQUALS')
LESS_THAN = LST = datastructures.Sentinel('LESS_THAN')
LESS_THAN_EQUAL_TO = LSEQ = datastructures.Sentinel('LESS_THAN_EQUAL_TO')
GREATER_THAN = GRT = datastructures.Sentinel('GREATER_THAN')
GREATER_THAN_EQUAL_TO = GTEQ = datastructures.Sentinel('GREATER_THAN_EQUAL_TO')
CONTAINS = IN = datastructures.Sentinel('CONTAINS')
NOT_CONTAINS = NOT_IN = datastructures.Sentinel('NOT_CONTAINS')


## AbstractQuery
# Specifies the interface for an ``apptools`` model API query class.
class AbstractQuery(object):

    ''' Specifies base structure and interface for all
        apptools query classes. '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def filter(self, expression):

        ''' Add a filter to the active :py:class:`Query`
            at ``self``.

            :param expression: Filter expression to apply during query planning.
            :raises NotImplementedError: Always, as this method is abstract.
            :returns: ``self``, for chainability. '''

        raise NotImplementedError('`filter` is abstract and may not be invoked directly.')

    @abc.abstractmethod
    def sort(self, expression):

        ''' Add a sort directive to the active :py:class:`Query`
            at ``self``.

            :param expression: Sort expression to apply to the target result set.
            :raises NotImplementedError: Always, as this method is abstract.
            :returns: ``self``, for chainability. '''

        raise NotImplementedError('`sort` is abstract and may not be invoked directly.')

    @abc.abstractmethod
    def hint(self, directive):

        ''' Pass a hint to the query-planning subsystem for how
            this query could most efficiently be satisfied.

            :param expression: Hint expression to take into consideration.
            :raises NotImplementedError: Always, as this method is abstract.
            :returns: ``self``, for chainability. '''

        raise NotImplementedError('`hint` is abstract and may not be invoked directly.')


## Query
# Top-level specification class for a datastore query.
class Query(AbstractQuery):

    ''' Top-level class representing a specification for
        a query across data accessible to the apptools
        model layer, using an adapter that supports the
        :py:class:`IndexedModelAdapter` interface. '''

    kind = None  # model kind
    sorts = None  # sort directives
    config = None  # arbitrary config
    filters = None  # filter directives

    def __init__(self, kind=None, filters=None, sorts=None, **kwargs):

        ''' Initialize this :py:class:`Query`, assigning
            any properties/config passed in via ``kwargs``
            and such.

            :returns: Nothing, as this is an initializer. '''

        self.kind, self.filters, self.sorts, self.config = kind, filters or [], sorts or [], kwargs


## QueryComponent
# Abstract parent for components of a :py:class:`Query`.
class QueryComponent(object):

    ''' Top-level abstract class for a component of a
        :py:class:`Query`, which is usually an attached
        specification like a :py:class:`Filter` or
        :py:class:`Sort`. '''

    __metaclass__ = abc.ABCMeta

    value = None  # value to match
    target = None  # property to filter on
    operator = None  # operator selection


## Filter
# Expresses an individual filter in a :py:class:`Query`.
class Filter(QueryComponent):

    ''' Query component specification parent for a generic
        filter, used to traverse indexes and find entities
        to return that match. '''

    ## == Constants == ##
    PROPERTY = PROPERTY


## KeyFilter
# Expresses a filter that applies to an entity's :py:class:`Key`.
class KeyFilter(Filter):

    ''' Expresses a filter that applies to an entity's
        associated :py:class:`model.Key`, or one of the
        member components thereof. '''

    # == Constants == #
    KIND = KEY_KIND
    ANCESTOR = KEY_ANCESTOR


## Sort
# Expresses a sort directive to apply to the target resultset.
class Sort(QueryComponent):

    ''' Expresses a directive to sort resulting entities
        by a property in a given direction. '''

    ## == Constants == ##
    ASC = ASCENDING = ASC
    DSC = DESCENDING = DSC

    ## == State == ##
    direction = ASC
