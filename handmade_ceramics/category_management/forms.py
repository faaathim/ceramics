from django import forms
from .models import Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image', 'is_listed']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError("Name cannot be empty.")
        return name

class CategorySearchForm(forms.Form):
    q = forms.CharField(required=False, label='Search', widget=forms.TextInput(attrs={'placeholder': 'Search by name or description'}))
