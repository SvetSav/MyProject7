from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from .models import Course, Lesson, Subscription
from .validators import YouTubeOnlyValidator


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = "__all__"
        validators = [
            YouTubeOnlyValidator(field="video_link"),
        ]


class CourseSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "preview",
            "description",
            "lessons_count",
            "lessons",
            "is_subscribed",
        )

    @extend_schema_field(OpenApiTypes.INT)
    def get_lessons_count(self, obj):
        return obj.lessons.count()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, course=obj
            ).exists()
        return False
