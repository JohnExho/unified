from django.db import models

# Create your models here.
class Information(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        permissions = [
            ("access_information_management_system", "Can access Information Management system"),
        ]

    def __str__(self):
        return self.name