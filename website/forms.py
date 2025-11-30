from django import forms

ALLOWED_EXTS = {".csv", ".xlsx", ".xls"}
SUBSEG_ALLOWED_EXTS = ALLOWED_EXTS.copy()
SUBSEG_MAX_ROWS = 25


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


class UploadSubSegmentsForm(forms.Form):
    segment = forms.CharField(
        label="Select segment",
        max_length=16,
        help_text="Start typing to search for an existing segment code."
    )
    start_row = forms.IntegerField(
        min_value=2,
        label="Row range start",
        help_text="First spreadsheet row that contains the sub-segment data (usually 2)."
    )
    end_row = forms.IntegerField(
        min_value=2,
        label="Row range end",
        help_text=f"Last spreadsheet row to include (max span {SUBSEG_MAX_ROWS} rows)."
    )
    segment_code_file = forms.FileField(
        label="Segment Code",
        help_text="Upload the spreadsheet (.csv, .xlsx, .xls)."
    )

    def clean_segment(self):
        return (self.cleaned_data["segment"] or "").strip()

    def clean_segment_code_file(self):
        f = self.cleaned_data["segment_code_file"]
        name = (f.name or "").lower()
        if not any(name.endswith(ext) for ext in SUBSEG_ALLOWED_EXTS):
            raise forms.ValidationError("File must be .csv, .xlsx, or .xls")
        if f.size and f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 5 MB).")
        return f

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_row")
        end = cleaned.get("end_row")
        if start and end:
            if end < start:
                self.add_error("end_row", "Row range end must be greater than or equal to the start.")
            elif (end - start + 1) > SUBSEG_MAX_ROWS:
                self.add_error(
                    "end_row",
                    f"Please select at most {SUBSEG_MAX_ROWS} rows at a time."
                )
        return cleaned
