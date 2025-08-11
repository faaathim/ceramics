from django import forms
from product.models import Product
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'description', 'category', 'image', 'is_listed']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Product.objects.filter(name__iexact=name, is_deleted=False).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("A product with this name already exists.")
        return name

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Image size should be less than 2MB.")
        return image

    def save(self, commit=True):
        instance = super().save(commit=False)
        image = self.cleaned_data.get('image')

        if image and not image.name.startswith('cropped_'):
            img = Image.open(image)
            img = img.convert("RGB")
            img = img.resize((800, 800))
            buffer = BytesIO()
            img.save(fp=buffer, format='JPEG')
            file_name = 'cropped_' + image.name.split('.')[0] + '.jpg'
            instance.image.save(file_name, ContentFile(buffer.getvalue()), save=False)

        if commit:
            instance.save()
        return instance
