from django.db import models

# Create your models here.
class Law(models.Model):
    law_name = models.CharField(max_length=255)
    law_description = models.TextField()
    registration_number = models.CharField(max_length=50, default=None)
    created_at = models.DateTimeField(auto_now_add=False)  # Automatically sets the field to now when the object is created

    def __str__(self):
        return self.law_name