from django import forms
from category_management.models import Category

SORT_CHOICES = [
    ('', 'Default'),
    ('price_asc', 'Price: low to high'),
    ('price_desc', 'Price: high to low'),
    ('name_asc', 'Name: A → Z'),
    ('name_desc', 'Name: Z → A'),
    ('newest', 'New arrivals'),
    # optionally: ('popularity', 'Popularity'), ('rating', 'Avg rating')
]

class ShopFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Search', widget=forms.TextInput(attrs={'placeholder': 'Search products'}))
    category = forms.ChoiceField(required=False)
    price_min = forms.DecimalField(required=False, min_value=0)
    price_max = forms.DecimalField(required=False, min_value=0)
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)
    page = forms.IntegerField(required=False, min_value=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # populate category choices from Category model (only listed & non-deleted)
        cats = Category.objects.filter(is_listed=True).order_by('name')
        choices = [('', 'All Categories')] + [(str(c.id), c.name) for c in cats]
        self.fields['category'].choices = choices
