from django import forms

class CollectionSelectForm(forms.Form):
    collection = forms.ChoiceField()
    def __init__(self, group_object=None, *args, **kwargs):
       super(CollectionSelectForm, self).__init__(*args, **kwargs)
       self.fields['collection'].choices = group_object.get_newsletter_receiver_collections()
