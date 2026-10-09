from django.db import models

class Author(models.Model):
    key = models.CharField(max_length=40 , unique=True)
    name = models.TextField(blank=True)
    last_modified = models.DateTimeField(db_index=True)

    def __str__(self):
        return self.name


class Work(models.Model):
    key = models.CharField(max_length=40 ,unique=True)
    title = models.TextField(blank = True )
    description = models.TextField(blank = True)
    subjects = models.JSONField(blank=True , default=list)
    first_publish_date = models.TextField(blank=True )
    last_modified = models.DateTimeField(db_index=True)
    authors = models.ManyToManyField(Author, through="WorkAuthor")

    def __str__(self):
        return self.title




class WorkAuthor(models.Model):
    work = models.ForeignKey(Work , on_delete=models.CASCADE)
    author = models.ForeignKey(Author , on_delete=models.CASCADE)
    position = models.IntegerField()
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["work", "author"],name="unique_work_author")
        ]
        ordering = ["position"]


    def __str__(self):
        return f"{self.work.title} - {self.author.name}"