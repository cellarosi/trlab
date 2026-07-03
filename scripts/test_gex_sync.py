import os
import tempfile
import unittest
from datetime import datetime

from gex_sync import (
    CSV_HEADER,
    _already_in_csv,
    _format_csv_row,
    _is_in_gex_window,
    build_gex_url,
    floor_to_15min,
    get_15min_interval,
    write_gex_csv,
)


# ============================================================
# get_15min_interval  —  all 4 buckets + boundary edges
# ============================================================

class TestGet15minInterval(unittest.TestCase):

    def _dt(self, minute: int) -> datetime:
        return datetime(2026, 7, 3, 10, minute, 0)

    # --- bucket 0 (0–14) ---
    def test_minute_0_returns_0(self):
        self.assertEqual(get_15min_interval(self._dt(0)), 0)

    def test_minute_7_returns_0(self):
        self.assertEqual(get_15min_interval(self._dt(7)), 0)

    def test_minute_14_returns_0(self):
        # right before the boundary — must still be in bucket 0
        self.assertEqual(get_15min_interval(self._dt(14)), 0)

    # --- bucket 15 (15–29) ---
    def test_minute_15_returns_15(self):
        self.assertEqual(get_15min_interval(self._dt(15)), 15)

    def test_minute_22_returns_15(self):
        self.assertEqual(get_15min_interval(self._dt(22)), 15)

    def test_minute_29_returns_15(self):
        self.assertEqual(get_15min_interval(self._dt(29)), 15)

    # --- bucket 30 (30–44) ---
    def test_minute_30_returns_30(self):
        self.assertEqual(get_15min_interval(self._dt(30)), 30)

    def test_minute_37_returns_30(self):
        self.assertEqual(get_15min_interval(self._dt(37)), 30)

    def test_minute_44_returns_30(self):
        self.assertEqual(get_15min_interval(self._dt(44)), 30)

    # --- bucket 45 (45–59) ---
    def test_minute_45_returns_45(self):
        self.assertEqual(get_15min_interval(self._dt(45)), 45)

    def test_minute_52_returns_45(self):
        self.assertEqual(get_15min_interval(self._dt(52)), 45)

    def test_minute_59_returns_45(self):
        # highest possible minute — must still land in bucket 45, not 60
        self.assertEqual(get_15min_interval(self._dt(59)), 45)


# ============================================================
# floor_to_15min  —  verify flooring + seconds/microseconds zeroed
# ============================================================

class TestFloorTo15min(unittest.TestCase):

    def test_floors_07_to_00(self):
        result = floor_to_15min(datetime(2026, 7, 3, 10, 7, 23, 456789))
        self.assertEqual(result, datetime(2026, 7, 3, 10, 0, 0, 0))

    def test_floors_22_to_15(self):
        result = floor_to_15min(datetime(2026, 7, 3, 10, 22, 45, 123456))
        self.assertEqual(result, datetime(2026, 7, 3, 10, 15, 0, 0))

    def test_floors_37_to_30(self):
        result = floor_to_15min(datetime(2026, 7, 3, 10, 37, 8, 999999))
        self.assertEqual(result, datetime(2026, 7, 3, 10, 30, 0, 0))

    def test_floors_52_to_45(self):
        result = floor_to_15min(datetime(2026, 7, 3, 10, 52, 59, 1))
        self.assertEqual(result, datetime(2026, 7, 3, 10, 45, 0, 0))

    def test_floors_00_is_00(self):
        result = floor_to_15min(datetime(2026, 7, 3, 10, 0, 0, 0))
        self.assertEqual(result, datetime(2026, 7, 3, 10, 0, 0, 0))

    def test_floors_59_to_45(self):
        result = floor_to_15min(datetime(2026, 7, 3, 23, 59, 59, 999999))
        self.assertEqual(result, datetime(2026, 7, 3, 23, 45, 0, 0))

    def test_hour_unchanged_across_bucket(self):
        # Midnight: 00:03 must floor to 00:00, not 23:45 of the previous day
        result = floor_to_15min(datetime(2026, 7, 3, 0, 3, 0, 0))
        self.assertEqual(result, datetime(2026, 7, 3, 0, 0, 0, 0))


# ============================================================
# build_gex_url
# ============================================================

class TestBuildGexUrl(unittest.TestCase):

    def test_builds_correct_url(self):
        url = build_gex_url("2026-07-06")
        expected = (
            "https://quantwheel.com/api/tools/gex"
            "?ticker=SPX&expirations=2026-07-06&deltaRange=all&formula=per_1pct"
        )
        self.assertEqual(url, expected)

    def test_different_expiration(self):
        url = build_gex_url("2026-12-31")
        self.assertIn("expirations=2026-12-31", url)
        self.assertIn("ticker=SPX", url)


# ============================================================
# _already_in_csv  —  every branch of the file/match logic
# ============================================================

class TestAlreadyInCsv(unittest.TestCase):

    def setUp(self):
        # delete=False so the file survives after the handle is closed
        self.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        self.path = self.tmp.name

    def tearDown(self):
        self.tmp.close()
        # test_file_does_not_exist removes it early; guard here avoids double-unlink
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_file_does_not_exist(self):
        os.unlink(self.path)
        self.assertFalse(_already_in_csv("2026-07-03 10:00:00", self.path))

    def test_file_exists_but_empty(self):
        # opened with mode="w" but never written → exists, getsize=0
        self.assertFalse(_already_in_csv("2026-07-03 10:00:00", self.path))

    def test_ts_not_in_file(self):
        self.tmp.write("datetime,expiration,callWall_strike\n")
        self.tmp.write("2026-07-03 10:15:00,2026-07-06 00:00:00,7500\n")
        self.tmp.flush()
        self.assertFalse(_already_in_csv("2026-07-03 10:00:00", self.path))

    def test_ts_found_as_start_of_row(self):
        self.tmp.write("datetime,expiration,callWall_strike\n")
        self.tmp.write("2026-07-03 10:00:00,2026-07-06 00:00:00,7500\n")
        self.tmp.flush()
        self.assertTrue(_already_in_csv("2026-07-03 10:00:00", self.path))

    def test_real_timestamp_does_not_match_header(self):
        # "datetime,..." is the header row; a real ts like "2026-07-03 ..." never
        # starts a line that begins with the header, so no false positive
        self.tmp.write("datetime,expiration,callWall_strike\n")
        self.tmp.write("2026-07-03 10:00:00,2026-07-06 00:00:00,7500\n")
        self.tmp.flush()
        self.assertFalse(_already_in_csv("2026-07-03 10:30:00", self.path))

    def test_startswith_matches_prefix(self):
        # startswith is deliberately loose: "2026-07-03 10:00" would match
        # "2026-07-03 10:00:30" — but in practice ts is always HH:MM:SS,
        # so this only affects same-second collisions (which are fine)
        self.tmp.write("datetime,expiration,callWall_strike\n")
        self.tmp.write("2026-07-03 10:00:30,2026-07-06 00:00:00,7500\n")
        self.tmp.flush()
        self.assertTrue(_already_in_csv("2026-07-03 10:00:30", self.path))
        self.assertFalse(_already_in_csv("2026-07-03 10:15:00", self.path))

    def test_multiple_rows_match_correct_one(self):
        self.tmp.write("datetime,expiration,callWall_strike\n")
        self.tmp.write("2026-07-03 10:00:00,2026-07-06 00:00:00,7500\n")
        self.tmp.write("2026-07-03 10:15:00,2026-07-06 00:00:00,7510\n")
        self.tmp.write("2026-07-03 10:30:00,2026-07-06 00:00:00,7520\n")
        self.tmp.flush()
        self.assertTrue(_already_in_csv("2026-07-03 10:15:00", self.path))
        self.assertFalse(_already_in_csv("2026-07-03 10:45:00", self.path))


# ============================================================
# _format_csv_row
# ============================================================

class TestFormatCsvRow(unittest.TestCase):

    def test_full_row_with_all_values(self):
        dt = datetime(2026, 7, 3, 10, 0, 0)
        row = _format_csv_row(dt, "2026-07-06", 7500, 7450, 7473.63, "positive", 7483.24)
        expected = "2026-07-03 10:00:00,2026-07-06 00:00:00,7500,7450,7473.63,positive,7483.24"
        self.assertEqual(row, expected)

    def test_row_with_none_values(self):
        # None → "None" in the CSV; this is intentional — empty would hide missing data
        dt = datetime(2026, 7, 3, 10, 15, 0)
        row = _format_csv_row(dt, "2026-07-06", None, None, None, None, None)
        expected = "2026-07-03 10:15:00,2026-07-06 00:00:00,None,None,None,None,None"
        self.assertEqual(row, expected)

    def test_row_with_empty_strings(self):
        # empty strings are the fallback when fetch_gex returns None
        dt = datetime(2026, 7, 3, 10, 30, 0)
        row = _format_csv_row(dt, "2026-07-06", "", "", "", "", "")
        expected = "2026-07-03 10:30:00,2026-07-06 00:00:00,,,,,"
        self.assertEqual(row, expected)

    def test_row_with_floats_and_string_zone(self):
        dt = datetime(2026, 7, 3, 10, 45, 0)
        row = _format_csv_row(dt, "2026-07-08", 7600.5, 7400.25, -100.0, "negative", 7500.0)
        expected = "2026-07-03 10:45:00,2026-07-08 00:00:00,7600.5,7400.25,-100.0,negative,7500.0"
        self.assertEqual(row, expected)

    def test_expiration_format_adds_midnight(self):
        # expiration is just a date; the row formatter appends "00:00:00"
        dt = datetime(2026, 12, 31, 23, 45, 0)
        row = _format_csv_row(dt, "2027-01-15", 1, 2, 3, "z", 4)
        self.assertIn("2027-01-15 00:00:00", row)


# ============================================================
# _is_in_gex_window  —  Rome-time window check
# ============================================================

class TestIsInGexWindow(unittest.TestCase):

    def _dt(self, hour: int, minute: int) -> datetime:
        # All test datetimes are Rome-local; _is_in_gex_window only checks .time()
        from zoneinfo import ZoneInfo
        return datetime(2026, 7, 3, hour, minute, 0, tzinfo=ZoneInfo("Europe/Rome"))

    def test_inside_window_mid_afternoon(self):
        self.assertTrue(_is_in_gex_window(self._dt(18, 30)))

    def test_window_open_at_15_00(self):
        self.assertTrue(_is_in_gex_window(self._dt(15, 0)))

    def test_window_closed_at_21_45(self):
        self.assertTrue(_is_in_gex_window(self._dt(21, 45)))

    def test_before_window_14_59(self):
        self.assertFalse(_is_in_gex_window(self._dt(14, 59)))

    def test_after_window_21_46(self):
        self.assertFalse(_is_in_gex_window(self._dt(21, 46)))

    def test_midnight_is_outside(self):
        self.assertFalse(_is_in_gex_window(self._dt(0, 0)))

    def test_morning_is_outside(self):
        self.assertFalse(_is_in_gex_window(self._dt(10, 0)))


# ============================================================
# write_gex_csv  —  file I/O, header, append, duplicate skip
# ============================================================

class TestWriteGexCsv(unittest.TestCase):

    def setUp(self):
        # delete=False + manual close: some OSes lock the file while the
        # NamedTemporaryFile handle is open, preventing re-open in tests
        self.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        self.path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def _dt(self, minute: int = 0) -> datetime:
        return datetime(2026, 7, 3, 10, minute, 0)

    def _read(self) -> str:
        with open(self.path, "r") as f:
            return f.read()

    def test_new_file_writes_header_and_row(self):
        result = write_gex_csv(self._dt(0), "2026-07-06", 7500, 7450, 7473.6, "positive", 7483.2, path=self.path)
        self.assertTrue(result)
        content = self._read()
        lines = content.strip().split("\n")
        self.assertEqual(lines[0], CSV_HEADER)
        self.assertTrue(lines[1].startswith("2026-07-03 10:00:00"))
        self.assertIn("7500", lines[1])
        self.assertIn("7450", lines[1])

    def test_append_to_existing_file_no_second_header(self):
        write_gex_csv(self._dt(0), "2026-07-06", 7500, 7450, 7473.6, "positive", 7483.2, path=self.path)
        result = write_gex_csv(self._dt(15), "2026-07-06", 7510, 7460, 7480.0, "positive", 7490.0, path=self.path)
        self.assertTrue(result)
        content = self._read()
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 3)  # header + 2 rows
        self.assertEqual(lines[0], CSV_HEADER)

    def test_duplicate_datetime_skipped(self):
        write_gex_csv(self._dt(0), "2026-07-06", 7500, 7450, 7473.6, "positive", 7483.2, path=self.path)
        # Second call with same floored time but different values — must be skipped
        result = write_gex_csv(self._dt(0), "2026-07-06", 9999, 9999, 9999, "x", 9999, path=self.path)
        self.assertFalse(result)
        content = self._read()
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 2)  # header + 1 row only
        # Original value 7500 is still there — 9999 was NOT written
        self.assertIn("7500", lines[1])

    def test_write_minute_45_bucket(self):
        result = write_gex_csv(self._dt(45), "2026-07-06", 7500, 7450, 7473.6, "positive", 7483.2, path=self.path)
        self.assertTrue(result)
        content = self._read()
        self.assertIn("10:45:00", content)

    def test_write_with_none_values(self):
        result = write_gex_csv(self._dt(30), "2026-07-06", None, None, None, None, None, path=self.path)
        self.assertTrue(result)
        content = self._read()
        self.assertIn("None,None,None,None,None", content)

    def test_write_with_empty_strings(self):
        result = write_gex_csv(self._dt(0), "2026-07-06", "", "", "", "", "", path=self.path)
        self.assertTrue(result)
        content = self._read()
        self.assertIn("10:00:00,2026-07-06 00:00:00,,,,,", content)

    def test_three_intervals_all_written(self):
        for minute in (0, 15, 30):
            result = write_gex_csv(self._dt(minute), "2026-07-06", 7500, 7450, 7473.6, "positive", 7483.2, path=self.path)
            self.assertTrue(result)
        content = self._read()
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 4)  # header + 3 rows

    def test_fourth_interval_45_written(self):
        # All four possible intervals must be writable without conflicts
        for minute in (0, 15, 30, 45):
            write_gex_csv(self._dt(minute), "2026-07-06", 7500, 7450, 7473.6, "positive", 7483.2, path=self.path)
        content = self._read()
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 5)  # header + 4 rows


if __name__ == "__main__":
    unittest.main()
