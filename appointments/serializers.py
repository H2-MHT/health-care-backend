from rest_framework import serializers
from datetime import datetime
from .models import Appointment

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
            data['new_date_time'] = datetime.combine(day, time)
        except ValueError:
            raise serializers.ValidationError("Invalid day or time format.")
        
        return data
