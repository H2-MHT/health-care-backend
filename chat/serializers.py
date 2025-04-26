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


class GetChatRoomSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = (
            "id", "first_name", "last_name", "profile_picture", "is_online",
            "room_name", "sender", "receiver", "last_seen", "last_update", "doc"
        )

    def get_current_user(self):
        """Get the current logged-in user from the request context."""
        request = self.context.get("request")
        return request.user if request else None

    def get_other_user(self, obj):
        """Identify whether the current user is sender or receiver, and return the other user."""
        current_user = self.get_current_user()
        if current_user:
            return obj.receiver if obj.sender == current_user else obj.sender
        return None

    def get_first_name(self, obj):
        user = self.get_other_user(obj)
        return user.first_name if user else None

    def get_last_name(self, obj):
        user = self.get_other_user(obj)
        return user.last_name if user else None

    def get_profile_picture(self, obj):
        user = self.get_other_user(obj)
        if user and user.profile_picture:
            return user.profile_picture.url
        return None

    def get_is_online(self, obj):
        user = self.get_other_user(obj)
        return user.is_online if user else False

    def get_last_seen(self, obj):
        user = self.get_other_user(obj)
        return user.last_activity if user else None

    def to_representation(self, instance):
        """Swap sender and receiver in response if the current user is the receiver."""
        data = super().to_representation(instance)
        current_user = self.get_current_user()

        if current_user and instance.receiver == current_user:
            # Swap sender and receiver fields
            data["sender"], data["receiver"] = data["receiver"], data["sender"]

        return data