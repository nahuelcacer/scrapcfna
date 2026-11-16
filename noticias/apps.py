import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class NoticiasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'noticias'

    def ready(self):
        from django.conf import settings

        if not settings.SCRAPE_VERIFY_SSL:
            # Un solo aviso al arrancar en vez de un InsecureRequestWarning por petición.
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning(
                "DJANGO_SCRAPE_VERIFY_SSL=0: no se verifica el certificado TLS de cfna.org.ar. "
                "Usar solo como parche temporal."
            )
