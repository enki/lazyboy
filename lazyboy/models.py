from lazyboy.record import Record
from lazyboy.key import Key
import simplejson as json

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
        return self.decode(instance.get(self.name, self._get_default()))

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
            value = self._get_default()

        return value

    def _get_default(self):
        if callable(self.default):
            return self.default()
        else:
            return self.default


class CharField(Field):
    pass

StringField = CharField

class KeyField(CharField):
    required = True

    def __init__(self, **kwargs):
        if 'required' in kwargs and kwargs['required'] == False:
            raise ValueError('KeyField must be a required field.')

        CharField.__init__(self, **kwargs)


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
            ret.update(value)
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


        fields.update(new_fields)

        for attrname, field in fields.items():
            if isinstance(field, KeyField):
                # Add _key_field attr so we know what the key is
                if '_key_field' in attrs:
                    raise FieldError("Multiple key fields defined for " 
                        "model '%s'" % name)
                attrs['_key_field'] = attrname
 

        if 'key' in fields:
            raise AttributeError("Models cannot have field named 'key'.")

        attrs['fields'] = fields
        new_cls = super(ModelType, cls).__new__(cls, name, bases, attrs)

        if '_key_field' not in new_cls.__dict__:
            raise NameError("%s is missing a KeyField." % name)

        for field, value in new_fields.items():
            setattr(new_cls, field, value)
 
        if not hasattr(new_cls, 'Meta'):
            raise Exception("Class has no Meta definition.")

        return new_cls


class Model(Record):
    __metaclass__ = ModelType

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)

        if self._key_field in kwargs and len(kwargs) == 1:
            self.load(self.key)
        elif len(kwargs) > 1:
            for key, value in kwargs.items():
                if key in self.fields:
                    setattr(self, key, value)
                else:
                    raise TypeError, "Unexpected keyword arguments '%s'" % key

    def get_key(self):
        return Key(keyspace=self.Meta.keyspace, 
            key=Record.sanitize(self, self[self._key_field]),
            column_family=self.Meta.column_family)

    def set_key(self, key):
        pass

    key = property(get_key, set_key)

    def _clean(self):
        map(self.__delitem__, self.keys())
        self._original, self._columns = {}, {}
        self._modified, self._deleted = {}, {}

    def save(self):
        for name, field in self.fields.items():
            if name not in self:
                if field.default != None:
                    self[name] = getattr(self, name)
                elif field.required:
                    raise ValueError("Missing required field '%s'." % name)

            if name in self:
                field.validate(self[name])

        # data = dict([(k, self.fields[k].encode(v)) for k, v in self.items()])

        Record.save(self)

    def sanitize(self, value):
        return value

    def delete(self):
        Record.remove(self)

    def _marshal(self):
        result = Record._marshal(self)

        changed = []
        for col in result['changed']:
            col.value = self.fields[col.name].encode(col.value)
            changed.append(col)

        result['changed'] = tuple(changed)

        return result

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
