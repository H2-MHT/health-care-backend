from rest_framework import serializers
from datetime import datetime
from pytz import timezone
from .models import Appointment, Chat, Call, Message


class RescheduleAppointmentSerializer(serializers.ModelSerializer):
    day = serializers.DateField()
    time = serializers.TimeField(input_formats=['%I:%M%p'])  # Accepts formats like 11:00am

    class Meta:
        model = Appointment
        fields = ['day', 'time']

    def validate(self, data):
        day = data.get('day')
        time = data.get('time')

        # Combine day and time into a single datetime object
        try:
            # Create naive datetime
            naive_datetime = datetime.combine(day, time)

            # Convert to IST timezone
            ist = timezone('Asia/Kolkata')
            data['new_date_time'] = ist.localize(naive_datetime)

        except ValueError:
            raise serializers.ValidationError("Invalid day or time format.")

        return data


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class CallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Call
        fields = '__all__'


class ChatSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    calls = CallSerializer(many=True, read_only=True)

    class Meta:
        model = Chat
        fields = '__all__'
