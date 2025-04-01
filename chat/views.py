from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from chat.models import *
from django.db.models import Q
from chat.serializers import *


class ChatRoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
            try:
                user = request.user
                rooms = ChatRoom.objects.filter(Q(sender=user) | Q(receiver=user)).order_by(
                    "-last_update"
                )
                serializer = GetChatRoomSerializer(rooms, many=True, context={"request": request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    def post(self, request, *args, **kwargs):
        """Create or get a chat room between two users."""
        try:
            sender = request.user
            receiver_id = request.data.get("receiver_id")

            if not receiver_id:
                return Response(
                    {"error": "Receiver ID is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            receiver = User.objects.filter(id=receiver_id).first()
            if not receiver:
                return Response(
                    {"error": "Receiver not found."}, status=status.HTTP_404_NOT_FOUND
                )

            room = ChatRoom.objects.filter(
                Q(sender=sender, receiver=receiver) |
                Q(sender=receiver, receiver=sender)
            ).first()

            if not room:
                room = ChatRoom.objects.create(room_name=f"room-{sender.id}-{receiver_id}", sender=sender, receiver=receiver)
                

            rooms = ChatRoom.objects.filter(
                Q(sender=sender) | Q(receiver=sender)
            ).order_by("-last_update")
            serializer = ChatRoomSerializer(rooms, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChatMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id, *args, **kwargs):
        try:
            user = request.user
            room = ChatRoom.objects.filter(id=room_id).first()
            messages = Message.objects.filter(room=room).order_by("doc")

            Message.objects.filter(room=room, receiver=user, seen=False).update(seen=True)

            serializer = ChatMessageSerializer(
                messages, many=True, context={"user": user}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
