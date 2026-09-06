(() => {
  const links = [...document.querySelectorAll('.rail-links a[href^="#"]')];
  const targets = links
    .map((link) => document.getElementById(decodeURIComponent(link.hash.slice(1))))
    .filter(Boolean);

  if ('IntersectionObserver' in window && targets.length) {
    const linkById = new Map(links.map((link) => [decodeURIComponent(link.hash.slice(1)), link]));
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (!visible) return;
      links.forEach((link) => link.removeAttribute('aria-current'));
      linkById.get(visible.target.id)?.setAttribute('aria-current', 'location');
    }, { rootMargin: '-20% 0px -65%', threshold: [0, .25, .6] });
    targets.forEach((target) => observer.observe(target));
  }

  document.querySelectorAll('[data-quiz]').forEach((quiz) => {
    const feedback = quiz.querySelector('.feedback');
    const correctChoice = [...quiz.querySelectorAll('.choice')]
      .find((choice) => choice.dataset.value === quiz.dataset.answer);
    if (correctChoice && !quiz.querySelector('.print-answer')) {
      const printAnswer = document.createElement('p');
      printAnswer.className = 'print-answer';
      const explanation = correctChoice.dataset.correct || '这是正确答案。';
      printAnswer.textContent = `打印答案：${correctChoice.textContent.trim()}。${explanation}`;
      quiz.append(printAnswer);
    }
    quiz.querySelectorAll('.choice').forEach((choice) => {
      choice.setAttribute('type', 'button');
      choice.setAttribute('aria-pressed', 'false');
      choice.addEventListener('click', () => {
        quiz.querySelectorAll('.choice').forEach((item) => item.setAttribute('aria-pressed', 'false'));
        choice.setAttribute('aria-pressed', 'true');
        const correct = choice.dataset.value === quiz.dataset.answer;
        const message = correct ? choice.dataset.correct : choice.dataset.wrong;
        if (feedback) feedback.textContent = message || (correct ? '回答正确。' : '再想一想。');
      });
    });
  });

  let printDetails = [];
  window.addEventListener('beforeprint', () => {
    printDetails = [...document.querySelectorAll('details:not([open])')];
    printDetails.forEach((item) => { item.open = true; });
  });
  window.addEventListener('afterprint', () => {
    printDetails.forEach((item) => { item.open = false; });
    printDetails = [];
  });
})();
