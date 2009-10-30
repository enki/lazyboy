# Python imports
import unittest
import time
import logging
from lazyboy import models
from lazyboy import connection

NOW = int(time.time())

connection.add_pool('Tests', ['10.0.1.4:9160'])

class ModelTestCase(unittest.TestCase):
    pass


class TestModelInheritance(ModelTestCase):
    def test_inheritance(self):
        class ParentModel(models.Model):
            class Meta:
                keyspace = "ParentModels"
                column_family = "ParentModel"

            id = models.KeyField()
            name = models.CharField()

        class ChildModel(ParentModel):
            pass


class TestField(ModelTestCase):
    class MyModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyModelFamily'
    
        id = models.KeyField()
        name = models.CharField(required=True)
        # Don't set or change address, and don't remove it from this test
        # this validates adding a non-required field to a Model that never 
        # gets used
        address = models.CharField(required=False)
        date_created = models.IntegerField(default=NOW) 

    class MyDefaultModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyModelFamily'
    
        id = models.KeyField()
        date_created = models.IntegerField(default=time.time) 
    
    class MyChoicesModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyChoicesModelFamily'
    
        CHOICES = (
            'person', 'place', 'thing', 'media'
        )
    
        id = models.KeyField()
        type = models.CharField(choices=CHOICES)

    def test_kwargs_in_init(self):
        """Assert that kwargs on init work."""
        m = self.MyModel(id="blah", name="Joe Stump", date_created=NOW)
        self.assertEquals("blah", m.id)
        self.assertEquals("Joe Stump", m.name)
        self.assertEquals(NOW, m.date_created)

    def test_init_defaults(self):
        """Assure that values set in different instances are different."""
        a = self.MyModel(id="a", name="Joe Stump", date_created=NOW)
        b = self.MyModel(id="b", name="Lance Weber", date_created=0)

        self.assertNotEquals(a.id, b.id)  
        self.assertNotEquals(a.name, b.name)
        self.assertNotEquals(a.date_created, b.date_created)

    def test_required_false(self):
        """Assure that required=False fields work properly."""
        m = self.MyModel(id="blah", name="Joe Stump", date_created=NOW)
        m.save()

        a = self.MyModel(id="blah")
        self.assertEquals(a.name, m.name)
        self.assertEquals(a.address, None)

    def test_option_required_fail(self):
        """Assure a missing required field fails properly."""
        m = self.MyModel()
        m.id = "blah"
        m.date_created = NOW

        self.failUnlessRaises(ValueError, m.save) 

    def test_sanitize(self):
        """Test sanitize for fields"""
        f = models.Field()
        value = "test"
        result = f.sanitize(value)
        self.assertEquals(value, result)

    def test_option_required_good(self):
        """Assure that required fields work properly."""
        m = self.MyModel()
        m.id = "blah"
        m.name = "Joe Stump"
        m.date_created = int(time.time())
        m.save()

    def test_option_default(self):
        """Assure that default values work properly."""
        m = self.MyModel()
        self.assertEquals(m.date_created, NOW)

    def test_option_default_callable(self):
        """Test field defaults"""
        m = self.MyDefaultModel()
        
        if m.date_created == None:
            self.fail("Default was not properly set.")

    def test_option_choices_good(self):
        """Assure that valid choices do not fail."""
        m = self.MyChoicesModel()
        m.id = "blah"
        m.type = 'person'
        m.save()

    def test_option_choices_fail(self):
        """Assure that invalid choices fail properly."""
        m = self.MyChoicesModel()
        m.id = "blah"
        m.type = 'totally-invalid'
        self.failUnlessRaises(ValueError, m.save) 

class TestBooleanField(ModelTestCase):
    class MyBooleanModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyBooleanModelFamily'
    
        id = models.KeyField()
        public = models.BooleanField()

    def test_boolean_field(self):
        """Test that when we store a bool we get back a bool."""
        m = self.MyBooleanModel()
        m.id = "blah"
        m.public = False
        m.save()

        a = self.MyBooleanModel(id="blah")
        self.assertTrue(isinstance(m.public, bool))
        self.assertEquals(m.public, a.public) 

    def test_boolean_field_true(self):
        """Test that when we store a bool True we get True back."""
        m = self.MyBooleanModel()
        m.id = "blah-true"
        m.public = True
        m.save()

        a = self.MyBooleanModel(id="blah-true")
        self.assertTrue(isinstance(m.public, bool))
        self.assertEquals(m.public, a.public) 

class TestCharField(ModelTestCase):
    class MyCharModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyCharFamily'
    
        id = models.KeyField()
        name = models.CharField()

    def test_char_field(self):
        """Test that strings are stored properly."""
        m = self.MyCharModel()
        m.id = "blah"
        m.name = "Joe Stump"
        m.save()

        a = self.MyCharModel(id="blah")
        self.assertEquals(m.name, a.name)
    
class TestIntegerField(ModelTestCase):
    class MyIntegerModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyIntegerFamily'
    
        id = models.KeyField()
        year = models.IntegerField()
        clicks = models.IntegerField(default=1000)

    def test_integer_field(self):
        """Test that the integer we store is the same when we get it back."""
        m = self.MyIntegerModel()
        m.id = "blah"
        m.year = 2009
        m.save()

        a = self.MyIntegerModel(id="blah")
        self.assertTrue(isinstance(m.year, int))
        self.assertEquals(m.year, a.year)

class TestFloatField(ModelTestCase):
    class MyFloatModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyFloatFamily'
    
        id = models.KeyField()
        price = models.FloatField()

    def test_float_field(self):
        """Test that the float we store is the same when we get it back."""
        m = self.MyFloatModel()
        m.id = "blah"
        m.price = 19.99 
        m.save()

        a = self.MyFloatModel(id="blah")
        self.assertTrue(isinstance(m.price, float))
        self.assertEquals(m.price, a.price)

class TestDictField(ModelTestCase):
    class MyDictModel(models.Model):
        class Meta:
            keyspace = 'Tests'
            column_family = 'MyDictFamily'
    
        id = models.KeyField()
        meta = models.DictField()

    def test_dict_field(self):
        """Test that the dict we store is the same when we get it back."""

        meta = {
            'first_name' : 'Joe',
            'last_name' : 'Stump'
        }

        m = self.MyDictModel()
        m.id = "blah"
        m.meta = meta
        m.save()

        a = self.MyDictModel(id="blah")
        self.assertTrue(isinstance(m.meta, dict))
        self.assertEquals(m.meta, a.meta)

        for key, val in meta.items():
            self.assertEquals(val, a.meta[key])


class MyUserModel(models.Model):
    class Meta:
        keyspace = 'Tests'
        column_family = 'MyUserFamily'
    
    username = models.KeyField()
    first_name = models.CharField()
    last_name = models.CharField()


class MyPostModel(models.Model):
    class Meta:
        keyspace = 'Tests'
        column_family = 'MyPostFamily'
 
    id = models.KeyField()
    user = models.RelatedField(MyUserModel)
    title = models.CharField()

class TestRelatedField(ModelTestCase):
    def test_dict_field(self):
        """Test field type RelatedField"""
        u = MyUserModel()
        u.username = "joestump"
        u.first_name = "Joe"
        u.last_name = "Stump"
        u.save()


        p = MyPostModel()
        p.id = 59
        p.user = u
        p.title = "Unit tests and stuff."
        p.save()

        a = MyPostModel(id=59)
        self.assertTrue(isinstance(a.user, MyUserModel))
        self.assertEquals(a.user.username, u.username)
        self.assertEquals(a.user.first_name, u.first_name)
        self.assertEquals(a.user.last_name, u.last_name)

class TestModel(ModelTestCase):
    class BlahModel(models.Model):
        class Meta:
            keyspace = "Tests"
            column_family = "BlahModelFamily"

        id = models.KeyField()
        name = models.CharField()
        urls = models.IntegerField()

    def setUp(self):
        self.args = {
            'id' : 55,
            'name' : 'asdfasdf',
            'urls' : 1
        }

    def test_equal(self):
        """Test equality function for Models"""
        a = self.BlahModel(**self.args)
        b = self.BlahModel(**self.args)
        self.assertEquals(a, b)
        self.assertTrue(a == b)
 
    def test_not_equal(self):
        """Test inequality function for Models"""
        a = self.BlahModel(**self.args)
        b = self.BlahModel(id=self.args['id'], name=self.args['name'])
        self.assertNotEquals(a, b) 
        self.assertFalse(a == b)


class Test_WFIError(ModelTestCase):
    class WFIErrorModel(models.Model):
        class Meta:
            keyspace = "Tests"
            column_family = "WFIErrorModelFamily"

        id = models.KeyField()
        name = models.CharField()
        counter = models.IntegerField()

    def test_intermittent(self):
        """Test for WFI Error"""
        id = '00001'
        name = 'alpha'
        counter = 100

        m = self.WFIErrorModel(id=id, name=name, counter=counter)
        self.assertEqual(id, m.id)
        self.assertEqual(name, m.name)
        self.assertEqual(counter, m.counter)

        m.save()

        self.assertEqual(id, m.id)
        self.assertEqual(name, m.name)
        self.assertEqual(counter, m.counter)

        a = self.WFIErrorModel(id=id)
        self.assertEqual(id, a.id)
        self.assertEqual(name, a.name)
        self.assert_(a.counter == 100)
        self.assert_(a.name == "alpha")


class TestModelHasKeyField(ModelTestCase):
    def test_model_without_a_key(self):
        try:
            class ModelWithoutKey(models.Model):
                class Meta:
                    keyspace = "Tests"
                    column_family = "WFIErrorModelFamily"

                name = models.CharField()
                counter = models.IntegerField()
        except Exception, e:
            return

        self.fail("A model without a _key_field passed.")

