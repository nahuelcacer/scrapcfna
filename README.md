# scrapcfna

Una sola página (`/`) con las noticias más recientes de https://www.cfna.org.ar/noticias/.

## Instalación

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`. Cada vez que se carga la página se scrapea cfna.org.ar; si el sitio no responde, muestra las últimas noticias guardadas.

## Despliegue en Debian (gunicorn + nginx)

Archivos en `deploy/`: `systemd/scrapcfna.service` (gunicorn) y `nginx/scrapcfna.conf`. Asumen el proyecto en `/opt/scrapcfna`, el virtualenv en `/opt/scrapcfna/venv` y un usuario de sistema `scrapcfna`; reemplazá `api.midominio.com` por tu dominio.

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
sudo -u scrapcfna bash -c 'set -a; . /etc/scrapcfna.env; set +a; venv/bin/python manage.py migrate && venv/bin/python manage.py collectstatic --noinput'

# Servicios
sudo cp deploy/systemd/scrapcfna.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scrapcfna.service

# nginx + TLS (certbot configura https antes de que Django empiece a redirigir)
sudo cp deploy/nginx/scrapcfna.conf /etc/nginx/sites-available/scrapcfna
sudo ln -s /etc/nginx/sites-available/scrapcfna /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.midominio.com
```

Verificación: `curl https://api.midominio.com/`, `systemctl status scrapcfna`, `journalctl -u scrapcfna -f`.

Para actualizar: copiar el código, `pip install -r requirements.txt`, `migrate`, `collectstatic` y `sudo systemctl reload scrapcfna`.

## Despliegue sin systemd (contenedor Docker / QNAP)

Si el Debian es un contenedor sin systemd ni nginx, `deploy/run.sh` levanta gunicorn directo en un puerto (por defecto 8002, tiene que estar publicado por el contenedor). Los estáticos los sirve `whitenoise`.

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
```

```bash
chmod 600 .env
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput

chmod +x deploy/run.sh
deploy/run.sh start      # también: stop | restart | status
```

Logs en `logs/` (`access.log`, `error.log`). Variables opcionales de `run.sh`: `PORT` y `WORKERS`.

Como el contenedor no tiene init, el proceso **no se reinicia solo** si el contenedor se reinicia: hay que volver a correr `deploy/run.sh start`.

Para actualizar: `git pull && venv/bin/pip install -r requirements.txt && venv/bin/python manage.py migrate && venv/bin/python manage.py collectstatic --noinput && deploy/run.sh restart`.

## Configuración

- `CFNA_NOTICIAS_URL` en `config/settings.py`: URL base a scrapear.

## Tests

```bash
python manage.py test
```
