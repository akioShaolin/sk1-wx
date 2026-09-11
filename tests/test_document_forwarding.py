# -*- coding: utf-8 -*-
"""Real Python 2 sender/receiver with binary I/O; GUI services are stubbed."""
import os
import shutil
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def module(name, **attrs):
    result = types.ModuleType(name)
    result.__dict__.update(attrs)
    return result


@unittest.skipUnless(sys.version_info[0] == 2,
                     'Real application receiver requires Python 2 byte strings')
class ForwardingTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp().decode(sys.getfilesystemencoding())
        self.cfg = os.path.join(self.root, '.config', 'sk1-wx')
        os.makedirs(self.cfg)
        self.socket = os.path.join(self.cfg, 'socket')
        self.lock = os.path.join(self.cfg, 'lock')
        with open(self.lock, 'wb') as fp:
            fp.write(b'\n')
        self.opened = []
        self.raised = []
        self.payload = None

        # Bundled fsutils.upath decodes UTF-8 bytes on Windows; uopen uses
        # the real builtin open, including its strict binary write behavior.
        def upath(path):
            return path if isinstance(path, unicode) else path.decode('utf-8')

        fsutils = module('uc2.utils.fsutils',
                         uopen=lambda path, mode: open(upath(path), mode),
                         exists=lambda path: os.path.exists(upath(path)),
                         remove=lambda path: os.remove(upath(path)))
        stubs = {'uc2': module('uc2', _=lambda value: value),
                 'uc2.utils': module('uc2.utils', fsutils=fsutils),
                 'wal': module('wal')}
        previous = dict((name, sys.modules.get(name)) for name in
                        list(stubs) + ['sk1'])
        try:
            sys.modules.update(stubs)
            self.sender = module('sk1')
            filename = os.path.join(ROOT, 'src', 'sk1', '__init__.py')
            with open(filename, 'rb') as fp:
                exec(compile(fp.read(), filename, 'exec'), self.sender.__dict__)
            self.sender.config = module('config', app_server=True)
            self.sender.events = module('events')
            sys.modules['sk1'] = self.sender
            receiver = self.receiver = module('receiver')
            filename = os.path.join(ROOT, 'src', 'sk1', 'app_fsw.py')
            with open(filename, 'rb') as fp:
                exec(compile(fp.read(), filename, 'exec'), receiver.__dict__)
        finally:
            for name, value in previous.items():
                if value is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value
        self.watcher = receiver.AppFileWatcher.__new__(receiver.AppFileWatcher)
        self.watcher.socket = self.socket.encode('utf-8')
        self.watcher.lock = self.lock.encode('utf-8')
        self.watcher.app = module('app', open=self.opened.append)
        self.watcher.mw = module('mw', raise_window=lambda: self.raised.append(True))
        # Replace only this module's references, never global sys/time.
        self.sender.sys = module('sys', argv=[], exit=sys.exit)
        self.sender.time = module('time', sleep=self.consume)

    def tearDown(self):
        shutil.rmtree(self.root)

    def consume(self, seconds):
        self.assertEqual(seconds, 2)
        with open(self.socket, 'rb') as fp:
            self.payload = fp.read()
        self.watcher.on_timer()

    def forward(self, names):
        paths = []
        expected = []
        for name in names:
            path = os.path.join(self.root, name.decode('utf-8')
                                if isinstance(name, str) else name)
            parent = os.path.dirname(path)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            with open(path, 'wb') as fp:
                fp.write(b'transport fixture')
            wire_path = path.encode('utf-8')
            paths.append(wire_path if isinstance(name, str) else path)
            expected.append(wire_path)
        self.sender.sys.argv = ['sk1'] + paths
        with self.assertRaises(SystemExit) as stopped:
            self.sender.check_server(self.root.encode('utf-8'))
        self.assertEqual(stopped.exception.code, 0)
        self.assertEqual(self.payload, b''.join(p + b'\n' for p in expected))
        self.assertEqual(self.opened, expected)
        self.assertTrue(all(type(p) is str for p in self.opened))
        self.assertEqual(self.raised, [True])
        self.assertFalse(os.path.exists(self.socket))
        self.assertTrue(os.path.exists(self.lock))

    def test_unicode_accented_filename(self):
        self.forward([u'B ação.sk2'])

    def test_unicode_parent_and_spaces(self):
        self.forward([u'pasta ação com espaços/B ação.sk2'])

    def test_unicode_outside_codepage_transport(self):
        self.forward([u'测试.sk2'])

    def test_utf8_bytes(self):
        self.forward([u'B ação.sk2'.encode('utf-8')])

    def test_ascii_bytes(self):
        self.forward([b'A with spaces.sk2'])

    def test_multiple_ordered_paths(self):
        self.forward([u'B ação.sk2', b'A with spaces.sk2',
                      u'pasta ação/测试.sk2', u'bytes ação.sk2'.encode('utf-8')])


if __name__ == '__main__':
    unittest.main()
