"""Infrastructure to add and consume functionality"""
import collections
import copy
import logging
import sys
import types
import typing
import itertools

__all__ = ['register_functionality', 'register_functionality_in_all_imported_modules',
           'get_contributed_functionality', 'call_app_composing_function']

log = logging.getLogger(__name__)

# The main API functionality
_registered_functionality: {str: list} = collections.defaultdict(list)


def register_functionality(module: types.ModuleType):
    """Registers all declared functionality"""
    for attr in dir(module):
        if attr.startswith('MARA_'):
            items = getattr(module, attr)
            assert (callable(items) or isinstance(items, typing.Iterable))
            log.debug("Registered '%s' in module '%s'", attr, module.__name__)
            _registered_functionality[attr].append((module, items))


def get_contributed_functionality(name: str) -> typing.Iterable:
    """Gets the contributed functionality for one MARA_ variable"""
    all_items = _registered_functionality[name]
    for module, items in all_items:
        if callable(items):
            # a generator
            try:
                yield from zip(itertools.repeat(module), items())
            except Exception as e:
                # if we get a problem, just go over it to not stall the whole app
                log.exception(e)
        else:
            # lists and so on
            try:
                yield from zip(itertools.repeat(module), items)
            except Exception as e:
                log.exception(e)


def register_functionality_in_all_imported_modules():
    """ Imports all contributed mara functionality from any imported modules

    For compatibility with earlier versions of mara_app"""
    for name, module in copy.copy(sys.modules).items():
        register_functionality(module)


def call_app_composing_function():
    """Finds and calls the app composing function

    Tries to import the Module returned by the
    `default_app_module()` (default: app.app) and then call the
    `compose_mara_app()` function in that module, if it exists.
    """
    import importlib
    from .config import default_app_module
    app_module_name = default_app_module()
    try:
        app = importlib.import_module(app_module_name)
    except ModuleNotFoundError:
        msg = f"MARA_APP ({app_module_name}) is not an importable module."
        raise RuntimeError(msg) from None
    if not hasattr(app, 'compose_mara_app'):
        log.error("MARA_APP (%s) has no 'compose_mara_app() function.", app_module_name)
        # this is still recoverable as someone might have just did all the registering on import
        return
    compose_mara_app = getattr(app, 'compose_mara_app')
    log.debug("About to call '%s.compose_mara_app()'", app_module_name)
    try:
        compose_mara_app()
    except BaseException as e:
        msg = "Calling '%s.compose_mara_app()' resulted in an exception"
        raise RuntimeError(msg) from e
    log.debug("Finished '%s.compose_mara_app()'", app_module_name)
    return
