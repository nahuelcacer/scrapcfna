#!/usr/bin/env bash
# Arranque sin systemd (contenedores Docker, QNAP, etc.): gunicorn.
#
#   deploy/run.sh start|stop|restart|status
#
# Lee la configuración de Django desde ../.env (ver .env.example). Variables opcionales:
#   PORT=8002            puerto donde escucha gunicorn
#   WORKERS=2            cantidad de workers
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8002}"
WORKERS="${WORKERS:-2}"
RUN_DIR="$APP_DIR/run"
LOG_DIR="$APP_DIR/logs"
GUNICORN_PID="$RUN_DIR/gunicorn.pid"

mkdir -p "$RUN_DIR" "$LOG_DIR"
cd "$APP_DIR" || exit 1

is_running() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

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
}

stop() {
    if is_running "$GUNICORN_PID"; then
        kill "$(cat "$GUNICORN_PID")" && echo "gunicorn detenido"
    fi
    rm -f "$GUNICORN_PID"
}

status() {
    is_running "$GUNICORN_PID" && echo "gunicorn: corriendo (pid $(cat "$GUNICORN_PID"), puerto $PORT)" || echo "gunicorn: detenido"
}

case "${1:-}" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    status) status ;;
    *) echo "uso: $0 {start|stop|restart|status}"; exit 1 ;;
esac
