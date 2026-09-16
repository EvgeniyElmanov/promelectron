<template>
  <footer class="app-footer" data-testid="app-footer">
    <div class="app-footer__columns">
      <div class="app-footer__col app-footer__col--brand">
        <span class="app-footer__logo">Пром Электрон</span>
        <p class="app-footer__about">
          Интернет-магазин электротоваров и сопутствующих товаров.
        </p>
        <a class="app-footer__phone" href="tel:88005004585">8 (800) 500-45-85</a>
        <span class="app-footer__hours">Ежедневно с 9:00 до 21:00</span>
        <div class="app-footer__socials" aria-label="Социальные сети">
          <span v-for="s in socials" :key="s.name" class="app-footer__social" :title="s.name" v-html="s.icon" />
        </div>
      </div>

      <nav v-for="col in columns" :key="col.title" class="app-footer__col" :aria-label="col.title">
        <h3 class="app-footer__col-title">{{ col.title }}</h3>
        <ul class="app-footer__links">
          <li v-for="link in col.links" :key="link.label">
            <RouterLink v-if="link.to" :to="link.to" class="app-footer__link">{{ link.label }}</RouterLink>
            <span v-else class="app-footer__link app-footer__link--muted">{{ link.label }}</span>
          </li>
        </ul>
      </nav>
    </div>

    <div class="app-footer__bottom">
      <span class="app-footer__copy">© 2026 Пром Электрон. Все права защищены.</span>
      <div class="app-footer__payments" aria-label="Способы оплаты">
        <span class="app-footer__payment">МИР</span>
        <span class="app-footer__payment">VISA</span>
        <span class="app-footer__payment">Mastercard</span>
      </div>
    </div>
  </footer>
</template>

<script setup>
// Статичный footer (D-04/D-12). Ссылки — только на существующие роуты;
// страницы «О компании»/«Доставка и оплата» и т.п. отсутствуют → немые элементы.
// Соц-иконки — немые (внешних ссылок на соцсети в проекте нет, как в D-12).
const socials = [
  {
    name: 'ВКонтакте',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13 17.5c-5 0-7.8-3.4-7.9-9h2.5c.1 4.2 1.9 6 3.4 6.3V8.5h2.3v3.6c1.5-.2 3-1.7 3.5-3.6h2.3c-.3 2.3-1.6 4-2.5 4.7.9.6 2.4 2.2 2.9 4.3h-2.6c-.4-1.4-1.3-2.6-2.7-3.3v3.3H13z"/></svg>',
  },
  {
    name: 'Telegram',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.9 4.6l-3.1 14.6c-.2 1-.8 1.3-1.7.8l-4.7-3.4-2.2 2.2c-.3.3-.5.5-1 .5l.3-4.7L18 7.9c.4-.3-.1-.5-.6-.2L7.2 13.5 2.6 12c-1-.3-1-1 .2-1.4l17.7-6.8c.8-.3 1.6.2 1.4.8z"/></svg>',
  },
  {
    name: 'YouTube',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M23 12s0-3.9-.5-5.6c-.3-1-1.1-1.8-2.1-2C18.6 4 12 4 12 4s-6.6 0-8.4.4c-1 .2-1.8 1-2.1 2C1 8.1 1 12 1 12s0 3.9.5 5.6c.3 1 1.1 1.8 2.1 2 1.8.4 8.4.4 8.4.4s6.6 0 8.4-.4c-1 0 0 0 0 0 1-.2 1.8-1 2.1-2 .5-1.7.5-5.6.5-5.6zM9.8 15.5v-7l6 3.5-6 3.5z"/></svg>',
  },
];

const columns = [
  {
    title: 'Покупателям',
    links: [
      { label: 'Доставка и оплата' },
      { label: 'Гарантия и возврат' },
      { label: 'Как сделать заказ' },
      { label: 'Частые вопросы' },
    ],
  },
  {
    title: 'Компания',
    links: [
      { label: 'О компании' },
      { label: 'Новости' },
      { label: 'Вакансии' },
      { label: 'Контакты' },
    ],
  },
  {
    title: 'Сервис и помощь',
    links: [
      { label: 'Поддержка 24/7' },
      { label: 'Проверка статуса заказа', to: '/orders' },
      { label: 'Возврат товара' },
      { label: 'Карта сайта', to: '/catalog' },
    ],
  },
];
</script>

<style scoped>
.app-footer {
  margin-top: var(--space-8);
  background: var(--color-dark);
  color: rgba(255, 255, 255, 0.75);
  padding: var(--space-7) var(--space-4) var(--space-5);
  font-size: var(--font-size-body-sm);
}

.app-footer__columns {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-5);
}

.app-footer__logo {
  font-size: var(--font-size-h3);
  font-weight: var(--font-weight-bold);
  color: var(--color-white);
}

.app-footer__about {
  margin-top: var(--space-2);
}

.app-footer__phone {
  display: inline-block;
  margin-top: var(--space-3);
  font-size: var(--font-size-body-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-white);
  text-decoration: none;
}

.app-footer__hours {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--font-size-caption);
}

.app-footer__socials {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.app-footer__social {
  display: inline-flex;
  color: rgba(255, 255, 255, 0.75);
}

.app-footer__col-title {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
  color: var(--color-white);
  margin-bottom: var(--space-3);
}

.app-footer__links {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.app-footer__link {
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
}

.app-footer__link:hover {
  color: var(--color-white);
}

.app-footer__link--muted:hover {
  color: rgba(255, 255, 255, 0.75);
}

.app-footer__bottom {
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.app-footer__payments {
  display: flex;
  gap: var(--space-2);
}

.app-footer__payment {
  padding: var(--space-1) var(--space-2);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
}

@media (min-width: 768px) {
  .app-footer__columns {
    grid-template-columns: 2fr 1fr 1fr 1fr;
  }

  .app-footer__bottom {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}
</style>
