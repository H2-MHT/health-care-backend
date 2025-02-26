from rest_framework import serializers
from chat.models import *


class ChatRoomSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="receiver.first_name")
    last_name = serializers.CharField(source="receiver.last_name")
    profile_picture = serializers.URLField(source="receiver.profile_picture")
    is_online = serializers.URLField(source="receiver.is_online")
    last_seen = serializers.URLField(source="receiver.last_activity")

    class Meta:
        model = ChatRoom
        fields = "__all__"
        extra_fields = (
            "first_name",
            "last_name",
            "profile_picture",
            "is_online",
            "last_seen",
        )
        read_only_fields = ('last_update', 'doc')


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['message', 'doc', 'seen']

    def to_representation(self, instance):
        user = self.context["user"]
        data = super().to_representation(instance)
        data["doc"] = instance.doc.strftime("%Y-%m-%d %H:%M:%S")
        data["send"] = instance.sender == user
        return data

