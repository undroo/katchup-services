from app.scrapers.yepbooking import YepBookingSiteConfig

ABDC_ALEXANDRIA_CONFIG = YepBookingSiteConfig(
    site_key="abdc_alexandria",
    venue_name="Australia Badminton Development Centre (Alexandria)",
    base_url="https://australia-badminton-development-centre.yepbooking.com.au",
    sport_id=3,  # Court hire: "Alexandria" tab in ajax.showTabs (lessons/social/tournament are other ids)
    timezone="Australia/Sydney",
)

__all__ = ["ABDC_ALEXANDRIA_CONFIG"]
