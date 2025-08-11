from django import forms
from category.models import Category
from image_cropping import ImageCropWidget

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image', 'cropping', 'is_listed']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'cropping': ImageCropWidget(),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        if not name:
            raise forms.ValidationError("Name cannot be empty.")

        # Case-sensitive uniqueness check (excluding current instance on edit)
        qs = Category.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A category with this exact name already exists (case-sensitive).")

        return name

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) > 500:
            raise forms.ValidationError("Description is too long (max 500 characters).")
        return description

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file too large (max 2MB).")
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError("Uploaded file is not an image.")
        return image
