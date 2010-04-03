from lazyboy import models

class User(models.Model):
    class Meta:
        keyspace = 'ModelTest'
        column_family = 'User'
    # All models must define one and only one KeyField.
    # This is the key that the record is stored under in
    # Cassandra.
    username = models.KeyField() 
    first_name = models.CharField()
    last_name = models.CharField()
    age = models.IntegerField()


# Create and save a record
user = User()
user.username = "joestump"
user.first_name = "Joe"
user.last_name = "Stump"
user.age = 29
user.save()

# Load a record
user = User(username="joestump")
print "Hello, %s %s!" % (user.first_name, user.last_name)

# Delete a record
user.delete()

