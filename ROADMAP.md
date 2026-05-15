# Roadmap — My Shop

## ✅ Завершено

| Спринт | Описание | Статус |
|--------|----------|--------|
| Foundation | FastAPI + Vue 3 + PostgreSQL + Docker + Alembic + Makefile | ✅ |
| Sprint 1 | Auth (JWT + OAuth), регистрация, вход, профиль | ✅ |
| Sprint 2 | Каталог, PDP, избранное, отзывы, корзина, заказы | ✅ |
| Sprint 2.5 | Редактирование профиля, смена пароля | ✅ |
| Sprint 2.6 | Responsive design (mobile + desktop) | ✅ |
| Sprint 3 | Поиск, фильтры, сортировка, Toast-уведомления | ✅ |

---

## 🗺 Дальнейший план

### Sprint 4 — Админ-панель и управление контентом
**Цель:** дать админам и поставщикам инструменты управления.

**Срез 1 — Backend: API для поставщика**
- `GET /products/my` — товары текущего поставщика
- Проверка прав в `DELETE /products/{id}` (только свой товар)

**✅ Срез 2 — Frontend: "Мои товары" для поставщика**
- Новый роут `/my-products` (только для `role=supplier`)
- Список товаров поставщика (карточки)
- Модалка создания/редактирования товара
- Soft-delete (деактивация) вместо hard-delete
- Toast-уведомления
- E2E тест

**✅ Срез 3 — Admin Panel**
- CRUD категорий (админ): POST/PUT/DELETE /categories
- Страница `/admin` с таблицей категорий (создание, редактирование, удаление)
- Router guard `/admin` (только `role=admin`)
- Ссылка «Админ» в Header.vue (только для admin)
- Seed-админ: `seed-admin@example.com` / `seedpassword123`
- E2E тест

**Срез 4 — Upload изображений + E2E**
- Backend: `POST /products/{id}/images` (Multipart upload)
- Frontend: загрузка фото в форме товара
- E2E: создание, редактирование, удаление товара поставщиком

### Sprint 5 — Корзина и оформление заказа v2
**Цель:** превратить корзину и заказы в полноценный checkout flow.

- **Backend:**
  - Адрес доставки в модели Order
  - Валидация наличия товара перед заказом
  - Promo-коды (скидки)
- **Frontend:**
  - Переверстать Cart.vue в мобильный Ozon-стиль
  - Страница checkout (адрес, доставка, оплата)
  - Skeleton-загрузки вместо текстовых спиннеров
  - Бесконечный скролл в каталоге (вместо кнопки "Показать ещё")
- **Тесты:** e2e на полный flow покупки

### Sprint 6 — Интеграции и инфраструктура
**Цель:** production-ready функции.

- **Backend:**
  - Redis для кэширования популярных товаров
  - Celery + RabbitMQ для фоновых задач (отправка email, очистка корзин)
  - Rate limiting на API
  - Health check endpoint
- **Frontend:**
  - SSR или хотя бы prerender для SEO
  - Meta-теги для PDP
  - Service Worker для офлайн-корзины
- **DevOps:**
  - Docker Compose production
  - GitHub Actions CI/CD
  - Nginx reverse proxy

### Sprint 7 — AI / ML фичи (опционально)
- Рекомендации товаров (похожие товары, "вам может понравиться")
- Поиск с опечатками (fuzzy search)
- Автоматическая категоризация товаров

---

## 🎯 Рекомендация: следующий шаг

**Срез 4 — Upload изображений товаров**

Причины:
1. **Admin Panel готова** — категории управляются через UI
2. **Витрина без фото выглядит неполноценно** — сейчас у товаров только placeholder'ы
3. **Минимальный срез:**
   - Backend: `POST /products/{id}/images` (Multipart upload, сохранение на диск)
   - Frontend: `<input type="file">` в ProductFormModal
   - Отображение фото в ProductCard и ProductDetail
4. **Пользователь уже просил** upload ранее (в плане Sprint 4)

**Оценка:** 1.5–2 часа работы.
