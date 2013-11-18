# -*- coding: utf-8 -*-

__doc__ = ''' docs coming soon '''


# stdlib
import sys, os, argparse


## == Embedded Metaclass == ##
class Tool(object):

  ''' Meta parent class that applies an embedded metaclass to enforce/
      transform encapsulated objects into :py:mod:`argparse` directives. '''

  parser = None  # local parser for this tool
  commands = None  # subcommands to this tool
  arguments = None  # arguments for this tool

  class __metaclass__(type):

    ''' Bound utility metaclass that re-writes embedded comand classes
        on-the-fly, into :py:mod:`argparse`-provided objects. '''

    tree = {}  # command parser tree
    parsers = {}  # all encountered parsers

    def __new__(cls, name, bases, properties):

      ''' Check to see if we're initializing a new subcommand class,
          and if we are, construct the appropriate subparser.

          :param name: Target class name.
          :param bases: Target class bases.
          :param properties: Class dict properties.

          :raises RuntimeError: If invalid tool bindings are expressed
          in a meta-initialized class (for instance, an argument without
          a name).

          :returns: Initialized class, transformed into additional
          objects provided by :py:mod:`argparse`. '''

      # construct class regularly
      klass = super(cls, cls).__new__(cls, name, bases, properties)

      # initialize `Tool` regularly to apply this metaclass downwards
      if name is 'Tool': return klass

      _subtools, _arguments = [], []
      for key, value in properties.viewitems():

        # is it a list of arguments?
        if isinstance(value, (list, tuple)) and key is 'arguments':

          def _add_argument(_parser, _name, _config):
              _parser.add_argument(_name, **_config)

          for _name, config in value:
            _arguments.append(((_add_argument, _name, config)))

        # is it a subtool?
        elif isinstance(value, type) and issubclass(value, Tool):

          def _add_subparser(obj, subparsers):
            sub = subparsers.add_parser((getattr(obj, 'name') if hasattr(obj, 'name') else obj.__name__).lower(), **{
              'help': getattr(obj, '__doc__').strip() if hasattr(obj, '__doc__') and (getattr(obj, '__doc__') is not None) else None  ## bind helptext from __doc__
            })

            return sub

          _subtools.append((value, _add_subparser))

        elif not key.startswith('__'):
          # well those are the only two options
          raise RuntimeError('Attached item to `Tool` subclass that is not '
                             'an argument or subtool.')

      # add to registered parsers
      cls.parsers[name] = {
        'name': (properties['name'] if 'name' in properties else name).lower(),
        'description': properties['__doc__'] if '__doc__' in properties else None,
        'implementation': klass,
        'objects': {
          'subtools': _subtools,
          'arguments': _arguments
        }
      }

      return klass

    def consider(self, parser, parent=None):

      ''' Consider a new sub-parser and its parent. Accepts a ``parent``
          and ``parser`` and adjusts the local :py:attr:`self.tree` to
          properly reflect sub-tools.

          :param parser: ``ArgumentParser`` object to consider and merge
          into our tree.
          
          :param parent: Parent parser to this one. Defaults to ``None``,
          in which case ``parser`` is the top of the tree.

          :returns: Original parser object, via ``parser``. '''

      if parent not in self.tree: self.tree[parent] = []
      self.tree[parent].append(self)
      return parser

  def __init__(self, parser=None):

    ''' This initializer method is called at the tip of the toolchain
        tree (composed of :py:class:`Tool` classes) to start the process
        of initializing and constructing each :py:mod:`argparse` object.

        Execution cascades from the tip to sub- :py:class:`Tool`s, and
        then to arguments.

        :returns: ``None``, as this is an initializer method. '''

    # lookup local config
    config = self.__metaclass__.parsers[self.__class__.__name__]

    if not parser:
      # start top-level argument parser
      parser = argparse.ArgumentParser(prog=(self.name if hasattr(self, 'name') else self.__class__.__name__).lower(), description=__doc__)

    self.parser = parser  # assign local parser

    # local args
    for callable, flag, _config in config.get('objects', {}).get('arguments', []):
      callable(parser, flag, _config)  # initialize each argument

    # local subtools
    if config.get('objects', {}).get('subtools', []):
      commands = parser.add_subparsers(help='bundled tools')
      for impl, callable in config.get('objects', {}).get('subtools', []):
        subparser = callable(impl, commands)  # initialize each subtool
        setattr(self, (impl.name if hasattr(impl, 'name') else impl.__name__).lower(), impl(subparser))

  def __call__(self, arguments):

    ''' Begins dispatching execution from a set of parsed arguments,
        as the product of a :py:meth:`parser.parse_args()` call.

        :param arguments: :py:class:`argparse.Namespace` object,
        resulting from ``parser.parse_args()``.

        :returns: Unix return code, suitable for passing directly
        to ``sys.exit()``. '''

    return 0
