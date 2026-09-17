from django import forms

from core.models import Indicador, Observatorio, RegistroIndicador


class RegistroPublicoForm(forms.ModelForm):
    """
    Formulario público de captura. No requiere autenticación:
    cualquier persona con el enlace puede diligenciarlo desde su dispositivo.
    """

    latitud = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_latitud"}),
    )
    longitud = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_longitud"}),
    )

    class Meta:
        model = RegistroIndicador
        fields = ["indicador", "fecha", "valor", "fuente", "observaciones"]
        widgets = {
            "indicador": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "fuente": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Acta comunitaria, visita de campo"}
            ),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "indicador": "Indicador",
            "fecha": "Fecha del dato",
            "valor": "Valor registrado",
            "fuente": "Fuente de la información",
            "observaciones": "Observaciones",
        }

    def __init__(self, *args, observatorio=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Indicador.objects.select_related("observatorio").filter(activo=True)
        if observatorio is not None:
            qs = qs.filter(observatorio=observatorio)
        self.fields["indicador"].queryset = qs.order_by("observatorio__codigo", "nombre")

    def save(self, commit=True):
        from django.contrib.gis.geos import Point

        registro = super().save(commit=False)
        lat = self.cleaned_data.get("latitud")
        lon = self.cleaned_data.get("longitud")
        if lat is not None and lon is not None:
            registro.ubicacion = Point(lon, lat, srid=4326)
        if commit:
            registro.save()
        return registro
