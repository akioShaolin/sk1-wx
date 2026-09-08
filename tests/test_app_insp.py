# -*- coding: utf-8 -*-
import os
import sys
import types
import unittest

try:
    import imp
except ImportError:
    imp = None


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_INSP = os.path.join(ROOT, 'src', 'sk1', 'app_insp.py')


def module(name, **attrs):
    ret = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(ret, key, value)
    return ret


def load_app_inspector():
    stubs = {
        'sk1': module('sk1', __path__=[], modes=module('sk1.modes'),
                      config=module('sk1.config')),
        'uc2': module('uc2', __path__=[], uc2const=module('uc2.uc2const'),
                      sk2const=module('uc2.sk2const')),
    }
    previous = {}
    for name, value in stubs.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = value
    try:
        if imp is not None:
            loaded = imp.load_source('tested_sk1_app_insp', APP_INSP)
        else:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'tested_sk1_app_insp', APP_INSP)
            loaded = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loaded)
    finally:
        for name in stubs:
            if previous[name] is None:
                del sys.modules[name]
            else:
                sys.modules[name] = previous[name]
    return loaded.AppInspector


class Document(object):
    def __init__(self, saved):
        self.saved = saved


class Application(object):
    def __init__(self, states):
        self.docs = [Document(saved) for saved in states]


class AnyDocumentNotSavedTests(unittest.TestCase):
    @staticmethod
    def predicate(states):
        inspector_class = load_app_inspector()
        inspector = inspector_class(Application(states))
        return inspector.is_any_doc_not_saved()

    def test_no_documents(self):
        self.assertFalse(self.predicate([]))

    def test_one_saved_document(self):
        self.assertFalse(self.predicate([True]))

    def test_one_modified_document(self):
        self.assertTrue(self.predicate([False]))

    def test_multiple_saved_documents(self):
        self.assertFalse(self.predicate([True, True]))

    def test_saved_and_modified_documents(self):
        self.assertTrue(self.predicate([True, False, True]))

    def test_all_documents_modified(self):
        self.assertTrue(self.predicate([False, False]))


if __name__ == '__main__':
    unittest.main()
