# scrapcfna

API en Django REST Framework que scrapea las noticias de https://www.cfna.org.ar/noticias/ y las expone como JSON.

## Instalación

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py scrapear_noticias --paginas 3   # carga inicial (opcional)
python manage.py runserver
```

La API queda en `http://127.0.0.1:8000/api/v1/`.

## Endpoints

| Método | URL | Permiso | Descripción |
|--------|-----|---------|-------------|
| GET | `/api/v1/noticias/` | Público | Listado paginado (20 por página) de noticias guardadas |
| GET | `/api/v1/noticias/{id}/` | Público | Detalle de una noticia |
| GET | `/api/v1/noticias/page/{num}` | Público, 10/min por IP | Scrapea en vivo `cfna.org.ar/noticias/page/{num}/?et_blog`, guarda y devuelve esa página |
| POST | `/api/v1/noticias/scrape/` | Admin | Scrapea varias páginas y guarda las noticias |
| GET | `/api/v1/scrape-runs/` | Admin | Historial de ejecuciones del scraping (filtros `?estado=error`, `?origen=cron`) |

### `GET /api/v1/noticias/`

Parámetros de query:

| Parámetro | Ejemplo | Descripción |
|-----------|---------|-------------|
| `search` | `?search=revista` | Busca en título y resumen |
| `desde` / `hasta` | `?desde=2026-01-01&hasta=2026-06-30` | Rango de fechas de publicación |
| `categoria` | `?categoria=Portada` | Filtra por categoría |
| `ordering` | `?ordering=-fecha` | Ordena por `fecha` o `titulo` (`-` para descendente) |
| `page` | `?page=2` | Número de página del listado |

Respuesta:

```json
{
  "count": 29,
  "next": "http://127.0.0.1:8000/api/v1/noticias/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "wp_id": 10685,
      "titulo": "I FORO NACIONAL DE PLA – SECTOR NOTARIAL",
      "url": "https://www.cfna.org.ar/foropla/",
      "imagen_url": "https://www.cfna.org.ar/wp-content/uploads/2026/09/....jpg",
      "resumen": "El próximo 28 de octubre, ...",
      "fecha": "2026-09-30",
      "categorias": ["Noticias", "Portada"]
    }
  ]
}
```

### `GET /api/v1/noticias/page/{num}`

Funciona con o sin barra final. Cada llamada hace un pedido a cfna.org.ar, por eso tiene throttling.

```json
{ "page": 4, "count": 9, "results": [ ... ] }
```

Errores:

- `404`: la página no tiene noticias.
- `429`: se superó el límite de 10 pedidos por minuto (ver header `Retry-After`).
- `502`: no se pudo obtener la página desde cfna.org.ar.

### `POST /api/v1/noticias/scrape/`

Requiere un usuario admin (autenticación por sesión).

```json
{ "paginas": 3 }
```

`paginas` es opcional (por defecto 1, máximo 50). Respuesta:

```json
{ "creadas": 12, "actualizadas": 18 }
```

El scraping es idempotente: las noticias se identifican por `wp_id`, así que repetirlo actualiza en vez de duplicar.

## Scraping desde consola

```bash
python manage.py scrapear_noticias --paginas 5
```

## Scraping automático (Debian)

Un timer de systemd corre `scrapear_noticias --paginas 2 --origen cron` cada hora (con hasta 5 min de demora aleatoria). Cada ejecución queda registrada en `ScrapeRun` (admin y `/api/v1/scrape-runs/`).

Los units están en `deploy/systemd/` y asumen el proyecto en `/opt/scrapcfna`, un virtualenv en `/opt/scrapcfna/venv` y un usuario `scrapcfna`. Ajustá esas rutas si difieren.

```bash
sudo cp deploy/systemd/scrapcfna-scrape.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scrapcfna-scrape.timer

systemctl list-timers | grep scrapcfna        # próxima ejecución
sudo systemctl start scrapcfna-scrape.service  # correr ahora
journalctl -u scrapcfna-scrape -n 20           # logs
```

Si el scraping falla, el comando sale con código distinto de 0 y la unidad queda en estado *failed*.

## Despliegue en Debian (gunicorn + nginx)

Archivos en `deploy/`: `systemd/scrapcfna.service` (gunicorn), `systemd/scrapcfna-scrape.{service,timer}` y `nginx/scrapcfna.conf`. Asumen el proyecto en `/opt/scrapcfna`, el virtualenv en `/opt/scrapcfna/venv` y un usuario de sistema `scrapcfna`; reemplazá `api.midominio.com` por tu dominio.

```bash
sudo apt install nginx certbot python3-certbot-nginx python3-venv
sudo useradd --system --home /opt/scrapcfna --shell /usr/sbin/nologin scrapcfna

# Código y dependencias (no copies db.sqlite3 ni .env de desarrollo)
sudo mkdir -p /opt/scrapcfna && sudo chown scrapcfna: /opt/scrapcfna
# ...copiar el proyecto a /opt/scrapcfna...
sudo -u scrapcfna python3 -m venv /opt/scrapcfna/venv
sudo -u scrapcfna /opt/scrapcfna/venv/bin/pip install -r /opt/scrapcfna/requirements.txt

# Variables de entorno (completar DJANGO_SECRET_KEY y el dominio)
sudo cp /opt/scrapcfna/.env.example /etc/scrapcfna.env
sudo chmod 640 /etc/scrapcfna.env && sudo chown root:scrapcfna /etc/scrapcfna.env
sudo nano /etc/scrapcfna.env

# Directorios de datos (los mismos que crea systemd) + estáticos
sudo install -d -o scrapcfna -g www-data /var/lib/scrapcfna /var/www/scrapcfna/static
cd /opt/scrapcfna
sudo -u scrapcfna bash -c 'set -a; . /etc/scrapcfna.env; set +a; venv/bin/python manage.py migrate && venv/bin/python manage.py collectstatic --noinput && venv/bin/python manage.py createsuperuser'

# Servicios
sudo cp deploy/systemd/scrapcfna*.service deploy/systemd/scrapcfna-scrape.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scrapcfna.service scrapcfna-scrape.timer

# nginx + TLS (certbot configura https antes de que Django empiece a redirigir)
sudo cp deploy/nginx/scrapcfna.conf /etc/nginx/sites-available/scrapcfna
sudo ln -s /etc/nginx/sites-available/scrapcfna /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.midominio.com
```

Verificación: `curl https://api.midominio.com/api/v1/noticias/`, `systemctl status scrapcfna`, `journalctl -u scrapcfna -f`.

Para actualizar: copiar el código, `pip install -r requirements.txt`, `migrate`, `collectstatic` y `sudo systemctl reload scrapcfna`.

## Despliegue sin systemd (contenedor Docker / QNAP)

Si el Debian es un contenedor sin systemd ni nginx, `deploy/run.sh` levanta gunicorn directo en un puerto (por defecto 8002, tiene que estar publicado por el contenedor) y un loop que scrapea cada hora. Los estáticos del admin los sirve `whitenoise`.

```bash
git clone https://github.com/nahuelcacer/scrapcfna.git ~/scrapcfna && cd ~/scrapcfna
python3 -m venv venv && venv/bin/pip install -r requirements.txt
```

Crear `~/scrapcfna/.env` (Django lo lee solo) con este contenido, reemplazando la clave y la IP:

```
DJANGO_SECRET_KEY=<generar con: python3 -c "import secrets; print(secrets.token_urlsafe(50))">
DJANGO_ALLOWED_HOSTS=192.168.1.79
DJANGO_CSRF_TRUSTED_ORIGINS=http://192.168.1.79:8002
DJANGO_SSL_REDIRECT=0
DJANGO_CACHE_DIR=/home/nahuel/scrapcfna/cache
```

```bash
chmod 600 .env
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/python manage.py createsuperuser

chmod +x deploy/run.sh
deploy/run.sh start      # también: stop | restart | status
```

Logs en `logs/` (`access.log`, `error.log`, `scrape.log`). Variables opcionales de `run.sh`: `PORT`, `WORKERS`, `SCRAPE_INTERVAL` (segundos, default 3600) y `SCRAPE_PAGES`.

Como el contenedor no tiene init, los procesos **no se reinician solos** si el contenedor se reinicia: hay que volver a correr `deploy/run.sh start`.

Para actualizar: `git pull && venv/bin/pip install -r requirements.txt && venv/bin/python manage.py migrate && venv/bin/python manage.py collectstatic --noinput && deploy/run.sh restart`.

## Configuración

- `CFNA_NOTICIAS_URL` en `config/settings.py`: URL base a scrapear.
- `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["scrape_page"]`: límite del endpoint `page` (por defecto `10/min`).
- Los contadores del throttling usan el cache local de Django; con varios workers conviene un cache compartido (Redis).

## Tests

```bash
python manage.py test
```
