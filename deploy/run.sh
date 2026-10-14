#!/usr/bin/env bash
# Arranque sin systemd (contenedores Docker, QNAP, etc.): gunicorn + scraping horario.
#
#   deploy/run.sh start|stop|restart|status
#
# Lee la configuración de Django desde ../.env (ver .env.example). Variables opcionales:
#   PORT=8002            puerto donde escucha gunicorn
#   WORKERS=2            cantidad de workers
#   SCRAPE_INTERVAL=3600 segundos entre scrapeos
#   SCRAPE_PAGES=2       páginas por scrapeo
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$APP_DIR/venv/bin/python"
PORT="${PORT:-8002}"
WORKERS="${WORKERS:-2}"
SCRAPE_INTERVAL="${SCRAPE_INTERVAL:-3600}"
SCRAPE_PAGES="${SCRAPE_PAGES:-2}"
RUN_DIR="$APP_DIR/run"
LOG_DIR="$APP_DIR/logs"
GUNICORN_PID="$RUN_DIR/gunicorn.pid"
SCHEDULER_PID="$RUN_DIR/scheduler.pid"

mkdir -p "$RUN_DIR" "$LOG_DIR"
cd "$APP_DIR" || exit 1

is_running() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

scheduler_loop() {
    while true; do
        "$PY" manage.py scrapear_noticias --paginas "$SCRAPE_PAGES" --origen cron >>"$LOG_DIR/scrape.log" 2>&1 \
            || echo "$(date -Is) scraping falló" >>"$LOG_DIR/scrape.log"
        sleep "$SCRAPE_INTERVAL"
    done
}

start() {
    if is_running "$GUNICORN_PID"; then
        echo "gunicorn ya está corriendo (pid $(cat "$GUNICORN_PID"))"
    else
        "$APP_DIR/venv/bin/gunicorn" config.wsgi:application \
            --bind "0.0.0.0:$PORT" --workers "$WORKERS" --timeout 60 \
            --pid "$GUNICORN_PID" --daemon \
            --access-logfile "$LOG_DIR/access.log" --error-logfile "$LOG_DIR/error.log"
        sleep 1
        is_running "$GUNICORN_PID" && echo "gunicorn iniciado en el puerto $PORT" \
            || { echo "gunicorn no pudo iniciar; ver $LOG_DIR/error.log"; return 1; }
    fi
    if is_running "$SCHEDULER_PID"; then
        echo "scheduler ya está corriendo (pid $(cat "$SCHEDULER_PID"))"
    else
        nohup setsid bash "${BASH_SOURCE[0]}" _scheduler >/dev/null 2>&1 &
        echo $! >"$SCHEDULER_PID"
        echo "scheduler iniciado (cada ${SCRAPE_INTERVAL}s, ${SCRAPE_PAGES} páginas)"
    fi
}

stop() {
    if is_running "$GUNICORN_PID"; then
        kill "$(cat "$GUNICORN_PID")" && echo "gunicorn detenido"
    fi
    if is_running "$SCHEDULER_PID"; then
        # Mata el grupo de procesos del loop (incluye el sleep en curso).
        kill -- "-$(cat "$SCHEDULER_PID")" 2>/dev/null || kill "$(cat "$SCHEDULER_PID")"
        echo "scheduler detenido"
    fi
    rm -f "$GUNICORN_PID" "$SCHEDULER_PID"
}

status() {
    is_running "$GUNICORN_PID" && echo "gunicorn: corriendo (pid $(cat "$GUNICORN_PID"), puerto $PORT)" || echo "gunicorn: detenido"
    is_running "$SCHEDULER_PID" && echo "scheduler: corriendo (pid $(cat "$SCHEDULER_PID"))" || echo "scheduler: detenido"
}

case "${1:-}" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    status) status ;;
    _scheduler) scheduler_loop ;;
    *) echo "uso: $0 {start|stop|restart|status}"; exit 1 ;;
esac
