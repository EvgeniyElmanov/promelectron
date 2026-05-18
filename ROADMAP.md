# Roadmap — MyShop

## ✅ Завершённые спринты

### Спринт 1 — Базовая инфраструктура
- [x] FastAPI + PostgreSQL + SQLAlchemy async
- [x] Docker Compose (postgres)
- [x] Alembic миграции
- [x] JWT авторизация (регистрация, логин)
- [x] Vue 3 + Vite + Vue Router

### Спринт 2 — Каталог и товары
- [x] Модели Product, Category
- [x] CRUD товаров (API + UI)
- [x] Загрузка изображений
- [x] Поиск, фильтры, сортировка
- [x] Пагинация (load more)

### Спринт 3 — Корзина и заказы
- [x] Корзина (добавление, удаление, количество)
- [x] Оформление заказа
- [x] История заказов
- [x] Роли: user, admin, supplier

### Спринт 4 — Профиль и соцсети
- [x] Профиль пользователя (просмотр, редактирование)
- [x] OAuth 2.0 (Google, Yandex) — backend endpoints
- [x] Аватарка + загрузка фото
- [x] Редактирование личных данных

### Спринт 5 — Адрес и RWD
- [x] **5.1** Структурированный адрес (6 полей, JSON в БД)
- [x] **5.2** Автодополнение адреса (Nominatim API + локальные словари)
- [x] **5.3** Валидация stock при оформлении заказа
- [x] **5.4** Cart Redesign (фото, свайп-удаление, sticky checkout, итоги)
- [x] **5.5** Skeleton Loaders на всех страницах
- [x] Responsive Web Design (64 responsive тестов)

### Спринт 6 — Email и статусы заказов
- [x] Email-инфраструктура (aiosmtplib)
- [x] Письмо подтверждения при создании заказа
- [x] Письмо обновления статуса заказа
- [x] Страница детализации заказа (`/orders/:id`)
- [x] Таймлайн статусов (pending → paid → shipped → delivered)
- [x] Цветные статус-бейджи

---

## 📋 Текущие задачи (Backlog)

### Спринт 7 — Настройка production-окружения

#### 7.1 Email (SMTP) для production
**Задача:** Настроить сервисный email для отправки писем всем пользователям.

**Варианты решения:**
- **Mailgun** (рекомендуется) — 5000 писем/месяц бесплатно, специально для приложений
- **Gmail** — до 100 писем/день, подходит только для теста
- **Mailtrap** — для dev/testing, письма не уходят в реальный мир

**Что нужно сделать:**
1. Зарегистрироваться на https://www.mailgun.com/
2. Создать домен (или использовать sandbox)
3. Получить SMTP credentials
4. Заполнить `.env`:
   ```
   SMTP_HOST=smtp.mailgun.org
   SMTP_PORT=587
   SMTP_USER=postmaster@mg.myshop.ru
   SMTP_PASSWORD=your-mailgun-api-key
   SMTP_FROM=MyShop <noreply@myshop.ru>
   SMTP_TLS=true
   ```
5. Протестировать: оформить заказ с реальным email

#### 7.2 OAuth 2.0 — Google ID
**Задача:** Настроить авторизацию через Google для реальных пользователей.

**Что нужно сделать:**
1. Перейти в [Google Cloud Console](https://console.cloud.google.com/)
2. Создать проект (или использовать существующий)
3. Включить API: **Google+ API** / **Google Identity Toolkit**
4. Создать OAuth 2.0 credentials (Web application)
5. Добавить Authorized redirect URI:
   - Dev: `http://localhost:5173/auth/callback`
   - Prod: `https://myshop.ru/auth/callback`
6. Скопировать **Client ID** и **Client Secret**
7. Заполнить `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
8. Протестировать: кнопка «Войти через Google» на странице логина

#### 7.3 OAuth 2.0 — Yandex ID
**Задача:** Настроить авторизацию через Яндекс.

**Что нужно сделать:**
1. Перейти в [Yandex OAuth](https://oauth.yandex.ru/)
2. Создать приложение
3. Выбрать платформу: **Веб-сервисы**
4. Добавить Callback URL:
   - Dev: `http://localhost:5173/auth/callback`
   - Prod: `https://myshop.ru/auth/callback`
5. Выбрать необходимые доступы: **Доступ к email-адресу**, **Доступ к данным Яндекс ID**
6. Скопировать **Client ID** и **Client Secret**
7. Заполнить `.env`:
   ```
   YANDEX_CLIENT_ID=your-client-id
   YANDEX_CLIENT_SECRET=your-client-secret
   ```
8. Протестировать: кнопка «Войти через Яндекс» на странице логина

---

## 🚀 Будущие спринты (идеи)

### Спринт 8 — SEO и мета-теги
- [ ] Динамические `<title>` и `<meta description>` для товаров
- [ ] Open Graph теги (картинка, заголовок, описание)
- [ ] Sitemap.xml генерация
- [ ] SSR или prerender для поисковиков

### Спринт 9 — Админка: дашборд ✅
- [x] Статистика заказов (графики по дням/неделям)
- [x] Выручка, средний чек
- [x] Топ-товары по продажам
- [x] Управление пользователями (список, блокировка)

### Спринт 10 — Платёжный шлюз (mock)
- [ ] Интеграция с тестовым шлюзом (ЮKassa / Stripe test)
- [ ] Статус «оплачен» после успешной оплаты
- [ ] История платежей

### Спринт 11 — Уведомления внутри приложения
- [ ] Toast-уведомления о смене статуса заказа (real-time)
- [ ] Push-уведомления (Firebase Cloud Messaging)
- [ ] История уведомлений в профиле

### Спринт 12 — Производительность
- [ ] Redis для кэширования популярных товаров
- [ ] Пагинация на бэкенде (limit/offset)
- [ ] Оптимизация изображений (WebP, resize)
- [ ] CDN для статики
