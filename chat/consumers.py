from channels.generic.websocket import AsyncWebsocketConsumer
from users.models import User
from chat.models import ChatRoom, Message
from channels.db import database_sync_to_async
import json
from rest_framework_simplejwt.tokens import AccessToken, TokenError
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import async_to_sync


class ChatConsumer(AsyncWebsocketConsumer):

    @database_sync_to_async
    def update_last_activity(self, user, status):
        try:
            user.last_activity = timezone.localtime().now()
            user.is_online = status
            user.save()
            print(f"[DEBUG] updating user activity: {user}")
            async_to_sync(self.send_user_status)(user)
        except Exception as e:
            print(f"[ERROR] Error updating user activity: {str(e)}")

    @database_sync_to_async
    def verify_user(self):
        query_string = self.scope.get("query_string", b"").decode()
        token_key = None

        if "token=" in query_string:
            try:
                token_key = query_string.split("token=")[1]
            except IndexError:
                return None

        if token_key:
            try:
                token = AccessToken(token_key)
                user = User.objects.get(id=token["user_id"])
                self.sender = user
                print(f"[DEBUG] Token verified, sender: {user}")
                return user
            except User.DoesNotExist:
                print("[ERROR] User does not exist for this token.")
            except TokenError as e:
                print(f"[ERROR] Token verification failed: {str(e)}")
            return None

        return None

    @database_sync_to_async
    def verify_room(self):
        try:
            room = ChatRoom.objects.filter(
                Q(room_name=self.room_name)
                & (Q(sender=self.sender) | Q(receiver=self.sender))
            ).first()  # Get the first matching room

            if room:
                print(f"[DEBUG] Room verified: {room}")
                self.room = room
                self.receiver = (
                    room.receiver if room.sender == self.sender else room.sender
                )
                print(
                    f"[DEBUG] Verified sender: {self.sender}, Receiver: {self.receiver}"
                )
                return room
            else:
                print(f"[ERROR] User {self.sender} is not part of this chat room.")
                self.room = None
                self.receiver = None
                return None

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            self.room = None
            self.receiver = None
            return None

    async def connect(self):
        print("[DEBUG] Starting connect()")
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat-{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        print("[DEBUG] Accepting connection...")
        await self.accept()

        print("[DEBUG] Verifying user...")
        user = await self.verify_user()
        if not user:
            print("[DEBUG] User verification failed, closing...")
            await self.close()
            return

        print("[DEBUG] Verifying room...")
        room_valid = await self.verify_room()
        if not room_valid:
            print("[DEBUG] Room verification failed, closing...")
            await self.close()
            return

        print("[DEBUG] Updating last activity...")
        await self.update_last_activity(user, True)

    async def disconnect(self, code=None):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        user = self.sender
        if user:
            await self.update_last_activity(user, False)

    @database_sync_to_async
    def save_message(self, message):
        try:
            sender = self.sender
            receiver = self.receiver

            msg = Message.objects.create(
                room=self.room,
                sender=sender,
                receiver=receiver,
                message=message,
            )

            print(f"[DEBUG] Saved message from {sender} to {receiver}: {message}")
            return msg

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            return None

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
            action = data.get("action")

            print(f"[DEBUG] Received message: {data}")

            if action == "check_status":
                await self.send_user_status(self.receiver)

            elif action == "mark_seen":
                await self.mark_messages_seen()

            elif action == "chat_message":
                message = data.get("message", "")
                msg = await self.save_message(message)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": message,
                        "doc": msg.doc.strftime("%Y-%m-%d %H:%M:%S"),
                        "seen": msg.seen,
                        "user_id": msg.sender.id,
                    },
                )
        except Exception as e:
            print(f"[ERROR] Error in receive: {str(e)}")

    async def chat_message(self, event):
        print(f"[DEBUG] Broadcasting message: {event}")
        user_id = event.pop("user_id")
        event["send"] = self.sender.id == user_id
        await self.send(text_data=json.dumps(event))

    async def send_user_status(self, user):
        if user:
            status = {
                "type": "user_status",
                "is_online": user.is_online,
                "last_seen": (
                    user.last_activity.strftime("%Y-%m-%d %H:%M:%S")
                    if user.last_activity
                    else None
                ),
                "user_id": user.id,
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                status,
            )
        else:
            print(f"[ERROR] User {user.id} not found.")

    async def user_status(self, event):
        user_id = event.pop("user_id")
        user_type = "self" if self.sender.id == user_id else "receiver"
        event["user_type"] = user_type
        print(f"[DEBUG] Processed status update: {event}")
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def mark_messages_seen(self):
        try:
            updated_count = Message.objects.filter(
                room=self.room, receiver=self.sender, seen=False
            ).update(seen=True)
            print(
                f"[DEBUG] Marked {updated_count} messages as seen in room {self.room_name}"
            )
        except Exception as e:
            print(f"[ERROR] Error marking messages as seen: {str(e)}")
