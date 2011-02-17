from django import forms

class CollectionSelectForm(forms.Form):
    collections = forms.MultipleChoiceField()
    def __init__(self, group_object=None, extra_fields=None, *args, **kwargs):
       super(CollectionSelectForm, self).__init__(*args, **kwargs)
       choices = tuple((number,c[0]) for number, c in enumerate(group_object.get_newsletter_receiver_collections()))
       self.fields['collections'].choices = choices
       for key, field in extra_fields.items():
           self.fields[key] = field
