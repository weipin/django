from django.db.models.fields.related import (
    create_many_to_many_intermediary_model,
    ManyToManyField, ManyToManyRel, RelatedField,
    RECURSIVE_RELATIONSHIP_CONSTANT, ReverseManyRelatedObjectsDescriptor,
)

from django.utils.functional import curry


class CustomManyToManyField(RelatedField):
    """
    Ticket #24104 - Need to have a custom ManyToManyField,
    which is not an inheritor of ManyToManyField.
    """
    many_to_many = True

    def __init__(self, to, db_constraint=True, swappable=True, **kwargs):
        try:
            to._meta
        except AttributeError:
            to = str(to)
        kwargs['rel'] = ManyToManyRel(
            self, to,
            related_name=kwargs.pop('related_name', None),
            related_query_name=kwargs.pop('related_query_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            symmetrical=kwargs.pop('symmetrical', to == RECURSIVE_RELATIONSHIP_CONSTANT),
            through=kwargs.pop('through', None),
            through_fields=kwargs.pop('through_fields', None),
            db_constraint=db_constraint,
        )
        self.swappable = swappable
        self.db_table = kwargs.pop('db_table', None)
        if kwargs['rel'].through is not None:
            assert self.db_table is None, "Cannot specify a db_table if an intermediary model is used."
        super(CustomManyToManyField, self).__init__(**kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        if self.rel.symmetrical and (self.rel.to == "self" or self.rel.to == cls._meta.object_name):
            self.rel.related_name = "%s_rel_+" % name
        super(CustomManyToManyField, self).contribute_to_class(cls, name, **kwargs)
        if not self.rel.through and not cls._meta.abstract and not cls._meta.swapped:
            self.rel.through = create_many_to_many_intermediary_model(self, cls)
        setattr(cls, self.name, ReverseManyRelatedObjectsDescriptor(self))
        self.m2m_db_table = curry(self._get_m2m_db_table, cls._meta)

    def get_internal_type(self):
        return 'ManyToManyField'

    # Copy those methods from ManyToManyField because they don't call super() internally
    contribute_to_related_class = ManyToManyField.__dict__['contribute_to_related_class']
    _get_m2m_attr = ManyToManyField.__dict__['_get_m2m_attr']
    _get_m2m_reverse_attr = ManyToManyField.__dict__['_get_m2m_reverse_attr']
    _get_m2m_db_table = ManyToManyField.__dict__['_get_m2m_db_table']


class InheritedManyToManyField(ManyToManyField):
    pass
