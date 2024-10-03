from django.db import models

# Create your models here.
class Law(models.Model):
    serial_number = models.CharField(max_length=50, unique=True)  # Ensures serial numbers are unique
    law_name = models.CharField(max_length=255)
    law_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically sets the field to now when the object is created

    def __str__(self):
        return self.law_name