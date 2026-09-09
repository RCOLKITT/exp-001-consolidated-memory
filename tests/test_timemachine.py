from datetime import date, datetime, timezone

from phase0.timemachine import check_freeze, cutoff_for, pip_env, timemachine_command


def test_cutoff_from_epoch_and_datetime():
    assert cutoff_for(1_700_000_000) == date(2023, 11, 14)
    assert cutoff_for(datetime(2024, 5, 1, 23, 30, tzinfo=timezone.utc)) == date(2024, 5, 1)


def test_freeze_audit_flags_future_and_unknown():
    cutoff = date(2024, 5, 1)
    dates = {("numpy", "1.26.4"): date(2024, 2, 5), ("requests", "2.32.0"): date(2024, 5, 20)}
    v = check_freeze(["numpy==1.26.4", "requests==2.32.0", "Some_Pkg==0.1", "-e ./local"], dates, cutoff)
    assert [(x.package, x.reason.split(" ")[0]) for x in v] == [("requests", "released"), ("some-pkg", "unknown")]


def test_pip_env_and_command():
    env = pip_env(date(2024, 5, 1))
    assert env["PIP_INDEX_URL"].startswith("http://127.0.0.1:") and env["TIMEMACHINE_CUTOFF"] == "2024-05-01"
    assert timemachine_command(date(2024, 5, 1))[:2] == ["pypi-timemachine", "2024-05-01"]
