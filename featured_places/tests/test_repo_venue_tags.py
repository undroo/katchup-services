from __future__ import annotations

import unittest

from featured_places.repo import BADMINTON_COURT_VENUE_TAGS, venue_rows_to_featured_payloads


class TestVenueRowsToFeaturedPayloads(unittest.TestCase):
    def test_includes_canonical_tags(self) -> None:
        rows = venue_rows_to_featured_payloads(
            [
                {
                    "site_key": "botany",
                    "venue_name": "BadmintonWorx Botany",
                    "venue_timezone": "Australia/Sydney",
                }
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tags"], list(BADMINTON_COURT_VENUE_TAGS))
        self.assertEqual(rows[0]["court_site_key"], "botany")
        self.assertEqual(rows[0]["kind"], "badminton_court")


if __name__ == "__main__":
    unittest.main()
