set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/your/repo.git}"
REPO_BRANCH="${REPO_BRANCH:-develop}"
REPO_DIR="/srv/repo"
SCRIPT="${SCRIPT:-auth_server.py}"
APP_PORT="${APP_PORT:-8000}"

if [ ! -d "${REPO_DIR}/.git" ]; then
  echo "Клонирую ${REPO_URL} -> ${REPO_DIR} (branch ${REPO_BRANCH})"
  git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${REPO_DIR}"
else
  echo "Репозиторий уже существует, обновляю ветку ${REPO_BRANCH}"
  cd "${REPO_DIR}"
  git fetch origin "${REPO_BRANCH}"
  git checkout "${REPO_BRANCH}"
  git pull --ff-only origin "${REPO_BRANCH}" || true
fi

cd "${REPO_DIR}"

if [ -f requirements.txt ]; then
  echo "Устанавливаю зависимости из requirements.txt"
  pip install --no-cache-dir -r requirements.txt
fi

export PORT="${APP_PORT}"

echo "Запускаю python ${SCRIPT} (порт ${APP_PORT})"
exec python3 "${SCRIPT}"
