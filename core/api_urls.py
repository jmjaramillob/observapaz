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
router.register("registros", RegistroIndicadorViewSet)
router.register("envios-odk", EnvioODKViewSet)

urlpatterns = router.urls
