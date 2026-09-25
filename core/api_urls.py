from rest_framework.routers import DefaultRouter

from .views_api import (
    CategoriaIndicadorViewSet,
    EnvioODKViewSet,
    IndicadorViewSet,
    ObservatorioViewSet,
    RegistroIndicadorViewSet,
)

router = DefaultRouter()
router.register("observatorios", ObservatorioViewSet)
router.register("categorias", CategoriaIndicadorViewSet)
router.register("indicadores", IndicadorViewSet)
# Estos dos calculan su queryset en get_queryset() (según el usuario que
# consulta), así que el router no puede adivinar el basename solo y hay
# que indicárselo.
router.register("registros", RegistroIndicadorViewSet, basename="registro")
router.register("envios-odk", EnvioODKViewSet, basename="envioodk")

urlpatterns = router.urls
