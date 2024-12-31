from rest_framework import serializers
from datetime import datetime
from pytz import timezone
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
            # Create naive datetime
            naive_datetime = datetime.combine(day, time)

            # Convert to IST timezone
            ist = timezone('Asia/Kolkata')
            data['new_date_time'] = ist.localize(naive_datetime)

        except ValueError:
            raise serializers.ValidationError("Invalid day or time format.")
        
        return data
