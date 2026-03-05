/**
 * Профориентационный тест — вопросы, баллы по профилям, результаты
 */
(function() {
  var PROFILES = {
    ai_business: {
      id: 'ai_business',
      title: 'AI для бизнеса',
      emoji: '📊',
      desc: 'Вам подойдут курсы по автоматизации, ChatGPT, Midjourney и AI-инструментам для повышения эффективности. Идеально для тех, кто хочет быстрее решать рабочие задачи и внедрять нейросети в процессы.',
      courseUrl: '/courses/',
      courseLabel: 'Смотреть курсы по AI для бизнеса'
    },
    design_content: {
      id: 'design_content',
      title: 'Контент и дизайн',
      emoji: '🎨',
      desc: 'Ваша ниша — генерация изображений, текстов и креатив с помощью нейросетей. Рекомендуем курсы по Midjourney, DALL·E, ChatGPT для копирайтинга и визуального контента.',
      courseUrl: '/courses/',
      courseLabel: 'Курсы по дизайну и контенту'
    },
    python_ml: {
      id: 'python_ml',
      title: 'Python и машинное обучение',
      emoji: '🐍',
      desc: 'Вам интересна разработка и данные. Подойдут курсы по Python, машинному обучению, нейросетям и созданию AI-продуктов с нуля.',
      courseUrl: '/courses/',
      courseLabel: 'Курсы по Python и ML'
    },
    analytics: {
      id: 'analytics',
      title: 'Аналитика и данные',
      emoji: '📈',
      desc: 'Вам близка работа с данными и принятие решений. Рекомендуем курсы по Data Science, аналитике с AI и автоматизации отчётов.',
      courseUrl: '/courses/',
      courseLabel: 'Курсы по аналитике'
    }
  };

  /** Вопросы: каждый вариант — массив [ai_business, design_content, python_ml, analytics] */
  var QUESTIONS = [
    {
      q: 'Сколько вам лет?',
      o: [
        { text: 'До 18', scores: [0, 1, 1, 0] },
        { text: 'От 18 до 24', scores: [1, 1, 2, 1] },
        { text: 'От 25 до 34', scores: [2, 1, 1, 2] },
        { text: 'От 35 до 44', scores: [2, 0, 0, 1] },
        { text: 'От 45 до 54', scores: [2, 0, 0, 1] },
        { text: '55 и старше', scores: [2, 1, 0, 0] }
      ]
    },
    {
      q: 'Ваш текущий уровень в IT',
      o: [
        { text: 'Полный новичок', scores: [2, 2, 0, 0] },
        { text: 'Базовые знания', scores: [2, 1, 1, 1] },
        { text: 'Средний уровень', scores: [1, 0, 2, 2] },
        { text: 'Опытный специалист', scores: [0, 0, 2, 2] }
      ]
    },
    {
      q: 'Цель обучения',
      o: [
        { text: 'Сменить профессию', scores: [0, 0, 3, 2] },
        { text: 'Повысить эффективность', scores: [3, 1, 0, 1] },
        { text: 'Запустить свой продукт', scores: [1, 1, 2, 2] },
        { text: 'Из интереса', scores: [1, 2, 1, 1] }
      ]
    },
    {
      q: 'Сколько времени готовы уделять в неделю?',
      o: [
        { text: '1–3 часа', scores: [2, 2, 0, 0] },
        { text: '4–7 часов', scores: [2, 1, 1, 1] },
        { text: '8–15 часов', scores: [0, 0, 2, 2] },
        { text: 'Интенсивно (15+ часов)', scores: [0, 0, 3, 2] }
      ]
    },
    {
      q: 'Какое направление AI вам интереснее?',
      o: [
        { text: 'Контент и дизайн', scores: [0, 3, 0, 0] },
        { text: 'Аналитика и данные', scores: [1, 0, 0, 3] },
        { text: 'Разработка и код', scores: [0, 0, 3, 1] },
        { text: 'Автоматизация бизнеса', scores: [3, 0, 0, 1] }
      ]
    },
    {
      q: 'Чем вы занимаетесь сейчас?',
      o: [
        { text: 'Учёба (школа / вуз)', scores: [0, 2, 1, 1] },
        { text: 'Офисная работа', scores: [2, 1, 0, 1] },
        { text: 'Маркетинг, продажи, креатив', scores: [1, 2, 0, 1] },
        { text: 'Разработка или IT', scores: [0, 0, 2, 2] },
        { text: 'Свой бизнес / фриланс', scores: [2, 1, 1, 1] }
      ]
    },
    {
      q: 'Какой формат обучения удобнее?',
      o: [
        { text: 'Короткие уроки, сразу практика', scores: [2, 2, 0, 0] },
        { text: 'Системный курс с нуля', scores: [1, 0, 2, 2] },
        { text: 'Интенсив с дедлайнами', scores: [0, 0, 2, 1] },
        { text: 'Самостоятельно в своём темпе', scores: [1, 1, 1, 1] }
      ]
    }
  ];

  var PROFILE_KEYS = ['ai_business', 'design_content', 'python_ml', 'analytics'];

  function getResult(scores) {
    var max = -1;
    var key = 'ai_business';
    for (var i = 0; i < PROFILE_KEYS.length; i++) {
      var k = PROFILE_KEYS[i];
      if (scores[k] > max) {
        max = scores[k];
        key = k;
      }
    }
    return PROFILES[key];
  }

  function buildResultHtml(profile, registerUrl) {
    registerUrl = (registerUrl || '/register/') + (profile && profile.id ? '?goal=' + encodeURIComponent(profile.id) : '');
    var html = (
      '<div class="pt-result">' +
      '<div class="pt-result-emoji">' + profile.emoji + '</div>' +
      '<h3 class="pt-result-title">Ваша ниша — ' + profile.title + '</h3>' +
      '<p class="pt-result-desc">' + profile.desc + '</p>' +
      '<div class="pt-result-actions">' +
      '<a href="' + profile.courseUrl + '" class="pt-btn pt-btn-outline">' + profile.courseLabel + '</a> ' +
      '<a href="' + registerUrl + '" class="pt-btn">Записаться на курс</a>' +
      '</div>'
    );
    if (typeof window.PROFTEST_USER_LOGGED_IN !== 'undefined' && window.PROFTEST_USER_LOGGED_IN) {
      html += (
        '<div class="pt-save-result-box">' +
        '<button type="button" class="pt-btn pt-save-to-profile" id="ptSaveToProfile">Сохранить результат в мой профиль</button>' +
        '<p class="pt-save-msg" id="ptSaveMsg" aria-live="polite"></p>' +
        '</div>'
      );
    }
    html += '<button type="button" class="pt-result-retry" id="ptRetry">Пройти тест заново</button></div>';
    return html;
  }

  window.PROFTEST = {
    QUESTIONS: QUESTIONS,
    PROFILES: PROFILES,
    getResult: getResult,
    buildResultHtml: buildResultHtml
  };
})();
