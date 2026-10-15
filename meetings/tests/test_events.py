"""Events and meetings: listing, calendar feeds, officers adding,
editing, cancelling and deleting them, and their files."""

from datetime import timedelta

from django.utils import timezone

from core.tests.base import SiteTestCase
from meetings.models import Event, EventAttachment
from meetings.services import (
    get_feed_events, get_month_calendar, get_next_meeting, get_past_or_cancelled_meetings,
    get_upcoming_events, get_upcoming_meetings,
)


class EventTestCase(SiteTestCase):

    def make_event(self, title="Monthly Meeting", days=7, event_type=Event.TYPE_MEETING, **extra):
        return Event.objects.create(
            organization=self.org,
            title=title,
            event_type=event_type,
            starts_at=timezone.now() + timedelta(days=days),
            location="SNS Terminal",
            **extra,
        )


class EventServiceTests(EventTestCase):

    def test_upcoming_past_and_cancelled(self):
        upcoming = self.make_event("Upcoming")
        past = self.make_event("Past", days=-7)
        cancelled = self.make_event("Cancelled", is_cancelled=True)
        flyout = self.make_event("Fly-out", event_type=Event.TYPE_FLYOUT)
        self.assertEqual(list(get_upcoming_meetings(self.org)), [upcoming])
        self.assertEqual(set(get_upcoming_events(self.org)), {upcoming, flyout})
        self.assertEqual(set(get_past_or_cancelled_meetings(self.org)), {past, cancelled})
        # Feeds keep future cancelled events, so calendars can show them cancelled.
        self.assertIn(cancelled, get_feed_events(self.org))
        self.assertNotIn(past, get_feed_events(self.org))

    def test_next_meeting_skips_cancelled_and_other_types(self):
        self.make_event("Cancelled", days=1, is_cancelled=True)
        self.make_event("Fly-out", days=2, event_type=Event.TYPE_FLYOUT)
        later = self.make_event("Next", days=3)
        self.assertEqual(get_next_meeting(self.org), later)

    def test_month_calendar_places_events_on_their_day(self):
        event = self.make_event(days=0)
        today = timezone.localdate()
        calendar = get_month_calendar(self.org, today.year, today.month)
        days = [day for week in calendar["weeks"] for day in week]
        self.assertTrue(all(len(week) == 7 for week in calendar["weeks"]))
        today_cell = next(day for day in days if day["date"] == timezone.localtime(event.starts_at).date())
        self.assertIn(event, today_cell["events"])

    def test_month_calendar_prev_next_cross_years(self):
        calendar = get_month_calendar(self.org, 2027, 1)
        self.assertEqual(calendar["prev_month"], "2026-12")
        self.assertEqual(calendar["next_month"], "2027-02")
        self.assertEqual(calendar["month_label"], "January 2027")


class EventPageTests(EventTestCase):

    def test_list_and_detail_pages(self):
        meeting = self.make_event("January Meeting")
        flyout = self.make_event("Coast Fly-out", event_type=Event.TYPE_FLYOUT)
        self.assertContains(self.client.get("/meetings"), "January Meeting")
        self.assertNotContains(self.client.get("/meetings"), "Coast Fly-out")
        self.assertContains(self.client.get("/events"), "Coast Fly-out")
        self.assertContains(self.client.get(f"/meetings/{meeting.pk}"), "SNS Terminal")
        self.assertEqual(self.client.get(f"/meetings/{flyout.pk}").status_code, 200)
        self.assertEqual(self.client.get("/meetings/999999").status_code, 404)

    def test_next_meeting_panel(self):
        from core.models import InfoPanel

        InfoPanel.objects.create(organization=self.org, panel_type=InfoPanel.TYPE_NEXT_MEETING, title="Next Meeting")
        self.assertContains(self.client.get("/"), "No meetings currently scheduled")
        self.make_event("Soon")
        self.assertNotContains(self.client.get("/"), "No meetings currently scheduled")

    def test_ics_downloads(self):
        meeting = self.make_event("January Meeting", description="Agenda TBD")
        single = self.client.get(f"/meetings/{meeting.pk}/ics")
        self.assertEqual(single["Content-Type"], "text/calendar")
        self.assertIn(b"BEGIN:VEVENT", single.content)
        self.assertIn(b"January Meeting", single.content)
        for url in ("/meetings/feed.ics", "/events/feed.ics"):
            with self.subTest(url=url):
                feed = self.client.get(url)
                self.assertEqual(feed["Content-Type"], "text/calendar")
                self.assertIn(b"January Meeting", feed.content)

    def test_cancelled_event_marked_in_feed(self):
        self.make_event("Called Off", is_cancelled=True)
        self.assertIn(b"STATUS:CANCELLED", self.client.get("/meetings/feed.ics").content)


class EventManagementTests(EventTestCase):

    def setUp(self):
        self.site_admin_client = self.client_for(self.make_user("sa@example.com", role="site_admin"))
        self.member_client = self.client_for(self.make_user("member@example.com"))
        self.meeting = self.make_event("January Meeting")

    def form_data(self, **overrides):
        return {
            "event_type": "meeting", "title": "January Meeting", "starts_at": "2027-01-12T18:00",
            "location": "SNS Terminal", "description": "", **overrides,
        }

    def test_create(self):
        response = self.site_admin_client.post("/meetings/add", self.form_data(title="February Meeting"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Event.objects.get(title="February Meeting").organization, self.org)

    def test_edit(self):
        page = self.site_admin_client.get(f"/meetings/{self.meeting.pk}/edit")
        self.assertContains(page, "Edit Meeting")
        response = self.site_admin_client.post(f"/meetings/{self.meeting.pk}/edit", self.form_data(
            title="Jan Meeting (moved)", location="Hangar 2",
        ))
        self.assertRedirects(response, f"/meetings/{self.meeting.pk}", fetch_redirect_response=False)
        self.meeting.refresh_from_db()
        self.assertEqual((self.meeting.title, self.meeting.location), ("Jan Meeting (moved)", "Hangar 2"))

    def test_cancel_toggle(self):
        self.site_admin_client.post(f"/meetings/{self.meeting.pk}/cancel")
        self.meeting.refresh_from_db()
        self.assertTrue(self.meeting.is_cancelled)
        self.site_admin_client.post(f"/meetings/{self.meeting.pk}/cancel")
        self.meeting.refresh_from_db()
        self.assertFalse(self.meeting.is_cancelled)

    def test_delete_meeting_removes_files_and_returns_to_meetings(self):
        self.meeting.agenda = self.upload("agenda.pdf")
        self.meeting.minutes = self.upload("minutes.pdf")
        self.meeting.save()
        attachment = EventAttachment.objects.create(event=self.meeting, title="Report", file=self.upload("r.pdf"))
        files = [self.meeting.agenda.name, self.meeting.minutes.name, attachment.file.name]
        storage = self.meeting.agenda.storage
        response = self.site_admin_client.post(f"/meetings/{self.meeting.pk}/delete")
        self.assertEqual(response["Location"], "/meetings")
        self.assertFalse(Event.objects.exists())
        self.assertFalse(EventAttachment.objects.exists())
        self.assertFalse(any(storage.exists(name) for name in files))

    def test_delete_other_event_returns_to_events(self):
        flyout = self.make_event("Fly-out", event_type=Event.TYPE_FLYOUT)
        self.assertEqual(self.site_admin_client.post(f"/meetings/{flyout.pk}/delete")["Location"], "/events")

    def test_member_refused(self):
        pk = self.meeting.pk
        self.assertEqual(self.member_client.get(f"/meetings/{pk}/edit").status_code, 403)
        for action in ("delete", "cancel"):
            with self.subTest(action=action):
                self.assertEqual(self.member_client.post(f"/meetings/{pk}/{action}").status_code, 403)
        self.assertTrue(Event.objects.filter(pk=pk, is_cancelled=False).exists())

    def test_delete_and_cancel_require_post(self):
        for action in ("delete", "cancel"):
            with self.subTest(action=action):
                self.assertEqual(self.site_admin_client.get(f"/meetings/{self.meeting.pk}/{action}").status_code, 405)


class MeetingFileTests(EventTestCase):

    def setUp(self):
        self.site_admin_client = self.client_for(self.make_user("sa@example.com", role="site_admin"))
        self.member_client = self.client_for(self.make_user("member@example.com"))
        self.meeting = self.make_event("January Meeting")
        self.base = f"/meetings/{self.meeting.pk}"

    def test_agenda_upload_replace_and_download(self):
        self.site_admin_client.post(f"{self.base}/agenda", {"agenda": self.upload("a1.pdf", b"%PDF one")})
        self.meeting.refresh_from_db()
        first, storage = self.meeting.agenda.name, self.meeting.agenda.storage
        self.site_admin_client.post(f"{self.base}/agenda", {"agenda": self.upload("a2.pdf", b"%PDF two")})
        self.meeting.refresh_from_db()
        self.assertFalse(storage.exists(first))  # replaced file removed
        response = self.member_client.get(f"{self.base}/agenda/download")
        self.assertEqual(b"".join(response.streaming_content), b"%PDF two")

    def test_minutes_clear_removes_file(self):
        self.site_admin_client.post(f"{self.base}/minutes", {"minutes": self.upload("m.pdf")})
        self.meeting.refresh_from_db()
        name, storage = self.meeting.minutes.name, self.meeting.minutes.storage
        self.site_admin_client.post(f"{self.base}/minutes", {"minutes-clear": "on"})
        self.meeting.refresh_from_db()
        self.assertFalse(self.meeting.minutes)
        self.assertFalse(storage.exists(name))

    def test_agenda_and_minutes_need_login(self):
        self.meeting.agenda = self.upload("agenda.pdf")
        self.meeting.save()
        self.assertRedirectsToLogin(self.client.get(f"{self.base}/agenda/download"))
        self.assertEqual(self.member_client.get(f"{self.base}/minutes/download").status_code, 404)  # none uploaded

    def test_attachments(self):
        for title, name in (("Treasurer report", "report.xlsx"), ("Slides", "deck.pptx"), ("Photo", "pic.jpg")):
            response = self.site_admin_client.post(f"{self.base}/attachments/add", {
                "title": title, "file": self.upload(name, b"data"),
            })
            self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(self.meeting.attachments.values_list("title", flat=True)),
            ["Treasurer report", "Slides", "Photo"],
        )
        detail = self.member_client.get(self.base)
        self.assertContains(detail, "Treasurer report")
        self.assertNotContains(self.client.get(self.base), "Treasurer report")  # visitors don't see files

    def test_attachment_rejects_runnable_files(self):
        for name in ("page.html", "image.svg", "script.js"):
            with self.subTest(name=name):
                self.site_admin_client.post(f"{self.base}/attachments/add", {"title": "x", "file": self.upload(name)})
        self.assertFalse(EventAttachment.objects.exists())

    def test_attachment_download_and_remove(self):
        attachment = EventAttachment.objects.create(event=self.meeting, title="Report", file=self.upload("r.pdf"))
        url = f"{self.base}/attachments/{attachment.pk}"
        self.assertRedirectsToLogin(self.client.get(url))
        self.assertEqual(self.member_client.get(url).status_code, 200)
        other = self.make_event("Other")
        self.assertEqual(self.member_client.get(f"/meetings/{other.pk}/attachments/{attachment.pk}").status_code, 404)
        self.assertEqual(self.member_client.post(f"{url}/delete").status_code, 403)
        name, storage = attachment.file.name, attachment.file.storage
        self.site_admin_client.post(f"{url}/delete")
        self.assertFalse(EventAttachment.objects.exists())
        self.assertFalse(storage.exists(name))

    def test_member_cannot_upload(self):
        self.assertEqual(self.member_client.get(f"{self.base}/agenda").status_code, 403)
        self.assertEqual(self.member_client.get(f"{self.base}/attachments/add").status_code, 403)
