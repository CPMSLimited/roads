from django import forms

ALLOWED_EXTS = {".csv", ".xlsx", ".xls"}

class UploadSegmentsForm(forms.Form):
    segment_file = forms.FileField(label="Attach file")
    auto_index = forms.BooleanField(
        required=False,
        initial=False,
        help_text="If enabled, assign next index per route for new segments whose index is blank."
    )

    def clean_segment_file(self):
        f = self.cleaned_data["segment_file"]
        name = (f.name or "").lower()
        if not any(name.endswith(ext) for ext in ALLOWED_EXTS):
            raise forms.ValidationError("File must be .csv, .xlsx, or .xls")
        if f.size and f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 10 MB).")
        return f
