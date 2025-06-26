from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from datetime import datetime, timedelta
from events.models import Event
from django.contrib.auth import get_user_model
from django.conf import settings
import json
import tempfile
from PIL import Image
import os

User = get_user_model()


class EventAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test users
        self.user_a = User.objects.create_user(
            email="user_a@example.com",
            password="password123",
            first_name="User",
            last_name="A",
        )

        self.user_b = User.objects.create_user(
            email="user_b@example.com",
            password="password123",
            first_name="User",
            last_name="B",
        )

        # Create 15 test events for pagination testing
        self.events = []
        for i in range(15):
            event = Event.objects.create(
                name=f"Event {i+1}",
                date=datetime.now() + timedelta(days=i + 1),
                location="Location" if i % 2 == 0 else "Nairobi",
                description=f"Description for event {i+1}",
                organizer=self.user_a,
            )
            self.events.append(event)

        # URLs
        self.list_url = reverse("event-list-create")
        self.detail_url = reverse("event-detail", args=[self.events[0].id])
        self.invalid_detail_url = reverse(
            "event-detail", args=[999]
        )  # Non-existent event

    def test_get_all_events(self):
        """Test retrieving all events with pagination"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check pagination structure
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

        # Check count and first page results
        self.assertEqual(response.data["count"], 15)
        self.assertEqual(len(response.data["results"]), 10)

        # Check second page
        next_page_url = response.data["next"]
        self.assertIsNotNone(next_page_url)

        # Extract the relative URL from the absolute URL
        if next_page_url.startswith("http"):
            next_page_url = next_page_url.split("/", 3)[-1]

        second_page_response = self.client.get(next_page_url)
        self.assertEqual(second_page_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page_response.data["results"]), 5)

    def test_get_single_event(self):
        """Test retrieving a single event"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.events[0].name)
        self.assertEqual(response.data["location"], self.events[0].location)
        # Check that the organizer field is included in the response
        self.assertEqual(response.data["organizer"], self.user_a.email)

    def test_get_invalid_event(self):
        """Test retrieving a non-existent event"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(self.invalid_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_event(self):
        """Test creating a new event"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        data = {
            "name": "New Event",
            "date": (datetime.now() + timedelta(days=5)).isoformat(),
            "location": "Accra",
            "description": "A new test event",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 16)  # 15 from setUp + 1 new

        # Check that the organizer is set correctly
        self.assertEqual(Event.objects.get(name="New Event").organizer, self.user_a)

    def test_update_event(self):
        """Test updating an event"""
        # Authenticate as user_a (the organizer of the event)
        self.client.force_authenticate(user=self.user_a)

        data = {
            "name": "Updated Event",
            "date": self.events[0].date.isoformat(),
            "location": "Updated Location",
            "description": "Updated description",
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.events[0].refresh_from_db()
        self.assertEqual(self.events[0].name, "Updated Event")
        self.assertEqual(self.events[0].location, "Updated Location")

    def test_delete_event(self):
        """Test deleting an event as the organizer"""
        # Authenticate as user_a (the organizer of the event)
        self.client.force_authenticate(user=self.user_a)

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Event.objects.count(), 14)  # 15 from setUp - 1 deleted

    def test_delete_event_as_non_organizer(self):
        """Test that a non-organizer cannot delete an event"""
        # Authenticate as user_b (not the organizer of the event)
        self.client.force_authenticate(user=self.user_b)

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Event.objects.count(), 15)  # No event should be deleted

    def test_filter_by_location(self):
        """Test filtering events by location"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        url = f"{self.list_url}?location=Nairobi"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # With pagination, we need to check the results key
        self.assertIn("results", response.data)

        # Count how many events have location=Nairobi in our setup
        nairobi_count = sum(1 for event in self.events if event.location == "Nairobi")
        self.assertEqual(response.data["count"], nairobi_count)

        # Check that all returned events have the correct location
        locations = [event["location"] for event in response.data["results"]]
        self.assertTrue(all(location == "Nairobi" for location in locations))

    def test_filter_by_name(self):
        """Test filtering events by name"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        # Create a specific event with a unique name for this test
        specific_event = Event.objects.create(
            name="Specific Test Event",
            date=datetime.now() + timedelta(days=100),
            location="Test Location",
            description="A specific test event for name filtering",
            organizer=self.user_a,
        )

        url = f"{self.list_url}?name=Specific Test Event"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # With pagination, we need to check the results key
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Specific Test Event")

    def test_search_functionality(self):
        """Test the search functionality across name, description, and location fields"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        # Create three distinct events for search testing
        python_conference = Event.objects.create(
            name="Python Conference",
            date=datetime.now() + timedelta(days=30),
            location="Conference Center",
            description="A gathering of developers.",
            organizer=self.user_a,
        )

        music_festival = Event.objects.create(
            name="Music Festival",
            date=datetime.now() + timedelta(days=45),
            location="City Park",
            description="Live bands and python-like stage decorations.",
            organizer=self.user_a,
        )

        art_show = Event.objects.create(
            name="Art Show",
            date=datetime.now() + timedelta(days=60),
            location="Art Gallery",
            description="Local artists exhibition.",
            organizer=self.user_a,
        )

        # Test search for "Python" - should return two events
        url = f"{self.list_url}?search=Python"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that exactly two events are returned
        self.assertEqual(response.data["count"], 2)

        # Get the names of the returned events
        event_names = [event["name"] for event in response.data["results"]]

        # Check that the correct events are returned
        self.assertIn("Python Conference", event_names)
        self.assertIn("Music Festival", event_names)
        self.assertNotIn("Art Show", event_names)

        # Test search for "developer" - should return one event
        url = f"{self.list_url}?search=developer"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that exactly one event is returned
        self.assertEqual(response.data["count"], 1)

        # Check that the correct event is returned
        self.assertEqual(response.data["results"][0]["name"], "Python Conference")

    def test_create_event_with_image(self):
        """Test creating a new event with an image"""
        # Authenticate as user_a
        self.client.force_authenticate(user=self.user_a)

        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_image:
            # Create a simple image
            image = Image.new("RGB", (100, 100), color="red")
            image.save(temp_image, format="JPEG")
            temp_image.flush()

            # Prepare event data
            data = {
                "name": "Event With Image",
                "date": (datetime.now() + timedelta(days=5)).isoformat(),
                "location": "Virtual",
                "description": "An event with a promotional image",
            }

            # Open the image file in binary mode
            with open(temp_image.name, "rb") as image_file:
                # Make a multipart/form-data request with the image
                response = self.client.post(
                    self.list_url,
                    data={"image": image_file, **data},
                    format="multipart",
                )

            # Clean up the temporary file
            os.unlink(temp_image.name)

        # Assert that the event was created successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert that the event has an image URL
        self.assertIn("image", response.data)
        self.assertIsNotNone(response.data["image"])

        # Verify the event was saved in the database with the image
        event = Event.objects.get(name="Event With Image")
        self.assertTrue(event.image)
        self.assertTrue(
            os.path.exists(os.path.join(settings.MEDIA_ROOT, event.image.name))
        )
