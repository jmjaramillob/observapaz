from rest_framework.routers import DefaultRouter

from .views_api import (
    CasoVictimizanteViewSet,
    EnvioODKViewSet,
    ObservatorioViewSet,
    TipoHechoViewSet,
)

router = DefaultRouter()
router.register("observatorios", ObservatorioViewSet)
router.register("tipos-hecho", TipoHechoViewSet)
# Estos dos calculan su queryset en get_queryset() (según el usuario que
# consulta), así que el router no puede adivinar el basename solo y hay
# que indicárselo.
router.register("casos", CasoVictimizanteViewSet, basename="caso")
router.register("envios-odk", EnvioODKViewSet, basename="envioodk")

urlpatterns = router.urls
