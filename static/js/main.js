document.addEventListener('DOMContentLoaded', function() {
    // Анимация элементов при загрузке
    const animatedElements = document.querySelectorAll('.hero-content, .benefit-card, .pricing-card');
    animatedElements.forEach((el, index) => {
        el.classList.add('slide-up');
        el.style.animationDelay = `${index * 0.1}s`;
    });

    // Обработка загрузки файлов
    const fileUpload = document.getElementById('file-upload');
    if (fileUpload) {
        const fileUploadLabel = document.querySelector('.file-upload-label');

        fileUpload.addEventListener('change', function(e) {
            if (this.files.length) {
                const fileName = this.files[0].name;
                fileUploadLabel.innerHTML = `
                    <img src="${fileUploadLabel.querySelector('img').src}" alt="Загрузить">
                    <span>${fileName}</span>
                    <small>Готово к конвертации</small>
                `;
                fileUploadLabel.style.borderColor = '#4361ee';
            }
        });
    }

    // Плавная прокрутка
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Обработка формы подписки
    const subscribeForms = document.querySelectorAll('.subscribe-form');
    subscribeForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const emailInput = this.querySelector('input[type="email"]');
            if (emailInput.value) {
                alert('Спасибо за подписку! Мы отправили вам письмо с подтверждением.');
                emailInput.value = '';
            }
        });
    });

    // Анимация при наведении на кнопки
    const buttons = document.querySelectorAll('.btn-primary, .btn-outline');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});

// Форматирование чисел (для статистики)
function numberFormat(number) {
    return new Intl.NumberFormat('ru-RU').format(number);
}

// Инициализация элементов статистики
const statNumbers = document.querySelectorAll('.stat-number');
if (statNumbers.length) {
    statNumbers.forEach(el => {
        const target = parseInt(el.textContent);
        let current = 0;
        const increment = target / 50;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = numberFormat(Math.floor(current));
        }, 20);
    });
}