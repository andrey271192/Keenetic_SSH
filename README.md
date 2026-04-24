# 🔧 Keenetic SSH

Отдельный минимальный сервис: **управление роутерами Keenetic по SSH через Telegram**. Без веб-дашборда, без мониторинга, без HydraRoute — только бот и `sshpass`.

Логика SSH и команд взята из [keenetic-unified](https://github.com/andrey271192/keenetic-unified).

---

## Возможности

- `/ssh имя команда` и `/ssh all команда` — выполнение на одном или всех роутерах (verbose: exit-код, вывод)
- `/neo`, `/uptime`, `/interfaces`, `/reboot`, `/ping`
- `/add`, `/setip`, `/setname`, `/setweb`, `/delete`, `/list`, `/router`
- Список роутеров хранится в `data/routers.json` на сервере

---

## Требования

- Ubuntu 22/24 (или другой Linux с systemd)
- `sshpass`, `openssh-client`, Python 3.10+
- Токен бота и **один** chat ID (бот отвечает только этому чату)

---

## Установка

```bash
git clone https://github.com/andrey271192/Keenetic_SSH.git /opt/keenetic-ssh
cd /opt/keenetic-ssh
bash install.sh
nano .env
```

Пример `.env`:

```env
TELEGRAM_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=371010834

SSH_USER=root
SSH_PASS=keenetic
```

Перезапуск после правок `.env`:

```bash
systemctl restart keenetic-ssh
```

Логи:

```bash
journalctl -u keenetic-ssh -f
```

---

## Роутеры

Добавить из Telegram:

```
/add andrey 212.118.42.105 root keenetic
```

Или отредактировать `data/routers.json` на сервере:

```json
{
  "andrey": {
    "ip": "192.168.88.1",
    "user": "root",
    "password": "keenetic",
    "display_name": "Дом Andrey",
    "web_url": ""
  }
}
```

Поле `wan_ip` поддерживается как запасной вариант, если `ip` пустой.

---

## Команды бота

| Команда | Описание |
|--------|----------|
| `/help` | Справка |
| `/list` | Список роутеров |
| `/router имя` | Карточка |
| `/ssh имя команда` | SSH на роутер |
| `/ssh all команда` | На всех с IP |
| `/neo имя status\|restart` | Neo |
| `/uptime`, `/interfaces`, `/reboot` | Как в SSH |
| `/ping имя` | Ping с VPS до IP роутера |
| `/add имя IP [user] [pass]` | Добавить |
| `/setip`, `/setname`, `/setweb`, `/delete` | Настройка |

---

## Поддержка

[Boosty — донат](https://boosty.to/andrey27/donate)

---

## Обновление

```bash
cd /opt/keenetic-ssh && git pull && systemctl restart keenetic-ssh
```
