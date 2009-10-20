from lazyboy.record import Record
from lazyboy.key import Key


class Field(object):
    def __init__(self, **kwargs):
        if 'required' in kwargs:
            if kwargs['required'] == True:
                self.required = True
            else:
                self.required = False
        elif not hasattr(self, 'required'):
            self.required = True

        if 'default' in kwargs:
            self.default = kwargs['default']
        else:
            self.default = None

        self.options = kwargs

    def __set__(self, instance, value):
        instance[self.name] = self.sanitize(value)

    def __get__(self, instance, owner):
        return instance.get(self.name, self.default)

    def encode(self, value):
        if value.__class__ is unicode:
            return value.encode('utf-8')
        
        return str(value)

    def decode(self, value):
        return value

    def validate(self, value):
        if 'choices' in self.options and \
            value not in self.options['choices']:
            raise ValueError("%s is not in %s." % (value, 
                self.options['choices']))

    def sanitize(self, value):
        if value == None and self.default != None:
            if callable(self.default):
                value = self.default()
            else:
                value = self.default

        return value


class CharField(Field):
    pass


class KeyField(CharField):
    required = True

    def __init__(self, **kwargs):
        if 'required' in kwargs and kwargs['required'] == False:
            raise ValueError('KeyField must be a required field.')

        CharField.__init__(self, **kwargs)

    def __set__(self, instance, value):
        instance[self.name] = Key(keyspace=instance.Meta.keyspace,
            column_family=instance.Meta.column_family, 
            key=self.sanitize(value))

    def __get__(self, instance, owner):
        if self.name in instance:
            return instance[self.name].key

        raise AttributeError("'%s' is not a valid attribute." % self.name)

class IntegerField(Field):
    decode = int


class FloatField(Field):
    decode = float


class BooleanField(Field):
    def encode(self, value):
        if value:
            return "1"

        return "0"

    def decode(self, value):
        if value == True or value == "1":
            return True

        return False


class DictField(Field):
    default = {}

    def encode(self, value):
        return json.dumps(value)

    def decode(self, value):
        if isinstance(value, dict):
            return value

        return json.loads(value)


class RelatedField(Field):
    required = True

    def __init__(self, cls, **kwargs):
        Field.__init__(self, **kwargs)
        self.cls = cls

    def encode(self, value):
        return value[self.cls._key_field]

    def decode(self, value):
        if isinstance(value, dict):
            ret = self.cls()
            ret.load(value)
            return ret

        args = {
            self.cls._key_field : value
        }

        return self.cls(**args)

    def validate(self, value):
        if not isinstance(value, self.cls):
            raise ValueError("%s is not a %s." % (value.__class__.__name__, 
                self.cls.__class__.__name__))


class ModelType(type):
    def __new__(cls, name, bases, attrs):
        parents = [b for b in bases if isinstance(b, ModelType)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super(ModelType, cls).__new__(cls, name, bases, attrs)

        fields = {}
 
        for base in bases:
            if isinstance(base, ModelType) and hasattr(base, 'fields'):
                fields.update(base.fields)
 
        new_fields = {}
 
        # Move all the class's attributes that are Fields to the fields set.
        for attrname, field in attrs.items():
            if not isinstance(field, Field):
                continue

            if attrname in fields:
                # Throw out any parent fields that the subclass defined as
                # something other than a field
                del fields[attrname]
                continue

            field.name = attrname
            new_fields[attrname] = field
            if isinstance(field, KeyField):
                # Add _key_field attr so we know what the key is
                if '_key_field' in attrs:
                    raise FieldError("Multiple key fields defined for " 
                        "model '%s'" % name)
                attrs['_key_field'] = attrname
 
        fields.update(new_fields)
        attrs['fields'] = fields
        new_cls = super(ModelType, cls).__new__(cls, name, bases, attrs)

        for field, value in new_fields.items():
            setattr(new_cls, field, value)
 
        return new_cls


class Model(Record):
    __metaclass__ = ModelType

    def __init__(self, **kwargs):
        if self._key_field in kwargs and len(kwargs) == 1:
            self.load(self._key())
        elif len(kwargs) > 1:
            for key, value in kwargs.items():
                if key in self.fields:
                    setattr(self, key, value)
                else:
                    raise TypeError, "Unexpected keyword arguments '%s'" % key

    @property
    def key(self):
        return Key(keyspace=self.Meta.keyspace, 
            key=self.fields[self._key_field],
            column_space=self.Meta.column_family)

    def save(self):
        for name, field in self.fields.items():
            if name not in self:
                if field.default != None:
                    self[name] = getattr(self, name)
                elif field.required:
                    raise ValueError("Missing required field '%s'." % name)

            if name in self:
                field.validate(self[name])

        data = dict([(k, self.fields[k].encode(v)) for k, v in self.items()])

        Record.save(self)

    def delete(self):
        self.remove()

    def update(self, arg=None, **kwargs):
        if arg:
            if hasattr(arg, 'keys'):
                for key in arg:
                    if key in self.fields:
                        setattr(self, key, self.fields[key].decode(arg[key]))
            else:
                for key, val in arg: 
                    if key in self.fields:
                        setattr(self, key, self.fields[key].decode(val))

        if kwargs:
            for key in kwargs: 
                if key in self.fields:
                    setattr(self, key, self.fields[key].decode(kwargs[key]))

    def __unicode__(self):
        repr = [("%s='%s'" % (k, f)) for k, f in self.items()]
        return "%s(%s)" % (self.__class__.__name__, ', '.join(repr))

    def __repr__(self):
        return self.__unicode__()
