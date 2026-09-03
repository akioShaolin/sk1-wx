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
APPLICATION = os.path.join(ROOT, 'src', 'sk1', 'application.py')


class DummyBase(object):
    pass


class DummyApplication(object):
    pass


class DummyUCApplication(object):
    pass


class Config(object):
    save_dir = '/save'


class Events(types.ModuleType):
    DOC_SAVED = 'doc-saved'
    APP_STATUS = 'app-status'

    def __init__(self):
        types.ModuleType.__init__(self, 'sk1.events')
        self.emitted = []

    def emit(self, *args):
        self.emitted.append(args)


class FsUtils(types.ModuleType):
    def __init__(self):
        types.ModuleType.__init__(self, 'uc2.utils.fsutils')
        self.existing = set(['/docs', '/save'])

    def exists(self, path):
        return path in self.existing


class Dialogs(types.ModuleType):
    def __init__(self):
        types.ModuleType.__init__(self, 'sk1.dialogs')
        self.save_path = ''
        self.errors = []

    def get_save_file_name(self, *args, **kwargs):
        return self.save_path

    def error_dialog(self, *args, **kwargs):
        self.errors.append(args)


class Logger(object):
    def __init__(self):
        self.errors = []

    def error(self, *args):
        self.errors.append(args)


def module(name, **attrs):
    ret = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(ret, key, value)
    return ret


def load_application():
    events = Events()
    dialogs = Dialogs()
    fsutils = FsUtils()
    config = Config()

    sk1 = module('sk1', __path__=[],
                 _=lambda value: value, config=config, events=events,
                 modes=module('sk1.modes'), dialogs=dialogs,
                 appconst=module('sk1.appconst', SAVED=2),
                 app_plugins=module('sk1.app_plugins'),
                 app_actions=module('sk1.app_actions'))
    wal = module('wal', Application=DummyApplication)
    uc2_events = module('uc2.events')
    uc2const = module('uc2.uc2const', SK2=1,
                      FORMAT_EXTENSION={1: ['sk2']})
    uc2 = module('uc2', __path__=[], events=uc2_events,
                 uc2const=uc2const, libimg=module('uc2.libimg'),
                 msgconst=module('uc2.msgconst'))

    stubs = {
        'sk1': sk1,
        'sk1.events': events,
        'sk1.dialogs': dialogs,
        'sk1.app_cms': module('sk1.app_cms', AppColorManager=DummyBase),
        'sk1.app_conf': module('sk1.app_conf', AppData=DummyBase),
        'sk1.app_fsw': module('sk1.app_fsw', AppFileWatcher=DummyBase),
        'sk1.app_history': module('sk1.app_history', AppHistoryManager=DummyBase),
        'sk1.app_insp': module('sk1.app_insp', AppInspector=DummyBase),
        'sk1.app_palettes': module('sk1.app_palettes', AppPaletteManager=DummyBase),
        'sk1.app_proxy': module('sk1.app_proxy', AppProxy=DummyBase),
        'sk1.app_stdout': module('sk1.app_stdout', StreamLogger=DummyBase),
        'sk1.clipboard': module('sk1.clipboard', AppClipboard=DummyBase),
        'sk1.document': module('sk1.document', __path__=[]),
        'sk1.document.presenter': module('sk1.document.presenter', SK1Presenter=DummyBase),
        'sk1.parts': module('sk1.parts', __path__=[]),
        'sk1.parts.artprovider': module('sk1.parts.artprovider', create_artprovider=lambda: None),
        'sk1.parts.mw': module('sk1.parts.mw', AppMainWindow=DummyBase),
        'sk1.pwidgets': module('sk1.pwidgets', font_cache_update=lambda: None),
        'wal': wal,
        'uc2': uc2,
        'uc2.events': uc2_events,
        'uc2.application': module('uc2.application',
                                  UCApplication=DummyUCApplication),
        'uc2.formats': module('uc2.formats', get_saver_by_id=lambda value: None,
                              get_loader=lambda value: None),
        'uc2.utils': module('uc2.utils', __path__=[], fsutils=fsutils,
                            mixutils=module('uc2.utils.mixutils')),
        'uc2.utils.fsutils': fsutils,
    }
    previous = {}
    for name, value in stubs.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = value
    try:
        if imp is not None:
            loaded = imp.load_source('tested_sk1_application', APPLICATION)
        else:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'tested_sk1_application', APPLICATION)
            loaded = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loaded)
    finally:
        for name in stubs:
            if previous[name] is None:
                del sys.modules[name]
            else:
                sys.modules[name] = previous[name]
    return loaded, events, dialogs, fsutils


class Document(object):
    def __init__(self, path, name=None, saved=False, save_error=None):
        self.doc_file = path
        self.doc_name = name or os.path.basename(path)
        self.saved = saved
        self.save_error = save_error
        self.save_calls = 0

    def save(self):
        self.save_calls += 1
        if self.save_error:
            raise self.save_error
        self.saved = True

    def set_doc_file(self, path, name=''):
        self.doc_file = path
        self.doc_name = name or os.path.basename(path)


class History(object):
    def __init__(self):
        self.entries = []

    def add_entry(self, *args):
        self.entries.append(args)


class Inspector(object):
    def is_doc_not_saved(self, doc):
        return not doc.saved


class SaveTests(unittest.TestCase):
    def setUp(self):
        application, self.events, self.dialogs, unused = load_application()
        self.app = application.SK1Application.__new__(application.SK1Application)
        self.log = Logger()
        application.LOG = self.log
        self.app.history = History()
        self.app.insp = Inspector()
        self.app.mw = object()
        self.app.appdata = module('appdata', app_name='sK1')
        self.backups = []
        self.app.make_backup = self.backups.append

    def test_save_active_document(self):
        doc = Document('/docs/active.sk2')
        self.app.current_doc = doc

        self.assertTrue(self.app.save())

        self.assertEqual(doc.save_calls, 1)
        self.assertEqual(self.backups, ['/docs/active.sk2'])
        self.assertEqual(self.app.history.entries, [('/docs/active.sk2', 2)])
        self.assertIn(('doc-saved', doc), self.events.emitted)

    def test_save_non_active_document_uses_its_own_path(self):
        active = Document('/docs/active.sk2')
        other = Document('/docs/other.sk2')
        self.app.current_doc = active

        self.assertTrue(self.app.save(other))

        self.assertEqual(active.save_calls, 0)
        self.assertEqual(other.save_calls, 1)
        self.assertEqual(self.backups, ['/docs/other.sk2'])
        self.assertEqual(self.app.history.entries, [('/docs/other.sk2', 2)])
        self.assertIs(self.app.current_doc, active)

    def test_save_non_active_document_failure_uses_its_own_path(self):
        active = Document('/docs/active.sk2')
        other = Document('/docs/other.sk2', save_error=IOError('save failed'))
        self.app.current_doc = active

        self.assertFalse(self.app.save(other))

        self.assertEqual(other.save_calls, 1)
        self.assertEqual(self.backups, ['/docs/other.sk2'])
        self.assertEqual(self.app.history.entries, [])
        self.assertNotIn(('doc-saved', other), self.events.emitted)
        self.assertIn('/docs/other.sk2', self.dialogs.errors[0][2])
        self.assertEqual(self.log.errors[0][1], '/docs/other.sk2')
        self.assertIs(self.app.current_doc, active)

    def test_save_all_uses_each_document_path_and_preserves_active(self):
        first = Document('/docs/first.sk2')
        second = Document('/docs/second.sk2')
        self.app.docs = [first, second]
        self.app.current_doc = second

        self.app.save_all()

        self.assertEqual(first.save_calls, 1)
        self.assertEqual(second.save_calls, 1)
        self.assertEqual(self.backups,
                         ['/docs/first.sk2', '/docs/second.sk2'])
        self.assertEqual(self.app.history.entries,
                         [('/docs/first.sk2', 2), ('/docs/second.sk2', 2)])
        self.assertIs(self.app.current_doc, second)

    def test_save_non_active_document_without_path_uses_save_as_for_it(self):
        active = Document('/docs/active.sk2')
        untitled = Document('', 'Untitled 1')
        self.app.current_doc = active
        self.dialogs.save_path = '/save/new.sk2'

        self.assertTrue(self.app.save(untitled))

        self.assertEqual(untitled.doc_file, '/save/new.sk2')
        self.assertEqual(untitled.save_calls, 1)
        self.assertEqual(active.save_calls, 0)
        self.assertEqual(self.backups, ['/save/new.sk2'])
        self.assertEqual(self.app.history.entries, [('/save/new.sk2', 2)])
        self.assertIn(('doc-saved', untitled), self.events.emitted)
        self.assertIs(self.app.current_doc, active)

    def test_cancel_save_as_for_non_active_document_preserves_active(self):
        active = Document('/docs/active.sk2')
        untitled = Document('', 'Untitled 1')
        self.app.current_doc = active
        self.dialogs.save_path = ''

        self.assertFalse(self.app.save(untitled))

        self.assertEqual(untitled.save_calls, 0)
        self.assertEqual(self.backups, [])
        self.assertEqual(self.app.history.entries, [])
        self.assertIs(self.app.current_doc, active)

    def test_save_as_failure_restores_non_active_document(self):
        active = Document('/docs/active.sk2')
        other = Document('', 'Untitled 1', save_error=IOError('save failed'))
        self.app.current_doc = active
        self.dialogs.save_path = '/save/new.sk2'

        self.assertFalse(self.app.save_as(other))

        self.assertEqual(other.doc_file, '')
        self.assertEqual(other.doc_name, 'Untitled 1')
        self.assertFalse(other.saved)
        self.assertEqual(self.backups, ['/save/new.sk2'])
        self.assertEqual(self.app.history.entries, [])
        self.assertNotIn(('doc-saved', other), self.events.emitted)
        self.assertIn('/save/new.sk2', self.dialogs.errors[0][2])
        self.assertIs(self.app.current_doc, active)

    def test_save_all_with_non_active_untitled_document(self):
        untitled = Document('', 'Untitled 1')
        active = Document('/docs/active.sk2')
        self.app.docs = [untitled, active]
        self.app.current_doc = active
        self.dialogs.save_path = '/save/untitled.sk2'

        self.app.save_all()

        self.assertEqual(untitled.save_calls, 1)
        self.assertEqual(active.save_calls, 1)
        self.assertEqual(self.backups,
                         ['/save/untitled.sk2', '/docs/active.sk2'])
        self.assertEqual(self.app.history.entries,
                         [('/save/untitled.sk2', 2),
                          ('/docs/active.sk2', 2)])
        self.assertIs(self.app.current_doc, active)


if __name__ == '__main__':
    unittest.main()
