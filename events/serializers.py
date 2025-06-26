from rest_framework import serializers
from .models import Event, Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    """

    class Meta:
        model = Category
        fields = ["id", "name"]


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for the Event model.
    """

    categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True, required=False
    )

    # Display category names when reading an event
    category_names = serializers.SerializerMethodField()

    # Display organizer email
    organizer = serializers.ReadOnlyField(source="organizer.email")

    def get_category_names(self, obj):
        return [category.name for category in obj.categories.all()]

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "date",
            "location",
            "description",
            "image",
            "categories",
            "category_names",
            "created_at",
            "updated_at",
            "organizer",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "category_names",
            "organizer",
        ]
