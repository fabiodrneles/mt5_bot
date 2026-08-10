import sys
import main
import tracker
import dashboard
import tui


def test_main_version(capsys, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['mt5bot', '--version'])
    main.main()
    captured = capsys.readouterr()
    assert 'MT5Bot v1.4.0' in captured.out


def test_main_help(capsys, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['mt5bot', '--help'])
    main.main()
    captured = capsys.readouterr()
    assert 'MT5Bot — Measured, disciplined execution' in captured.out


def test_main_report_cli(monkeypatch):
    called = {'reported': False}
    monkeypatch.setattr(sys, 'argv', ['mt5bot', '--report'])
    monkeypatch.setattr(tracker, 'print_report', lambda: called.__setitem__('reported', True))

    main.main()

    assert called['reported'] is True


def test_main_dashboard_cli(monkeypatch):
    called = {'opened': False}
    monkeypatch.setattr(sys, 'argv', ['mt5bot', '--dashboard'])
    monkeypatch.setattr(dashboard, 'open_report', lambda: called.__setitem__('opened', True))

    main.main()

    assert called['opened'] is True


def test_main_quick_runs_bot(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['mt5bot', '--quick'])
    monkeypatch.setattr(tui, 'clear_screen', lambda: None)
    monkeypatch.setattr(tui, 'print_header', lambda: None)
    monkeypatch.setattr(tui, 'connect_mt5_tui', lambda: True)
    monkeypatch.setattr(tui, 'show_summary', lambda: None)
    monkeypatch.setattr(main, 'run_bot', lambda: None)
    monkeypatch.setattr(tracker, 'print_report', lambda: None)

    main.main()


def test_main_shutdown_action_cli(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['mt5bot', '--shutdown-action', 'wait-flat'])
    monkeypatch.setattr(main, '_show_startup_menu', lambda: '1')
    monkeypatch.setattr(tui, 'connect_mt5_tui', lambda: True)
    monkeypatch.setattr(tui, 'show_summary', lambda: None)
    monkeypatch.setattr(main, 'run_bot', lambda: None)
    monkeypatch.setattr(tracker, 'print_report', lambda: None)
    monkeypatch.setattr(tui, 'clear_screen', lambda: None)
    monkeypatch.setattr(tui, 'print_header', lambda: None)

    main._shutdown_action = None
    main.main()

    assert main._shutdown_action == 'wait-flat'
