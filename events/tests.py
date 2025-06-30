from django.test import TestCase

# Create your tests here.
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from events.models import Event # Make sure to adjust this import based on your app name
from datetime import datetime, timedelta

# Get the User model
User = get_user_model()

# --- Fixtures ---
# Fixtures provide reusable objects for your tests.
# pytest-django provides the 'db' fixture which ensures database access for tests.

@pytest.fixture
def api_client():
    """A Django REST Framework API client."""
    return APIClient()

@pytest.fixture
def regular_user(db):
    """A regular user for testing authentication."""
    return User.objects.create_user(username='testuser', email='test@example.com', password='password123')

@pytest.fixture
def organizer_user(db):
    """An organizer user for creating events."""
    return User.objects.create_user(username='organizer', email='organizer@example.com', password='password123')

@pytest.fixture
def event_data():
    """Sample data for creating an event."""
    return {
        "name": "Sample Event",
        "description": "This is a test event.",
        "location": "Test City",
        "start_date": (datetime.now() + timedelta(days=7)).isoformat(), # Future date
        "end_date": (datetime.now() + timedelta(days=8)).isoformat(),   # Future date
        "categories": [] # Assuming categories can be empty or you'd pass IDs
    }

@pytest.fixture
def another_event(db, organizer_user):
    """Creates another event for listing tests."""
    return Event.objects.create(
        name="Another Event",
        description="Just another test event.",
        location="Another City",
        start_date=datetime.now() + timedelta(days=10),
        end_date=datetime.now() + timedelta(days=11),
        organizer=organizer_user
    )


# --- Tests for EventListCreateView ---

def test_list_events_authenticated(api_client, regular_user, event_data, another_event):
    """
    Test that an authenticated user can list events.
    """
    api_client.force_authenticate(user=regular_user) # Authenticate the client
    url = reverse('event-list-create') # 'event-list-create' is a common name for ListCreateAPIView via DRF routers

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == Event.objects.count() 
    event_names = [event['name'] for event in response.data]
    assert event_data['name'] in event_names or another_event.name in event_names


def test_create_event_authenticated(api_client, organizer_user, event_data):
    """
    Test that an authenticated organizer can create an event.
    """
    api_client.force_authenticate(user=organizer_user)
    url = reverse('event-list-create')

    initial_event_count = Event.objects.count()
    response = api_client.post(url, event_data, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert Event.objects.count() == initial_event_count + 1

    new_event = Event.objects.get(id=response.data['id'])
    assert new_event.name == event_data['name']
    assert new_event.organizer == organizer_user 

def test_create_event_unauthenticated(api_client, event_data):
    """
    Test that an unauthenticated user cannot create an event.
    """
    url = reverse('event-list-create')

    initial_event_count = Event.objects.count()
    response = api_client.post(url, event_data, format='json')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED 
    assert Event.objects.count() == initial_event_count 

def test_list_events_unauthenticated(api_client):
    """
    Test that an unauthenticated user cannot list events (due to IsAuthenticated permission).
    """
    url = reverse('event-list-create')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED