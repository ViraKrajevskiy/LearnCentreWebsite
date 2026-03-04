# Восстановление кода главной страницы

Если нужно вернуть код главной страницы к версии из репозитория (последний коммит), можно сделать так.

## Через агента (Cursor / AI)

Напишите агенту, например:

- **«Верни мой код главной страницы»**
- **«Восстанови главную страницу из git»**
- **«Restore main page from git»**

Агент должен выполнить команды из раздела «Вручную» ниже (или запустить скрипт).

## Вручную

### Вариант 1: скрипт (PowerShell)

Из корня проекта:

```powershell
.\scripts\restore_main_page.ps1
```

### Вариант 2: команды Git

Из корня проекта:

```powershell
git checkout HEAD -- WebSite/static/css/main_pages.css
git checkout HEAD -- WebSite/static/js/main_pages.js
git checkout HEAD -- WebSite/templates/main_pages/base.html
git checkout HEAD -- "WebSiteFront/templates/Main_page/lastFigma versuin.html"
```

## Какие файлы восстанавливаются

| Файл | Описание |
|------|----------|
| `WebSite/static/css/main_pages.css` | Стили главной и общих страниц |
| `WebSite/static/js/main_pages.js` | Скрипты главной и общих страниц |
| `WebSite/templates/main_pages/base.html` | Базовый шаблон (шапка/подвал) в приложении WebSite |
| `WebSiteFront/templates/Main_page/lastFigma versuin.html` | Шаблон главной (лендинг) |

После восстановления при необходимости выполните `python manage.py collectstatic`, если используете `STATIC_ROOT`.
