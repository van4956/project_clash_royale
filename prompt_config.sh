#!/bin/bash

# Скрипт для настройки промпта в bash
# Запустите: bash setup_prompt.sh

echo "Настройка промпта для bash ..."

# Создаем бэкап текущего .bashrc
if [ -f ~/.bashrc ]; then
    cp ~/.bashrc ~/.bashrc.backup
    echo "Создан бэкап: ~/.bashrc.backup"
fi

# Добавляем кастомный промпт в .bashrc
cat >> ~/.bashrc << 'EOF'

# Кастомный промпт для покерного проекта
function set_custom_prompt() {
    local venv_name=""
    local project_name="project_09_poker"

    # Определяем виртуальное окружение
    if [[ -n "$VIRTUAL_ENV" ]]; then
        venv_name="($(basename $VIRTUAL_ENV))"
    fi

    # Цвета
    local GREEN='\[\033[01;32m\]'
    local BLUE='\[\033[01;34m\]'
    local YELLOW='\[\033[01;33m\]'
    local RESET='\[\033[00m\]'

    # Устанавливаем промпт
    PS1="${GREEN}${venv_name}${RESET} ${BLUE}(${project_name})${RESET} ${YELLOW}\u${RESET}@~ $ "
}

# Активируем кастомный промпт
set_custom_prompt

EOF

echo "Промпт настроен!"
echo "Для применения изменений выполните: source ~/.bashrc"
echo "Или перезапустите терминал"

# Показываем что добавили
echo ""
echo "Добавлено в ~/.bashrc:"
echo "----------------------------------------"
tail -n 20 ~/.bashrc