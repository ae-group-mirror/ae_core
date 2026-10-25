""" unit and integration tests of the ae.core portion. """
import datetime
import importlib
import logging
import os
import pytest
import shutil
import sys
import threading

from conftest import delete_files
from functools import partial
from typing import Any, TextIO, cast
from unittest.mock import patch, MagicMock


import ae.paths                 # for patch tests of ae.paths.PATH_PLACEHOLDERS
import ae.core                  # for patch tests of ae.core.PATH_PLACEHOLDERS

from ae.base import (
    DATE_TIME_ISO,
    force_encoding, norm_path, os_path_dirname, os_path_isfile, os_path_isdir, os_path_join, os_path_splitext,
    read_file, write_file)
from ae.paths import PATH_PLACEHOLDERS, placeholder_path, coll_folders, Collector

# noinspection PyProtectedMember
from ae.core import (
    APP_KEY_SEP, DEBUG_LEVELS, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE,
    LOG_FILE_IDX_WIDTH, MAX_NUM_LOG_FILES,
    activate_multi_threading, _deactivate_multi_threading, debug_out, hide_dup_line_prefix, is_debug, is_verbose,
    _join_app_threads, main_app_instance, print_out, registered_app_names,
    temp_context_cleanup, temp_context_folders, temp_context_get_or_create, _temp_folders, verbose_out,
    AppBase, _PrintingReplicator)


__version__ = '3.6.9dev-test'   # used for automatic app version find tests


class TestHelpers:
    def test_debug_out(self, capsys, restore_app_env):
        app = AppBase()
        app.debug_level = DEBUG_LEVEL_VERBOSE

        debug_out('tst console output')

        out, err = capsys.readouterr()
        assert 'tst console output' in out
        assert err == ""

        app.debug_level = DEBUG_LEVEL_ENABLED

        debug_out('tst console output')

        out, err = capsys.readouterr()
        assert 'tst console output' in out
        assert err == ""

        app.debug_level = DEBUG_LEVEL_DISABLED

        debug_out('tst console output')

        out, err = capsys.readouterr()
        assert 'tst console output' not in out
        assert out == ""
        assert err == ""

    def test_hide_dup_line_prefix(self):
        l1 = "<t_s_t>"
        l2 = l1
        assert hide_dup_line_prefix(l1, l2) == " " * len(l2)
        l2 = l1 + l1
        assert hide_dup_line_prefix(l1, l2) == " " * len(l1) + l1
        assert hide_dup_line_prefix(l2, l1) == " " * len(l1)
        l2 = l1[:3] + l1
        assert hide_dup_line_prefix(l1, l2) == " " * 3 + l1

    def test_is_debug(self, restore_app_env):
        app = AppBase()
        app.debug_level = DEBUG_LEVEL_DISABLED

        assert not is_debug()

        app.debug_level = DEBUG_LEVEL_ENABLED

        assert is_debug()

        app.debug_level = DEBUG_LEVEL_VERBOSE

        assert is_debug()

    def test_is_verbose(self, restore_app_env):
        app = AppBase()
        app.debug_level = DEBUG_LEVEL_DISABLED

        assert not is_verbose()

        app.debug_level = DEBUG_LEVEL_ENABLED

        assert not is_verbose()

        app.debug_level = DEBUG_LEVEL_VERBOSE

        assert is_verbose()

    def test_print_out_basics(self, capsys):
        print_out()
        out, err = capsys.readouterr()
        assert out == '\n' and err == ''

        print_out(invalid_kwarg='ika')
        out, err = capsys.readouterr()
        assert 'ika' in out and err == ''

        us = chr(40960) + chr(1972) + chr(2013) + 'äöü'
        print_out(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert us in out and err == ''

        print_out(us, file=sys.stdout)
        print_out(us, file=sys.stderr)
        fna = 'print_out.txt'
        fhd = open(fna, 'w', encoding='ascii', errors='strict')
        print_out(us, file=fhd)
        fhd.close()
        assert delete_files(fna) == 1
        print_out(bytes(chr(0xef) + chr(0xbb) + chr(0xbf), encoding='utf-8'))
        out, err = capsys.readouterr()
        assert us in out
        assert us in err

    def test_print_out_err_cov(self, capsys):
        # print invalid/surrogate code point/char to force UnicodeEncodeError exception in print_out() (test coverage)
        us = chr(0xD801)
        print_out(us, 123456, encode_errors_def='strict')      # .. also coverage of not-str args
        out, err = capsys.readouterr()
        assert force_encoding(us) in out and '123456' in out and err == ''

        print_out('\r', 123456)     # coverage of processing output (not captured by pytest)
        out, err = capsys.readouterr()
        assert out == '' and err == ''

    def test_print_out_exception_cov(self, capsys):     # PyCharm-debugging doesn't work?!?!?
        with (patch('builtins.map', side_effect=ValueError("tst_value_err_exception")),
              patch('traceback.print_exc') as mock_print_exc):
            print_out('tst_exception_print_out')

        mock_print_exc.assert_called_once()
        out, err = capsys.readouterr()
        assert '...... in ae.core.print_out' in out
        assert 'tst_exception_print_out' in out

    def test_registered_app_names_empty(self):
        assert not registered_app_names()

    def test_registered_app_names_not_empty(self, restore_app_env):
        assert not registered_app_names()
        app = AppBase()
        assert len(registered_app_names()) == 1
        assert app.app_name == registered_app_names()[0]

    def test_verbose_out(self, capsys, restore_app_env):
        app = AppBase()
        app.debug_level = DEBUG_LEVEL_VERBOSE

        verbose_out('tst console output')

        out, err = capsys.readouterr()
        assert 'tst console output' in out
        assert err == ""

        app.debug_level = DEBUG_LEVEL_ENABLED

        verbose_out('tst console output')

        out, err = capsys.readouterr()
        assert 'tst console output' not in out
        assert out == ""
        assert err == ""

        app.debug_level = DEBUG_LEVEL_DISABLED

        verbose_out('tst console output')

        out, err = capsys.readouterr()
        assert 'tst console output' not in out
        assert out == ""
        assert err == ""


class TestJoinAppThreads:
    @pytest.fixture
    def main_thread(self):
        return threading.current_thread()

    def test_no_app_threads(self, main_thread):
        """ empty _APP_THREADS -> loop body never runs, deactivation still happens. """
        with patch('ae.core._APP_THREADS', {}), \
                patch('ae.core.threading.current_thread', return_value=main_thread), \
                patch('ae.core._deactivate_multi_threading') as deactivate_mock:
            _join_app_threads()

        deactivate_mock.assert_called_once()

    def test_skips_main_thread(self, main_thread):
        """ the main thread itself must be neither joined nor popped. """
        app_threads = {1: main_thread}
        with patch('ae.core._APP_THREADS', app_threads), \
                patch('ae.core.threading.current_thread', return_value=main_thread), \
                patch('ae.core.print_out') as print_out_mock, \
                patch('ae.core._deactivate_multi_threading') as deactivate_mock:
            _join_app_threads()

        print_out_mock.assert_not_called()
        assert app_threads == {1: main_thread}  # untouched
        deactivate_mock.assert_called_once()

    def test_joins_and_pops_thread_with_ident(self, main_thread):
        """ non-main thread with a resolved ident: joined, logged and removed from _APP_THREADS. """
        worker = MagicMock(spec=threading.Thread)
        worker.ident = 42
        worker.name = "worker"
        app_threads = {42: worker}

        with patch('ae.core._APP_THREADS', app_threads), \
                patch('ae.core.threading.current_thread', return_value=main_thread), \
                patch('ae.core.print_out') as print_out_mock, \
                patch('ae.core._LOGGER', "logger_sentinel"), \
                patch('ae.core._deactivate_multi_threading') as deactivate_mock:
            _join_app_threads(timeout=5.0)

        worker.join.assert_called_once_with(5.0)
        print_out_mock.assert_called_once()
        args, kwargs = print_out_mock.call_args
        assert "42" in args[0] or "42" in str(args[0])
        assert "worker" in args[0]
        assert kwargs.get('logger') == "logger_sentinel"
        assert 42 not in app_threads
        deactivate_mock.assert_called_once()

    def test_joins_but_does_not_pop_thread_without_ident(self, main_thread):
        """ ident becomes None (e.g. thread already finished/cleaned up) -> join still happens, no pop. """
        worker = MagicMock(spec=threading.Thread)
        worker.ident = None
        worker.name = "ghost"
        app_threads = {99: worker}

        with patch('ae.core._APP_THREADS', app_threads), \
                patch('ae.core.threading.current_thread', return_value=main_thread), \
                patch('ae.core.print_out'), \
                patch('ae.core._deactivate_multi_threading') as deactivate_mock:
            _join_app_threads()

        worker.join.assert_called_once_with(None)
        assert app_threads == {99: worker}  # not popped, since ident is None
        deactivate_mock.assert_called_once()

    def test_default_timeout_is_none(self, main_thread):
        """ calling without a timeout argument must join with timeout=None (blocking). """
        worker = MagicMock(spec=threading.Thread)
        worker.ident = 7
        worker.name = "worker"
        app_threads = {7: worker}

        with patch('ae.core._APP_THREADS', app_threads), \
                patch('ae.core.threading.current_thread', return_value=main_thread), \
                patch('ae.core.print_out'), \
                patch('ae.core._deactivate_multi_threading'):
            _join_app_threads()

        worker.join.assert_called_once_with(None)

    def test_iterates_in_reverse_insertion_order(self, main_thread):
        """ threads must be joined in reverse of _APP_THREADS insertion order. """
        worker1 = MagicMock(spec=threading.Thread, ident=1, name="w1")
        worker2 = MagicMock(spec=threading.Thread, ident=2, name="w2")
        app_threads = {1: worker1, 2: worker2}
        join_order = []
        worker1.join.side_effect = lambda timeout: join_order.append(1)
        worker2.join.side_effect = lambda timeout: join_order.append(2)

        with patch('ae.core._APP_THREADS', app_threads), \
                patch('ae.core.threading.current_thread', return_value=main_thread), \
                patch('ae.core.print_out'), \
                patch('ae.core._deactivate_multi_threading'):
            _join_app_threads()

        assert join_order == [2, 1]
        assert app_threads == {}

    def test_mixed_main_and_worker_threads(self, main_thread):
        """ a dict containing both the main thread and a worker: only the worker gets joined/popped. """
        worker = MagicMock(spec=threading.Thread, ident=5, name="worker")
        app_threads = {1: main_thread, 5: worker}

        with patch('ae.core._APP_THREADS', app_threads), \
                patch('ae.core.threading.current_thread', return_value=main_thread), \
                patch('ae.core.print_out'), \
                patch('ae.core._deactivate_multi_threading') as deactivate_mock:
            _join_app_threads()

        worker.join.assert_called_once_with(None)
        assert app_threads == {1: main_thread}  # main thread stays, worker popped
        deactivate_mock.assert_called_once()


class TestPrintingReplicator:
    def test_init(self):
        dso = _PrintingReplicator()
        assert dso.sys_out_obj is sys.stdout

        dso = _PrintingReplicator(sys_out_obj=sys.stdout)
        assert dso.sys_out_obj is sys.stdout

        dso = _PrintingReplicator(sys_out_obj=sys.stderr)
        assert dso.sys_out_obj is sys.stderr

    def test_flush_method_exists(self):
        dso = _PrintingReplicator()
        assert hasattr(dso, 'flush')
        assert callable(dso.flush)

    def test_write(self):
        lfn = 'ca_dup_sys_write_test.txt'
        try:
            lfo = open(lfn, 'w')
            dso = _PrintingReplicator(lfo)
            msg = 'test_ascii_message'
            dso.write(msg)
            lfo.close()
            assert read_file(lfn) == msg

            lfo = open(lfn, 'w', encoding='utf-8')
            dso = _PrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            assert read_file(lfn, encoding='utf-8') == msg

            lfo = open(lfn, 'w', encoding='ascii')
            dso = _PrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            assert read_file(lfn, encoding='ascii') == '\\ua000\\u07b4'

            lfo = open(lfn, 'w')
            dso = _PrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            with open(lfn) as f:
                assert f.encoding == 'UTF-8'
                assert f.read() == msg              # == '\ua000\u07b4'

        finally:
            assert delete_files(lfn) == 1


class TestAeLogging:
    def test_log_file_rotation_basics(self, restore_app_env):
        log_file = 'test_ae_base_log.log'
        try:
            app = AppBase('test_base_log_file_rotation')
            app.init_logging(log_file_name=log_file, log_file_size_max=.001)    # log file max size == 1 kB
            # not needed explicitly: app.log_file_check()
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):                   # full loop is creating 1 kB of log entries (16 * 64 bytes)
                    app.po("TestBaseLogEntry{: >26}{: >26}".format(idx, line_no))
            assert os_path_isfile(log_file)
        finally:
            assert delete_files(log_file, keep_ext=True) == MAX_NUM_LOG_FILES + 1

    def test_log_file_rotation_coverage(self, restore_app_env):
        log_file = 'test_ae_cov_log.log'
        valid_log_content = "TestBaseLogEntry"
        invalid_log_content = "NeverAppearInLogFile"
        fb, ext = os_path_splitext(log_file)    # simulate a left-over log file from the last app run - coverage
        idx = 1
        write_file(f"{fb}-{idx:0>{LOG_FILE_IDX_WIDTH}}{ext}",
                   f"log file content to test left-over from last app run{invalid_log_content}")
        try:
            app = AppBase('test_cov_log_file_rotation', debug_level=DEBUG_LEVEL_VERBOSE)
            app.init_logging(log_file_name=log_file, log_file_size_max=.001)    # log file max size == 1 kB
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):                   # full loop is creating 1 kB of log entries (16 * 64 bytes)
                    app.po(f"{valid_log_content}{idx: >26}{line_no: >26}")
            assert os_path_isfile(log_file)
        finally:
            contents = delete_files(log_file, keep_ext=True, ret_type='contents')
            assert len(contents) == MAX_NUM_LOG_FILES + 1
            for fc in contents:
                assert valid_log_content in fc
                assert invalid_log_content not in fc

    def test_app_instances_reset1(self):
        assert main_app_instance() is None  # check if core._APP_INSTANCES/._MAIN_APP_INST_KEY got reset correctly

    def test_log_file_rotation_multi_threading(self, restore_app_env):
        log_file = 'test_ae_multi_log.log'
        try:
            app = AppBase('test_base_log_file_rotation', multi_threading=True)
            app.init_logging(log_file_name=log_file, log_file_size_max=.001)
            # not needed explicitly: app.log_file_check()
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):
                    app.po("TestBaseLogEntry{: >26}{: >26}".format(idx, line_no))
            assert os_path_isfile(log_file)
        finally:
            assert delete_files(log_file, keep_ext=True) == MAX_NUM_LOG_FILES + 1

    def test_log_file_rotation_explicit_multi_threading(self, restore_app_env):
        log_file = 'test_ae_multi_log.log'
        try:
            app = AppBase('test_base_log_file_rotation')
            activate_multi_threading()
            app.init_logging(log_file_name=log_file, log_file_size_max=.001)
            # not needed explicitly: app.log_file_check()
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):
                    app.po("TestBaseLogEntry{: >26}{: >26}".format(idx, line_no))
            assert os_path_isfile(log_file)
        finally:
            assert delete_files(log_file, keep_ext=True) == MAX_NUM_LOG_FILES + 1

    def test_open_log_file_with_suppressed_stdout(self, capsys, restore_app_env):
        log_file = 'test_ae_no_stdout.log'
        tst_out = 'only printed to log file'
        try:
            app = AppBase('test_open_log_file_with_suppressed_stdout', suppress_stdout=True)
            assert app.suppress_stdout is True
            app.init_logging(log_file_name=log_file)
            app.po(tst_out)
            out, err = capsys.readouterr()
            assert out == "" and err == ""
            app.init_logging()      # close the log file
            assert os_path_isfile(log_file)
            out, err = capsys.readouterr()
            assert out == "" and err == ""
        finally:
            contents = delete_files(log_file, ret_type='contents')
            assert len(contents)
            assert tst_out in contents[0]

    def test_open_log_file_with_suppressed_stdout_reopen(self, capsys, restore_app_env):
        log_file = 'test_ae_no_stdout.log'
        tst_out = 'only printed to log file'
        try:
            app = AppBase('test_open_log_file_with_suppressed_stdout', suppress_stdout=True)
            # noinspection PyUnresolvedReferences
            app._nul_std_out.close()

            assert app.suppress_stdout is True
            app.init_logging(log_file_name=log_file)
            app.po(tst_out)
            out, err = capsys.readouterr()
            assert out == "" and err == ""
            app.init_logging()      # close the log file
            assert os_path_isfile(log_file)
            out, err = capsys.readouterr()
            assert out == "" and err == ""
        finally:
            contents = delete_files(log_file, ret_type='contents')
            assert len(contents)
            assert tst_out in contents[0]

    def test_invalid_log_file_name(self, restore_app_env):
        log_file = ':/:invalid:/:'
        app = AppBase('test_invalid_log_file_name')
        app.init_logging(log_file_name=log_file)
        with pytest.raises(FileNotFoundError):
            app.log_file_check()     # coverage of callee exception
        assert not os_path_isfile(log_file)

    def test_log_file_flush(self, restore_app_env):
        log_file = 'test_ae_base_log_flush.log'
        try:
            app = AppBase('test_base_log_file_flush')
            app.init_logging(log_file_name=log_file)
            app.log_file_check()
            assert os_path_isfile(log_file)
        finally:
            assert delete_files(log_file) == 1

    def test_sub_app_logging(self, restore_app_env):
        log_file = 'test_sub_app_logging.log'
        tst_out = 'print-out to log file'
        mp = "MAIN_"  # main/sub-app prefixes for log file names and print-outs
        sp = "SUB__"
        try:
            app = AppBase('test_main_app')
            app.init_logging(log_file_name=mp + log_file)
            sub = AppBase('test_sub_app', app_name=sp)
            sub.init_logging(log_file_name=sp + log_file)
            print_out(mp + tst_out + "_1")
            app.po(mp + tst_out + "_2")
            sub.po(sp + tst_out)
            sub.init_logging()
            app.init_logging()  # close the log file
            # NOT WORKING: capsys.readouterr() returning empty strings
            # out, err = capsys.readouterr()
            # assert out.count(tst_out) == 3 and err == ""
            assert os_path_isfile(mp + log_file)
            assert os_path_isfile(sp + log_file)
        finally:
            contents = delete_files(sp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out in contents[0]
            contents = delete_files(mp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out not in contents[0]

    def test_threaded_sub_app_logging(self, restore_app_env):
        sub_printed = False

        def sub_app_po():
            """ test thread function """
            nonlocal sub, sub_printed
            sub = AppBase('test_sub_app_thread', app_name=sp)
            sub.init_logging(log_file_name=sp + log_file)
            sub.po(sp + tst_out)
            sub_printed = True

        log_file = 'test_threaded_sub_app_logging.log'
        tst_out = 'print-out to log file'
        mp = "MAIN_"                    # main/sub-app prefixes for log file names and print-outs
        sp = "SUB__"
        try:
            app = AppBase('test_main_app_thread', app_name=mp, multi_threading=True)
            app.init_logging(log_file_name=mp + log_file)
            sub: Any = None
            sub_thread = threading.Thread(target=sub_app_po)
            sub_thread.start()
            while not sub_printed:      # NOT ENOUGH fails on gitlab CI: not sub or not sub.active_log_stream:
                pass                    # wait until the sub-thread has called init_logging()
            print_out(mp + tst_out + "_1")
            app.po(mp + tst_out + "_2")
            sub.init_logging()          # close the sub-app log file created by sub_thread
            sub_thread.join()
            app.init_logging()          # close the main-app log file
            assert os_path_isfile(sp + log_file)
            assert os_path_isfile(mp + log_file)
        finally:
            contents = delete_files(sp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out in contents[0]
            contents = delete_files(mp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out not in contents[0]

    def test_exception_log_file_flush(self, restore_app_env):
        app = AppBase('test_exception_base_log_file_flush')
        # cause/provoke _append_eof_and_flush_file() exceptions for coverage by passing any other non-stream object
        # noinspection PyInvalidCast
        app._append_eof_and_flush_file(cast(TextIO, None), 'invalid stream')

    def test_exception_log_file_flush_print(self, restore_app_env):
        app = AppBase('test_exception_log_file_flush_print')
        app.po = MagicMock()

        with (patch('builtins.print', side_effect=Exception('tst_print_exception')),
              patch('traceback.print_exc')):
            app._append_eof_and_flush_file(TextIO(), 'mocked stream')

        assert 'end-of-file marker exception' in app.po.call_args[0][0]

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestPythonLogging:
    """ test python logging module support
    """
    def test_log_init(self, restore_app_env):
        var_val = {'version': 1,
                   'disable_existing_loggers': False}
        app = AppBase('log_init')
        app.init_logging(py_logging_params=var_val)

        assert app.py_log_params == var_val

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_logging_params_dict_console_from_init(self, restore_app_env):
        var_val = {'version': 1,
                   'disable_existing_loggers': False,
                   'handlers': {'console': {'class': 'logging.StreamHandler',
                                            'level': logging.INFO}}}
        print(str(var_val))

        main_app = AppBase('test_python_logging_params_dict_console')
        main_app.init_logging(py_logging_params=var_val)

        assert main_app.py_log_params == var_val

    def test_logging_params_dict_console_from_init_with_log_file(self, restore_app_env):
        log_file = 'tst_py_log_complex.log'
        var_val = {'version': 1,
                   'disable_existing_loggers': False,
                   'handlers': {'console': {'class': 'logging.handlers.RotatingFileHandler',
                                            'level': logging.INFO,
                                            'filename': log_file,
                                            'maxBytes': 33,
                                            'backupCount': 63}},
                   'loggers': {'root': {'handlers': ['console']},
                               'ae': {'handlers': ['console']},
                               'ae.console': {'handlers': ['console']}}}
        print(str(var_val))

        cae = AppBase('test_python_logging_params_dict_file', debug_level=DEBUG_LEVEL_DISABLED)
        cae.init_logging(py_logging_params=var_val)

        assert cae.py_log_params == var_val

        # empty log file created by logging.config.dictConfig(py_logging_params) in :func:`ae.core.AppBase.init_logging`
        assert delete_files(log_file, ret_type='contents')[0] == ""

    def test_logging_params_dict_complex(self, restore_app_env):
        """ test logging with rotating file handler. """
        log_file = 'test_py_log_complex.log'
        entry_prefix = "TEST LOG ENTRY "

        var_val = {'version': 1,
                   'disable_existing_loggers': False,
                   'handlers': {'console': {'class': 'logging.handlers.RotatingFileHandler',
                                            'level': logging.INFO,
                                            'filename': log_file,
                                            'maxBytes': 33,
                                            'backupCount': 63}},
                   'loggers': {'root': {'handlers': ['console']},
                               'ae': {'handlers': ['console']},
                               'ae.core': {'handlers': ['console']}}}
        print(str(var_val))

        cae = AppBase('test_python_logging_params_dict_file', debug_level=DEBUG_LEVEL_DISABLED)
        cae.init_logging(py_logging_params=var_val)  # logging.config.dictConfig(py_logging_params) creates empty logFil

        assert cae.py_log_params == var_val

        root_logger = logging.getLogger()   # 'root'
        ae_logger = logging.getLogger('ae')
        ae_cae_logger = logging.getLogger('ae.core')

        # AppBase print_out/.po
        try:
            log_text = entry_prefix + "0 print_out"
            cae.po(log_text)
        finally:
            logging.shutdown()
            # empty log file created in log_init, and gets not extended by the above cae.po() call
            files_contents = delete_files(log_file, ret_type='contents')
            assert len(files_contents) == 1
            assert files_contents[0] == ""

        try:
            log_text = entry_prefix + "0 print_out root"
            cae.po(log_text, logger=root_logger)
        finally:
            logging.shutdown()
            files_contents = delete_files(log_file, ret_type='contents')
            assert len(files_contents) == 1
            assert files_contents[0].endswith(log_text + os.linesep)

        try:
            log_text = entry_prefix + "0 print_out ae"
            cae.po(log_text, logger=ae_logger)
        finally:
            logging.shutdown()
            files_contents = delete_files(log_file, ret_type='contents')
            assert len(files_contents) > 1
            assert any(_.endswith(log_text + os.linesep) for _ in files_contents)

        try:
            log_text = entry_prefix + "0 print_out ae_cae"
            cae.po(log_text, logger=ae_cae_logger)
        finally:
            logging.shutdown()
            # multiple log files because the log text has 34 bytes but RotatingFileHandler maxbytes is 33
            files_contents = delete_files(log_file, ret_type='contents')
            assert len(files_contents) > 1
            assert any(_.endswith(log_text + os.linesep) for _ in files_contents)

        # logging
        try:
            logging.info(entry_prefix + "1 info")       # will NOT be added to the log
        finally:
            logging.shutdown()
            assert delete_files(log_file) == 0

        try:
            logging.debug(entry_prefix + "2 debug")     # NOT logged
        finally:
            logging.shutdown()
            assert delete_files(log_file) == 0

        try:
            log_text = entry_prefix + "3 warning"
            logging.warning(log_text)
        finally:
            logging.shutdown()
            # pjm: assert delete_files(log_file) == 0
            # PyCharm: assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)
            assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)

        try:
            log_text = entry_prefix + "4 error logging"
            logging.error(log_text)
        finally:
            logging.shutdown()
            # pjm: assert delete_files(log_file) == 0
            # PyCharm: assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)
            assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)

        # loggers
        try:
            log_text = entry_prefix + "4 error root"
            root_logger.error(log_text)
        finally:
            logging.shutdown()
            # pjm: assert delete_files(log_file) == 0
            # PyCharm: assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)
            assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)

        try:
            log_text = entry_prefix + "4 error ae"
            ae_logger.error(log_text)
        finally:
            logging.shutdown()
            # pjm: assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)
            # pjm+PyCharm: delete_files returns 5 files (this one 2*, all the before missing ones & wrong ordered)?!?!?
            assert log_text + os.linesep in delete_files(log_file, ret_type='contents')

        try:
            log_text = entry_prefix + "4 error ae_cae"
            ae_cae_logger.error(log_text)
        finally:
            logging.shutdown()
            assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)

        # AppBase.debug_out/.dpo
        sys.argv = ['tl_cdc']  # sys.argv has to be set to allow get_option('debug_level') calls done by debug_out()
        try:
            log_text = entry_prefix + "5 not logged debug_out/dpo"
            cae.dpo(log_text)
        finally:
            logging.shutdown()
            assert delete_files(log_file) == 0

        # AppBase.print_out/.po
        try:
            log_text = entry_prefix + "5 print_out/po"
            cae.po(log_text, logger=ae_cae_logger)
        finally:
            logging.shutdown()
            assert delete_files(log_file, ret_type='contents')[0].endswith(log_text + os.linesep)

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestAppBase:      # only some basic tests - test coverage is done by :class:`~ae.console.ConsoleApp` tests
    def test_app_name(self, restore_app_env):
        name = 'tan_app_name'
        sys.argv = [name, ]
        app = AppBase()
        assert app.app_name == name

    def test_app_key(self, restore_app_env):
        app_name = 'TstAppName'
        env_id = 'TstEnvId'
        app = AppBase(app_name=app_name, sys_env_id=env_id)
        assert app.app_key == app_name + '@' + env_id

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_app_attributes(self, restore_app_env):
        ver = '0.0'
        title = 'test_app_name'
        app = AppBase(title, app_version=ver)
        assert app.app_title == title
        assert app.app_version == ver
        assert app.app_path == norm_path(os_path_dirname(sys.argv[0]))

    def test_app_cwd(self, capsys, restore_app_env, tmp_path):
        with patch('ae.core.os.getcwd'):
            AppBase()

        out, err = capsys.readouterr()
        assert 'upgrade check skipped' in out

    def test_app_find_version(self, restore_app_env):
        app = AppBase()
        assert app.app_version == __version__

    def test_app_find_title(self, restore_app_env):
        app = AppBase()
        assert app.app_title == (__doc__ or "").strip()

    def test_call_method_pass_silently_if_not_existing(self, restore_app_env):
        app = AppBase()
        method = 'not_existing_method'
        assert not hasattr(app, method)
        assert app.call_method(method) is None

    def test_call_method_in_other_instance(self, restore_app_env):
        app = AppBase()

        class _OtherClass:
            def _method(self, *args, **kwargs):
                return self, args, kwargs

        _instance = _OtherClass()
        t_args = (1, 2, '3')
        t_kwargs = {'a': 1, 'b': 2, 'c': '3'}
        assert app.call_method(_instance._method, *t_args, **t_kwargs) == (_instance, t_args, t_kwargs)

    def test_call_method_no_exception_if_not_exists(self, restore_app_env):
        app = AppBase()
        app.call_method('not_existing_method_name')

    def test_call_method_no_exception_if_not_callable(self, restore_app_env):
        app = AppBase()
        app.init_called = False
        app.call_method('init_called')

    def test_call_method_no_exception_if_raises_exception(self, restore_app_env):
        app = AppBase()

        def _raising_ex():
            """ dummy method raising exception """
            raise AttributeError
        setattr(app, 'test_raiser', _raising_ex)
        app.call_method('test_raiser')

    def test_call_method_no_exception_if_error_in_lambda(self, restore_app_env):
        app = AppBase()
        app.test_method = lambda *_args: 3 / 0
        app.call_method('test_method')

    def test_call_method_catch_lookup_error_exception(self, restore_app_env):
        app = AppBase()

        def _raising_ex():
            """ dummy method raising exception """
            raise LookupError
        setattr(app, 'test_raiser', _raising_ex)
        app.call_method('test_raiser')

    def test_call_method_catch_value_error_exception(self, restore_app_env):
        app = AppBase()

        def _raising_ex():
            """ dummy method raising exception """
            raise ValueError
        setattr(app, 'test_raiser', _raising_ex)
        app.call_method('test_raiser')

    def test_debug_out(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_ENABLED)
        tst = "tsT-debug-out-string"
        app.debug_out(tst)
        assert tst in capsys.readouterr()[0]

    def test_init_path_placeholders(self, restore_app_env):
        cae = AppBase("test_init_path_placeholders")

        assert PATH_PLACEHOLDERS is ae.core.PATH_PLACEHOLDERS
        assert PATH_PLACEHOLDERS is ae.paths.PATH_PLACEHOLDERS

        tst_path_placeholders = ae.paths.PATH_PLACEHOLDERS.copy()
        with (patch('ae.core.PATH_PLACEHOLDERS', tst_path_placeholders),
              patch('ae.core.os_platform', 'android')):
            assert cae.app_name == 'pyTstConsAppKey'
            assert ae.core.PATH_PLACEHOLDERS['app_name'] == 'pyTstConsAppKey'
            assert ae.core.PATH_PLACEHOLDERS['main_app_name'] == 'pyTstConsAppKey'

            new_app_name = 'some_new_app_name'
            cae.app_name = new_app_name
            cae._init_path_placeholders()
            assert ae.core.PATH_PLACEHOLDERS['app_name'] == new_app_name
            assert ae.core.PATH_PLACEHOLDERS['main_app_name'] == new_app_name
            cae.app_name = 'pyTstConsAppKey'

            assert 'apk_ext' in ae.core.PATH_PLACEHOLDERS

    def test_init_path_placeholders_read_err(self, restore_app_env):
        cae = AppBase("test_init_path_placeholders_read_err")
        usr_path = ae.core.PATH_PLACEHOLDERS['usr']
        old_phs = ae.core.PATH_PLACEHOLDERS.copy()

        with patch('ae.core.read_file', lambda *_args, **_kwargs: ""):
            cae._init_path_placeholders()
        assert ae.core.PATH_PLACEHOLDERS == old_phs
        assert ae.paths.PATH_PLACEHOLDERS == old_phs

        def _raise_err(file_path: str, *_args, **_kwargs):
            if placeholder_path(file_path).startswith('{usr}'):
                return read_file(file_path, *_args, **_kwargs)
            else:
                raise Exception("TstInitPathPlaceHoldersWriteErr")

        with patch('ae.core.read_file', _raise_err):
            tst_path_placeholders = ae.core.PATH_PLACEHOLDERS.copy()
            with patch('ae.core.PATH_PLACEHOLDERS', tst_path_placeholders):
                assert not ae.core.PATH_PLACEHOLDERS['ado'].startswith(usr_path)
                assert not placeholder_path(ae.core.PATH_PLACEHOLDERS['ado']).startswith("{usr}")
                try:
                    cae._init_path_placeholders()
                finally:
                    for re_dir in Collector(item_collector=coll_folders
                                            ).collect(usr_path, select=cae.app_name + "*").paths:
                        shutil.rmtree(re_dir)
                assert ae.core.PATH_PLACEHOLDERS['ado'].startswith(usr_path)
                assert placeholder_path(ae.core.PATH_PLACEHOLDERS['ado']).startswith("{usr}")
                assert ae.core.PATH_PLACEHOLDERS != old_phs

            assert ae.core.PATH_PLACEHOLDERS == old_phs

    def test_init_path_placeholders_write_err(self, restore_app_env):
        cae = AppBase("test_init_path_placeholders_write_err")
        usr_path = ae.core.PATH_PLACEHOLDERS['usr']
        old_phs = ae.core.PATH_PLACEHOLDERS.copy()

        with patch('ae.core.write_file', lambda *_args, **_kwargs: None):
            cae._init_path_placeholders()
        assert ae.core.PATH_PLACEHOLDERS == old_phs
        assert ae.paths.PATH_PLACEHOLDERS == old_phs

        def _raise_write_err(file_path: str, *_args, **_kwargs):
            if placeholder_path(file_path).startswith('{usr}'):
                write_file(file_path, *_args, **_kwargs)
            else:
                raise Exception("TstInitPathPlaceHoldersWriteErr")

        with patch('ae.core.write_file', _raise_write_err):
            tst_path_placeholders = ae.core.PATH_PLACEHOLDERS.copy()
            with patch('ae.core.PATH_PLACEHOLDERS', tst_path_placeholders):
                assert not ae.core.PATH_PLACEHOLDERS['ado'].startswith(usr_path)
                assert not placeholder_path(ae.core.PATH_PLACEHOLDERS['ado']).startswith("{usr}")
                try:
                    cae._init_path_placeholders()
                finally:
                    for re_dir in Collector(item_collector=coll_folders
                                            ).collect(usr_path, select=cae.app_name + "*").paths:
                        shutil.rmtree(re_dir)
                assert ae.core.PATH_PLACEHOLDERS['ado'].startswith(usr_path)
                assert placeholder_path(ae.core.PATH_PLACEHOLDERS['ado']).startswith("{usr}")
                assert ae.core.PATH_PLACEHOLDERS != old_phs

            assert ae.core.PATH_PLACEHOLDERS == old_phs

    def test_log_line_prefix(self, restore_app_env):
        app = AppBase(sys_env_id='Tee sst')
        app._log_with_timestamp = True
        prefix = app.log_line_prefix()
        assert APP_KEY_SEP + 'Tee sst' in prefix
        assert datetime.datetime.now().strftime(DATE_TIME_ISO)[:12] in prefix

        app.debug_level = DEBUG_LEVEL_VERBOSE
        prefix = app.log_line_prefix()
        assert '[' + DEBUG_LEVELS[app.debug_level][0] + ']' in prefix

    def test_print_out(self, capsys, restore_app_env):
        app = AppBase('test_python_logging_params_dict_basic_from_ini', multi_threading=True)
        app.po()
        out, err = capsys.readouterr()
        assert out.endswith('\n') and err == ''

        app.po(invalid_kwarg='ika')
        out, err = capsys.readouterr()
        assert 'ika' in out and err == ''

        us = chr(40960) + chr(1972) + chr(2013) + 'äöü'
        app.po(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert us in out and err == ''

        app.po(us, app_instance=app)
        app.po(us, file=sys.stdout)
        app.po(us, file=sys.stderr)
        fna = 'print_out.txt'
        fhd = open(fna, 'w', encoding='ascii', errors='strict')
        app.po(us, file=fhd)
        fhd.close()
        assert delete_files(fna) == 1
        app.po(bytes(chr(0xef) + chr(0xbb) + chr(0xbf), encoding='utf-8'))
        out, err = capsys.readouterr()
        assert us in out and us in err

        # print invalid/surrogate code point/char to force UnicodeEncodeError exception in print_out() (test coverage)
        us = chr(0xD801)
        app.po(us, encode_errors_def='strict')

        # multi_threading has to be reset to prevent a debug test run freeze (added multi_threading for coverage)
        _deactivate_multi_threading()

    def test_app_instances_reset2(self):
        assert main_app_instance() is None

    def test_shutdown_err_msg(self, capsys, restore_app_env):
        app = AppBase()

        app.shutdown(None, error_message='AppBase.shutdown() error-message')

        out, err = capsys.readouterr()
        assert 'AppBase.shutdown() error-message' in out
        assert err == ""

    def test_shutdown_exit_code_0(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_ENABLED)

        with patch('ae.core.sys.exit', lambda *args, **kwargs: None):
            app.shutdown()  # exit_code == 0

        out, err = capsys.readouterr()
        assert 'shutdown of ' in out
        assert err == ""

    def test_shutdown_exit_code_1(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_VERBOSE)

        with patch('ae.core.sys.exit', lambda *args, **kwargs: None):
            app.shutdown(1)

        assert 'shutdown of ' in capsys.readouterr()[0]

    def test_shutdown_exit_code_123456(self, capsys, restore_app_env):
        app = AppBase()

        with patch('ae.core.sys.exit', lambda *args, **kwargs: None):
            app.shutdown(123456)    # test warning if exit code is not in 0..255

        assert 'extended exit code' in capsys.readouterr()[0]

    def test_shutdown_exit_code_none(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_DISABLED)

        app.shutdown(None)

        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""

    def test_shutdown_got_shut_down(self, capsys, restore_app_env):
        app = AppBase()
        app._got_shut_down = True
        capsys.readouterr()

        app.shutdown(None)

        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""

    def test_shutdown_join_app_threads(self, capsys, restore_app_env):
        app = AppBase(multi_threading=True)
        sub_thread = threading.Thread(target=partial(AppBase, sys_env_id='tst sub app id'))
        sub_thread.start()
        sub_thread.join()

        app.shutdown(None)

        out, err = capsys.readouterr()
        assert '  **  joining thread id ' in out
        assert err == ""

    def test_shutdown_logging(self, restore_app_env):
        app = AppBase()
        app.py_log_params = {'tst_param': 'tst_log_param_value'}

        with patch('ae.core.logging.shutdown') as mock_log_shutdown:
            app.shutdown(None)

        mock_log_shutdown.assert_called()

    def test_shutdown_nul_std_out(self, restore_app_env):
        app = AppBase()
        mock_nul_out = MagicMock()
        mock_nul_out.closed = False
        app._nul_std_out = mock_nul_out

        with patch.object(app, '_append_eof_and_flush_file') as mock_flush:
            app.shutdown(None)

        mock_flush.assert_called_once_with(mock_nul_out, "NUL stdout")
        assert mock_nul_out.close.called

    def test_shutdown_rename_log_file(self, restore_app_env):
        app = AppBase()
        app._log_file_index += 1

        with patch.object(app, '_rename_log_file') as mock_ren_log:
            app.shutdown(None)

        mock_ren_log.assert_called_once()

    def test_shutdown_sub_app(self, capsys, restore_app_env):
        app = AppBase()
        _sub_app = AppBase(sys_env_id='sub app id')

        app.shutdown(None, error_message='AppBase.shutdown() w/ sub app error-message')

        out, err = capsys.readouterr()
        assert 'AppBase.shutdown() w/ sub app error-message' in out
        assert err == ""

    def test_shutdown_temp_context(self, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_ENABLED)
        assert not _temp_folders
        temp_context_get_or_create('tst_shutdown_tmp_context')
        assert 'tst_shutdown_tmp_context' in _temp_folders

        app.shutdown(exit_code=None)

        assert not _temp_folders

    def test_verbose(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_VERBOSE)
        assert app.verbose

    def test_verbose_out(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_ENABLED)
        tst = "tsT-debug-miss-string"
        app.verbose_out(tst)
        assert tst not in capsys.readouterr()[0]

        app.debug_level = DEBUG_LEVEL_VERBOSE
        tst = "tsT-verbose-out-string"
        app.verbose_out(tst)
        assert tst in capsys.readouterr()[0]


class TestTempContextDirectories:
    def test_temp_context_cleanup(self):
        path = temp_context_get_or_create()
        assert path == temp_context_get_or_create()
        assert os_path_isdir(path)

        temp_context_cleanup()

        assert not os_path_isdir(path)

        new_path = temp_context_get_or_create()
        assert os_path_isdir(new_path)
        assert new_path != path

        temp_context_cleanup()

        assert not os_path_isdir(new_path)

    def test_temp_context_folders(self):
        folder_name = "tst_tmp_dir"
        path = temp_context_get_or_create(folder_name=folder_name)

        assert path.endswith(folder_name)
        assert set(temp_context_folders()) == {folder_name}

        assert temp_context_folders(context="any not existing context") == []

    def test_temp_context_get_or_create(self):
        path = temp_context_get_or_create()
        assert os_path_isdir(path)
        temp_context_cleanup()

    def test_temp_context_get_or_create_named(self):
        ctx_name = "any string to name a temp dir"

        path = temp_context_get_or_create(context=ctx_name)

        assert os_path_isdir(path)
        temp_context_cleanup()
        assert os_path_isdir(path)
        temp_context_cleanup(context=ctx_name)
        assert not os_path_isdir(path)

    def test_temp_context_get_or_create_with_folder(self):
        dir1 = "name of the first temp dir"
        dir2 = "TempDirFolder2"

        path = temp_context_get_or_create(folder_name=dir1)

        assert path.endswith(dir1)
        assert os_path_isdir(path)

        path2 = temp_context_get_or_create(folder_name=dir2)

        assert path2.endswith(dir2)
        assert os_path_isdir(path)
        assert os_path_isdir(path2)
        assert set(temp_context_folders()) == {dir1, dir2}

        path2a = temp_context_get_or_create(folder_name=dir2)

        assert path2a == path2
        assert path2a.endswith(dir2)
        assert os_path_isdir(path)
        assert os_path_isdir(path2a)
        assert set(temp_context_folders()) == {dir1, dir2}

        temp_context_cleanup()

        assert not os_path_isdir(path)
        assert not os_path_isdir(path2)


class TestCoreModuleLoad:
    """ this test class has to be at the end (after TestappBase), else test_shutdown_temp_context() fails """
    @pytest.fixture(autouse=True)
    def reset_module(self):
        yield
        importlib.reload(ae.core)

    def test_init_from_app_cfg_file(self, monkeypatch, tmp_path):
        prj_root = str(tmp_path)
        section = 'app'
        write_file(os_path_join(prj_root, 'buildozer.spec'),
                   f"[{section}]\n" +
                   'package.name' + "=" + 'tst_pkg_name' + "\n" +
                   'package.domain' + "=" + 'tst_pkg_domain' + "\n" +
                   'android.permissions' + "=" + 'tst_android_per' + "\n"
                   )
        monkeypatch.chdir(prj_root)
        importlib.reload(ae.core)

        assert ae.core.PACKAGE_NAME == 'tst_pkg_name'
        assert ae.core.PACKAGE_DOMAIN == 'tst_pkg_domain'
        assert ae.core.PERMISSIONS == 'tst_android_per'

    def test_init_from_app_cfg_file_defaults(self, monkeypatch, tmp_path):
        prj_root = str(tmp_path)
        write_file(os_path_join(prj_root, 'buildozer.spec'), "")
        monkeypatch.chdir(prj_root)
        with patch('ae.system.stack_var', return_value=""):
            importlib.reload(ae.core)
            pass

        assert ae.core.PACKAGE_NAME == 'unspecified_package'
        assert ae.core.PACKAGE_DOMAIN == 'org.test'
        assert (ae.core.PERMISSIONS ==
                'INTERNET,VIBRATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE')

    def test_init_for_android(self):
        with (patch('ae.system.os_platform', 'android'),
              patch('ae.core.os_path_basename', return_value='__init__' + '.py'),
              patch('ae.base.extend_file') as mock_extend,
              patch('ae.core.importlib.import_module') as mock_import):
            importlib.reload(ae.core)

            service_instance_start = mock_import.return_value.autoclass.return_value.start
            activity = mock_import.return_value.autoclass.return_value.mActivity
            ae.core.start_app_service("tst_app_service")

        mock_extend.assert_called_once_with('importlib' + '_debug.log',  # stack_var('__file__') from importlib.reload()
                                            f"no {'buildozer.spec'} found/using defaults\n")
        service_instance_start.assert_called_once_with(activity, 'tst_app_service')
