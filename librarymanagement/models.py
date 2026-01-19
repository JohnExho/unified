from django.db import models

# Create your models here.
class Library(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        permissions = [
            ("access_library_management_system", "Can access Library Management system"),
        ]

    def __str__(self):
        return self.name