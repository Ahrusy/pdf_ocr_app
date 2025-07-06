document.addEventListener('DOMContentLoaded', function() {
    // Анимация элементов при загрузке
    const animatedElements = document.querySelectorAll('.hero-content, .benefit-card, .pricing-card');
    animatedElements.forEach((el, index) => {
        el.classList.add('slide-up');
        el.style.animationDelay = `${index * 0.1}s`;
    });

    // Элементы формы загрузки
    const fileInput = document.getElementById('file-upload');
    const fileName = document.getElementById('file-name');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress');
    const progressText = document.getElementById('progress-text');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const spinner = document.getElementById('spinner');
    const uploadForm = document.getElementById('upload-form');
    const uploadLabel = document.querySelector('.file-upload-label');

    // Обработка выбора файла
    fileInput.addEventListener('change', function() {
        if (this.files.length) {
            fileName.textContent = this.files[0].name;
            uploadLabel.classList.add('file-selected');
        }
    });

    // Drag and drop функционал
    uploadLabel.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadLabel.classList.add('dragover');
    });

    uploadLabel.addEventListener('dragleave', () => {
        uploadLabel.classList.remove('dragover');
    });

    uploadLabel.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadLabel.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            fileName.textContent = e.dataTransfer.files[0].name;
            uploadLabel.classList.add('file-selected');
        }
    });

    // AJAX загрузка файла с индикацией прогресса
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const xhr = new XMLHttpRequest();

        // Показываем индикатор загрузки
        submitBtn.disabled = true;
        btnText.textContent = "Обработка...";
        spinner.style.display = "inline-block";
        progressContainer.style.display = "flex";

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percentComplete + '%';
                progressText.textContent = percentComplete + '%';
            }
        });

        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                // Перенаправляем на страницу результата после успешной загрузки
                window.location.href = "{{ url_for('result') }}";
            } else {
                alert('Ошибка при загрузке файла: ' + xhr.responseText);
                resetUploadForm();
            }
        });

        xhr.addEventListener('error', function() {
            alert('Произошла ошибка при соединении с сервером');
            resetUploadForm();
        });

        xhr.open('POST', "{{ url_for('upload_file') }}", true);
        xhr.send(formData);
    });

    function resetUploadForm() {
        submitBtn.disabled = false;
        btnText.textContent = "Преобразовать в текст";
        spinner.style.display = "none";
        progressContainer.style.display = "none";
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
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

    // Анимация чисел статистики
    const statNumbers = document.querySelectorAll('.stat-number');
    if (statNumbers.length) {
        statNumbers.forEach(el => {
            const target = parseInt(el.textContent.replace(/\s/g, ''));
            let current = 0;
            const increment = target / 50;
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                el.textContent = Math.floor(current).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
            }, 20);
        });
    }
});