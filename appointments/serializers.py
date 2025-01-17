from rest_framework import serializers
from datetime import datetime
from pytz import timezone
from .models import Appointment, Chat, Call, Message


class RescheduleAppointmentSerializer(serializers.ModelSerializer):
    day = serializers.DateField(input_formats=['%d-%m-%Y'])  # DD-MM-YYYY format
    time = serializers.TimeField(input_formats=['%H:%M'])  # 24-hour format HH:mm
    day = serializers.DateField(input_formats=['%d-%m-%Y'])  # DD-MM-YYYY format
    time = serializers.TimeField(input_formats=['%H:%M'])  # 24-hour format HH:mm

    class Meta:
        model = Appointment
        fields = ['day', 'time']
    def validate(self, data):
        day = data.get('day')
        time = data.get('time')
        try:
            naive_datetime = datetime.combine(day, time)
            data['new_date_time'] = naive_datetime
            data['new_date_time'] = naive_datetime
        except ValueError:
            raise serializers.ValidationError("Invalid day or time format. Please use DD-MM-YYYY for the date and HH:MM for the time. Please use DD-MM-YYYY for the date and HH:MM for the time.")
                
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
