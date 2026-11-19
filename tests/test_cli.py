"""End-to-end tests of the command line interface."""

from __future__ import annotations

import io

import pytest

from gradevault.cli.app import main


@pytest.fixture()
def run(tmp_path):
    """Run the CLI against a throw-away database and capture its output."""

    def _run(*argv: str):
        out = io.StringIO()
        err = io.StringIO()
        code = main(
            ["--db", str(tmp_path / "cli.db"), *argv],
            stream=out,
            error_stream=err,
        )
        return code, out.getvalue(), err.getvalue()

    return _run


def test_the_help_screen_lists_the_commands(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "student" in captured.out
    assert "course" in captured.out
    assert "result" in captured.out


def test_running_without_a_command_prints_the_help(run):
    code, out, _ = run()
    assert code == 2
    assert "usage" in out.lower()


def test_a_student_can_be_added_from_the_command_line(run):
    code, out, err = run("student", "add", "--id", "241337037", "--name", "Soron")
    assert code == 0
    assert "241337037" in out
    assert err == ""


def test_a_duplicate_student_is_reported_without_a_traceback(run):
    run("student", "add", "--id", "241337037", "--name", "Soron")
    code, out, err = run("student", "add", "--id", "241337037", "--name", "Other")
    assert code == 1
    assert out == ""
    assert "already exists" in err
    assert "Traceback" not in err


def test_an_unknown_student_is_reported(run):
    code, _, err = run("student", "show", "--id", "404")
    assert code == 1
    assert "no student with ID" in err


def test_a_course_can_be_added_and_listed(run):
    run("course", "add", "--code", "CSE402", "--title", "Software Engineering", "--credit", "3.00")
    code, out, _ = run("course", "list")
    assert code == 0
    assert "CSE402" in out
    assert "Software Engineering" in out


def test_a_mark_out_of_range_is_rejected(run):
    run("student", "add", "--id", "1", "--name", "Soron")
    run("course", "add", "--code", "CSE402", "--title", "Software Engineering")
    run("enroll", "--student", "1", "--course", "CSE402")
    code, _, err = run("mark", "enter", "--student", "1", "--course", "CSE402", "--mark", "120")
    assert code == 1
    assert "between 0 and 100" in err


def test_a_mark_can_be_entered(run):
    run("student", "add", "--id", "1", "--name", "Soron")
    run("course", "add", "--code", "CSE402", "--title", "Software Engineering")
    run("enroll", "--student", "1", "--course", "CSE402")
    code, out, _ = run(
        "mark", "enter", "--student", "1", "--course", "CSE402", "--mark", "86", "--by", "Prof. X"
    )
    assert code == 0
    assert "A+" in out


def test_the_result_sheet_is_shown(run):
    run("student", "add", "--id", "241337037", "--name", "Soron")
    run("course", "add", "--code", "CSE402", "--title", "Software Engineering", "--credit", "3.00")
    run("enroll", "--student", "241337037", "--course", "CSE402")
    run("mark", "enter", "--student", "241337037", "--course", "CSE402", "--mark", "86")
    code, out, _ = run("result", "--student", "241337037")
    assert code == 0
    assert "STUDENT RESULT SHEET" in out
    assert "CSE402" in out
    assert "4.00" in out  # the CGPA of a single A+ course


def test_the_result_sheet_can_be_written_as_csv(run):
    run("student", "add", "--id", "1", "--name", "Soron")
    run("course", "add", "--code", "CSE402", "--title", "Software Engineering")
    run("enroll", "--student", "1", "--course", "CSE402")
    run("mark", "enter", "--student", "1", "--course", "CSE402", "--mark", "86")
    code, out, _ = run("result", "--student", "1", "--csv")
    assert code == 0
    assert "student_id" in out
    assert "CSE402" in out


def test_the_result_sheet_can_be_written_to_a_file(run, tmp_path):
    run("student", "add", "--id", "1", "--name", "Soron")
    run("course", "add", "--code", "CSE402", "--title", "Software Engineering")
    run("enroll", "--student", "1", "--course", "CSE402")
    run("mark", "enter", "--student", "1", "--course", "CSE402", "--mark", "86")
    target = tmp_path / "sheet.csv"
    code, out, _ = run("result", "--student", "1", "--csv", "--out", str(target))
    assert code == 0
    assert "written to" in out
    assert "CSE402" in target.read_text(encoding="utf-8")


def test_the_grading_scale_is_printed(run):
    code, out, _ = run("scale")
    assert code == 0
    assert "80-100" in out
    assert "A+" in out
    assert "0-39" in out
    assert "F" in out


def test_the_demo_data_can_be_loaded_and_shown(run):
    code, out, _ = run("demo")
    assert code == 0
    assert "Loaded demo data" in out

    code, out, _ = run("result", "--student", "241337037")
    assert code == 0
    assert "CSE402" in out
    assert "3.83" in out  # the hand-computed CGPA of the demo student


def test_course_statistics_are_printed(run):
    run("demo")
    code, out, _ = run("stats", "--course", "CSE402")
    assert code == 0
    assert "CSE402" in out
    assert "Average" in out


def test_the_student_list_is_empty_at_the_start(run):
    code, out, _ = run("student", "list")
    assert code == 0
    assert "No students" in out


def test_the_memory_mode_leaves_no_file_behind(tmp_path, capsys):
    out = io.StringIO()
    err = io.StringIO()
    code = main(
        ["--memory", "student", "add", "--id", "1", "--name", "Soron"],
        stream=out,
        error_stream=err,
    )
    assert code == 0
    assert not list(tmp_path.glob("*.db"))


def test_data_survives_between_two_invocations(tmp_path):
    """The database file is the teacher's working copy."""
    database = tmp_path / "keep.db"
    out, err = io.StringIO(), io.StringIO()
    main(["--db", str(database), "student", "add", "--id", "1", "--name", "Soron"], out, err)
    out = io.StringIO()
    main(["--db", str(database), "student", "list"], out, err)
    assert "Soron" in out.getvalue()


def test_an_unknown_flag_is_a_usage_error(run):
    with pytest.raises(SystemExit) as exit_info:
        main(["--nonsense"])
    assert exit_info.value.code == 2


def test_a_mark_for_a_student_who_is_not_enrolled_is_reported(run):
    run("student", "add", "--id", "1", "--name", "Soron")
    run("course", "add", "--code", "CSE402", "--title", "Software Engineering")
    code, _, err = run("mark", "enter", "--student", "1", "--course", "CSE402", "--mark", "50")
    assert code == 1
    assert "not enrolled" in err
