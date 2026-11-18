from django import forms


class ImageUploadForm(forms.Form):
    images = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'multiple': True,
            'accept': '.jpg,.jpeg,.png,.webp',
            'class': 'form-control',
            'id': 'imageUploadInput',
        }),
        label='Select Images',
    )
