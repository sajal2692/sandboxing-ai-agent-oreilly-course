"""Check what counts as evidence from the optional OS-access probe."""

import unittest

from verify_host_access import check_probe


class HostAccessChecks(unittest.TestCase):
    def successful_probe(self):
        return {
            "outside_read": {"error": "PermissionError", "errno": 1},
            "private_read": {"error": "PermissionError", "errno": 1},
            "outside_write": {"error": "PermissionError", "errno": 1},
            "data_write": {"error": "PermissionError", "errno": 1},
            "data_read": {"status": "read"},
            "output_write": {"status": "written"},
        }

    def test_all_required_denials_and_allowed_operations_pass(self):
        check_probe(self.successful_probe())

    def test_missing_file_allowed_outside_access_or_broken_workload_fails(self):
        for key, value in (
            ("outside_read", {"error": "FileNotFoundError", "errno": 2}),
            ("outside_read", {"status": "read"}),
            ("outside_write", {"status": "written"}),
            ("data_write", {"status": "written"}),
            ("data_read", {"error": "PermissionError", "errno": 1}),
            ("output_write", {"error": "PermissionError", "errno": 1}),
            ("private_read", {}),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check_probe({**self.successful_probe(), key: value})


if __name__ == "__main__":
    unittest.main()
