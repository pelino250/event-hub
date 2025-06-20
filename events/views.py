from rest_framework import generics, permissions
from .models import Event
from .serializers import EventSerializer
from .permissions import IsOrganizerOrReadOnly

class EventListCreateView(generics.ListCreateAPIView):
    """
    Lists all upcoming events or creates a new event.

    Events can be filtered by `location` and `categories__name`.
    Full-text search is available via the `search` parameter.
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filterset_fields = ['location', 'categories__name']
    search_fields = ['^name', 'description', 'location']
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieves, updates, or deletes an event instance.

    Only the event organizer can update or delete the event.
    Authentication is required for all operations.
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrReadOnly]
