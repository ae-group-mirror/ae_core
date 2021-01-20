""" test doc string for AppBase.app_title tests. """

import datetime
import logging
import os
import sys
import threading
from typing import cast, Any

import pytest
from conftest import delete_files

from ae.base import DATE_TIME_ISO, force_encoding
# noinspection PyProtectedMember
from ae.core import (
    APP_KEY_SEP, DEBUG_LEVELS, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, MAX_NUM_LOG_FILES, LOG_FILE_IDX_WIDTH,
    activate_multi_threading, _deactivate_multi_threading, hide_dup_line_prefix, main_app_instance, po,
    registered_app_names,
    AppBase, _PrintingReplicator, SubApp)


__version__ = '3.6.9dev-test'   # used for automatic app version find tests


class TestCoreHelpers:
    def test_hide_dup_line_prefix(self):
        l1 = "<t_s_t>"
        l2 = l1
        assert hide_dup_line_prefix(l1, l2) == " " * len(l2)
        l2 = l1 + l1
        assert hide_dup_line_prefix(l1, l2) == " " * len(l1) + l1
        assert hide_dup_line_prefix(l2, l1) == " " * len(l1)
        l2 = l1[:3] + l1
        assert hide_dup_line_prefix(l1, l2) == " " * 3 + l1

    def test_print_out_basics(self, capsys):
        po()
        out, err = capsys.readouterr()
        assert out == '\n' and err == ''

        po(invalid_kwarg='ika')
        out, err = capsys.readouterr()
        assert 'ika' in out and err == ''

        us = chr(40960) + chr(1972) + chr(2013) + 'äöü'
        po(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert us in out and err == ''

        po(us, file=sys.stdout)
        po(us, file=sys.stderr)
        fna = 'print_out.txt'
        fhd = open(fna, 'w', encoding='ascii', errors='strict')
        po(us, file=fhd)
        fhd.close()
        assert delete_files(fna) == 1
        po(bytes(chr(0xef) + chr(0xbb) + chr(0xbf), encoding='utf-8'))
        out, err = capsys.readouterr()
        assert us in out
        assert us in err

    def test_print_out_cov(self, capsys):
        # print invalid/surrogate code point/char for to force UnicodeEncodeError exception in po() (testing coverage)
        us = chr(0xD801)
        po(us, 123456, encode_errors_def='strict')      # .. also coverage of not-str args
        out, err = capsys.readouterr()
        assert force_encoding(us) in out and '123456' in out and err == ''

        po('\r', 123456)     # coverage of processing output (not captured by pytest)
        out, err = capsys.readouterr()
        assert out == '' and err == ''

    def test_registered_app_names_empty(self):
        assert not registered_app_names()

    def test_registered_app_names_not_empty(self, restore_app_env):
        assert not registered_app_names()
        app = AppBase()
        assert len(registered_app_names()) == 1
        assert app.app_name == registered_app_names()[0]


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
            with open(lfn) as f:
                assert f.read() == msg

            lfo = open(lfn, 'w', encoding='utf-8')
            dso = _PrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            with open(lfn, encoding='utf-8') as f:
                assert f.read() == msg

            lfo = open(lfn, 'w', encoding='ascii')
            dso = _PrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            with open(lfn, encoding='ascii') as f:
                assert f.read() == '\\ua000\\u07b4'

            lfo = open(lfn, 'w')
            dso = _PrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            with open(lfn) as f:
                if f.encoding == 'ascii':
                    assert f.read() == '\\ua000\\u07b4'
                else:
                    assert f.read() == msg      # msg == '\ua000\u07b4'

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
            assert os.path.exists(log_file)
        finally:
            assert delete_files(log_file, keep_ext=True) == MAX_NUM_LOG_FILES + 1

    def test_log_file_rotation_coverage(self, restore_app_env):
        log_file = 'test_ae_cov_log.log'
        valid_log_content = "TestBaseLogEntry"
        invalid_log_content = "NeverAppearInLogFile"
        fb, ext = os.path.splitext(log_file)    # simulate left-over log file from last app run - coverage
        idx = 1
        with open(f"{fb}-{idx:0>{LOG_FILE_IDX_WIDTH}}{ext}", 'w') as fp:
            fp.write(f"log file content for to test left-over from last app run{invalid_log_content}")
        try:
            app = AppBase('test_cov_log_file_rotation', debug_level=DEBUG_LEVEL_VERBOSE)
            app.init_logging(log_file_name=log_file, log_file_size_max=.001)    # log file max size == 1 kB
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):                   # full loop is creating 1 kB of log entries (16 * 64 bytes)
                    app.po(f"{valid_log_content}{idx: >26}{line_no: >26}")
            assert os.path.exists(log_file)
        finally:
            contents = delete_files(log_file, keep_ext=True, ret_type='contents')
            assert len(contents) == MAX_NUM_LOG_FILES + 1
            for fc in contents:
                assert valid_log_content in fc
                assert invalid_log_content not in fc

    def test_app_instances_reset1(self):
        assert main_app_instance() is None  # check if core._app_instances/._main_app_inst_key got reset correctly

    def test_log_file_rotation_multi_threading(self, restore_app_env):
        log_file = 'test_ae_multi_log.log'
        try:
            app = AppBase('test_base_log_file_rotation', multi_threading=True)
            app.init_logging(log_file_name=log_file, log_file_size_max=.001)
            # not needed explicitly: app.log_file_check()
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):
                    app.po("TestBaseLogEntry{: >26}{: >26}".format(idx, line_no))
            assert os.path.exists(log_file)
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
            assert os.path.exists(log_file)
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
            app.init_logging()      # close log file
            assert os.path.exists(log_file)
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
        assert not os.path.exists(log_file)

    def test_log_file_flush(self, restore_app_env):
        log_file = 'test_ae_base_log_flush.log'
        try:
            app = AppBase('test_base_log_file_flush')
            app.init_logging(log_file_name=log_file)
            app.log_file_check()
            assert os.path.exists(log_file)
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
            sub = SubApp('test_sub_app', app_name=sp)
            sub.init_logging(log_file_name=sp + log_file)
            po(mp + tst_out + "_1")
            app.po(mp + tst_out + "_2")
            sub.po(sp + tst_out)
            sub.init_logging()
            app.init_logging()  # close log file
            # NOT WORKING: capsys.readouterr() returning empty strings
            # out, err = capsys.readouterr()
            # assert out.count(tst_out) == 3 and err == ""
            assert os.path.exists(mp + log_file)
            assert os.path.exists(sp + log_file)
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
            sub = SubApp('test_sub_app_thread', app_name=sp)
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
                pass                    # wait until sub-thread has called init_logging()
            po(mp + tst_out + "_1")
            app.po(mp + tst_out + "_2")
            sub.init_logging()          # close sub-app log file created by sub_thread
            sub_thread.join()
            app.init_logging()          # close main-app log file
            assert os.path.exists(sp + log_file)
            assert os.path.exists(mp + log_file)
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
        app._append_eof_and_flush_file(cast('TextIO', None), 'invalid stream')

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestPythonLogging:
    """ test python logging module support
    """
    def test_logging_params_dict_console_from_init(self, restore_app_env):
        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.StreamHandler',
                                              'level': logging.INFO}))
        print(str(var_val))

        app = AppBase('test_python_base_logging_params_dict_console')
        app.init_logging(py_logging_params=var_val)

        assert app.py_log_params == var_val
        logging.shutdown()

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_logging_params_dict_complex(self, caplog, restore_app_env, tst_app_key):
        log_file = 'test_base_rot_file.log'
        entry_prefix = "TEST LOG ENTRY "

        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.handlers.RotatingFileHandler',
                                              'level': logging.INFO,
                                              'filename': log_file,
                                              'maxBytes': 33,
                                              'backupCount': 63}),
                       loggers={'root': dict(handlers=['console']),
                                'ae.core': dict(handlers=['console']),
                                'ae.console': dict(handlers=['console'])}
                       )
        print(str(var_val))

        app = AppBase('test_python_base_logging_params_dict_file')
        app.init_logging(py_logging_params=var_val)

        assert app.py_log_params == var_val

        root_logger = logging.getLogger()
        ae_core_logger = logging.getLogger('ae.core')
        ae_app_logger = logging.getLogger('ae.console')

        # AppBase print_out()/po()
        log_text = entry_prefix + "0 print_out"
        app.po(log_text)
        assert caplog.text == ""

        log_text = entry_prefix + "0 print_out root"
        app.po(log_text, logger=root_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae"
        app.po(log_text, logger=ae_core_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae_app"
        app.po(log_text, logger=ae_app_logger)
        assert caplog.text.endswith(log_text + "\n")

        # logging
        logging.info(entry_prefix + "1 info")       # will NOT be added to log
        assert caplog.text.endswith(log_text + "\n")

        logging.debug(entry_prefix + "2 debug")     # NOT logged
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "3 warning"
        logging.warning(log_text)                   # NOT logged
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error logging"
        logging.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        # loggers
        log_text = entry_prefix + "4 error root"
        root_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error ae"
        ae_core_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error ae_app"
        ae_app_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        new_log_text = entry_prefix + "5 dpo"
        app.po(new_log_text)
        assert caplog.text.endswith(log_text + "\n")    # NO LOGGER OUTPUT without po logger arg - caplog unchanged
        app.po(new_log_text, logger=ae_app_logger)
        assert caplog.text.endswith(new_log_text + "\n")

        # final checks of log file contents
        logging.shutdown()
        file_contents = delete_files(log_file, ret_type='contents')
        assert len(file_contents) >= 5
        for fc in file_contents:
            if fc.startswith(" <"):
                fc = fc[fc.index("> ") + 2:]    # remove thread id prefix
            if fc.startswith("{TST}"):
                fc = fc[6:]                     # remove sys_env_id prefix
            assert fc.startswith(entry_prefix)
            assert "1 info" not in fc and "2 debug" not in fc and "3 warning" not in fc

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestAppBase:      # only some basic tests - test coverage is done by :class:`~.console.ConsoleApp` tests
    def test_app_name(self, restore_app_env, sys_argv_app_key_restore):
        name = 'tan_app_name'
        sys.argv = [name, ]
        app = AppBase()
        assert app.app_name == name

    def test_app_key(self, restore_app_env):
        app = AppBase(app_name='XXX', sys_env_id='YYY')
        assert app.app_key == 'XXX@YYY'

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_app_attributes(self, restore_app_env):
        ver = '0.0'
        title = 'test_app_name'
        app = AppBase(title, app_version=ver)
        assert app.app_title == title
        assert app.app_version == ver
        assert app.app_path == os.path.dirname(sys.argv[0])

    def test_app_find_version(self, restore_app_env):
        app = AppBase()
        assert app.app_version == __version__

    def test_app_find_title(self, restore_app_env):
        app = AppBase()
        assert app.app_title == __doc__.strip()

    def test_call_method_raise_if_not_callable(self, restore_app_env):
        app = AppBase()
        app.init_called = False
        with pytest.raises(AssertionError):
            app.call_method('init_called')

    def test_call_method_catch_attr_error_exception(self, restore_app_env):
        app = AppBase()

        def _raising_ex():
            """ dummy method raising exception """
            raise AttributeError
        setattr(app, 'test_raiser', _raising_ex)
        app.call_method('test_raiser')

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

        # print invalid/surrogate code point/char for to force UnicodeEncodeError exception in po() (testing coverage)
        us = chr(0xD801)
        app.po(us, encode_errors_def='strict')

        # multi_threading has to be reset for to prevent debug test run freeze (added multi_threading for coverage)
        _deactivate_multi_threading()

    def test_app_instances_reset2(self):
        assert main_app_instance() is None

    def test_verbose(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_VERBOSE)
        assert app.verbose

    def test_debug_out(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_ENABLED)
        tst = "tsT-debug-out-string"
        app.debug_out(tst)
        assert tst in capsys.readouterr()[0]

    def test_verbose_out(self, capsys, restore_app_env):
        app = AppBase(debug_level=DEBUG_LEVEL_ENABLED)
        tst = "tsT-debug-miss-string"
        app.verbose_out(tst)
        assert tst not in capsys.readouterr()[0]

        app.debug_level = DEBUG_LEVEL_VERBOSE
        tst = "tsT-verbose-out-string"
        app.verbose_out(tst)
        assert tst in capsys.readouterr()[0]
