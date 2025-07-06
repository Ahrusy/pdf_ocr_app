import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance
import pytesseract
from PyPDF2 import PdfReader
import sqlite3
from datetime import datetime, timedelta
from config import Config
import logging
from logging.handlers import RotatingFileHandler

# Инициализация приложения
app = Flask(__name__)
app.config.from_object(Config)


# Добавляем фильтр для форматирования чисел
@app.template_filter('number_format')
def number_format(value):
    """Фильтр для форматирования чисел с разделителями тысяч"""
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except (ValueError, TypeError):
        return value


# Настройка логирования
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

# Настройка Tesseract OCR
try:
    pytesseract.pytesseract.tesseract_cmd = app.config.get('TESSERACT_CMD', '/usr/bin/tesseract')
except Exception as e:
    app.logger.error(f"Tesseract initialization error: {str(e)}")

# Создание необходимых директорий
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.instance_path), exist_ok=True)


def init_db():
    """Инициализация базы данных"""
    with sqlite3.connect(os.path.join(app.instance_path, 'database.db')) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE,
                is_premium INTEGER DEFAULT 0,
                premium_expiry DATE,
                registration_date DATE DEFAULT CURRENT_DATE,
                api_key TEXT UNIQUE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()


init_db()


def log_activity(user_id, action):
    """Логирование действий пользователя"""
    try:
        with sqlite3.connect(os.path.join(app.instance_path, 'database.db')) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO user_activity (user_id, action) VALUES (?, ?)',
                           (user_id, action))
            conn.commit()
    except Exception as e:
        app.logger.error(f"Activity log error: {str(e)}")


def allowed_file(filename):
    """Проверка допустимых расширений файлов"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def optimize_image_for_ocr(image_path):
    """Оптимизация изображения для лучшего распознавания текста"""
    try:
        img = Image.open(image_path)

        # Конвертация в grayscale
        img = img.convert('L')

        # Увеличение контраста
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2)

        # Бинаризация
        img = img.point(lambda x: 0 if x < 140 else 255)

        return img
    except Exception as e:
        app.logger.error(f"Image optimization error: {str(e)}")
        raise


def extract_text_from_pdf(pdf_path):
    """Извлечение текста из PDF"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""  # Обработка None
        return text.strip()
    except Exception as e:
        app.logger.error(f"PDF extraction error: {str(e)}")
        raise


def extract_text_from_image(image_path):
    """Извлечение текста из изображения с помощью OCR"""
    try:
        img = optimize_image_for_ocr(image_path)
        custom_config = r'--oem 3 --psm 6 -l rus+eng'
        text = pytesseract.image_to_string(img, config=custom_config)
        return text.strip()
    except Exception as e:
        app.logger.error(f"OCR processing error: {str(e)}")
        raise


def get_user_info(user_id):
    """Получение информации о пользователе"""
    try:
        with sqlite3.connect(os.path.join(app.instance_path, 'database.db')) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, is_premium, premium_expiry, api_key 
                FROM users WHERE id = ?
            ''', (user_id,))
            return cursor.fetchone()
    except Exception as e:
        app.logger.error(f"Get user info error: {str(e)}")
        return None


def check_premium_status(user_id):
    """Проверка премиум-статуса пользователя"""
    user_info = get_user_info(user_id)
    if not user_info:
        return False

    is_premium = user_info[1] == 1
    premium_expiry = user_info[2]

    if is_premium and premium_expiry:
        expiry_date = datetime.strptime(premium_expiry, '%Y-%m-%d').date()
        if datetime.now().date() > expiry_date:
            # Премиум истек, обновляем статус
            with sqlite3.connect(os.path.join(app.instance_path, 'database.db')) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET is_premium = 0 WHERE id = ?', (user_id,))
                conn.commit()
            return False
    return is_premium


@app.before_request
def before_request():
    """Логирование запросов"""
    if 'user_id' in session:
        app.logger.info(f"User {session['user_id']} accessed {request.path}")


@app.route('/')
def index():
    """Главная страница"""
    stats = {
        'users': 12543,
        'conversions': 89256,
        'premium': 3245
    }
    return render_template('index.html', stats=stats)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загруженных файлов"""
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(request.url)

    if not allowed_file(file.filename):
        flash('Допустимые форматы: pdf, png, jpg, jpeg', 'error')
        return redirect(request.url)

    try:
        # Сохранение файла
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Проверка премиум-статуса
        is_premium = False
        if 'user_id' in session:
            is_premium = check_premium_status(session['user_id'])
            if is_premium:
                log_activity(session['user_id'], 'premium_file_upload')
            else:
                log_activity(session['user_id'], 'free_file_upload')

        # Проверка размера файла
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # в MB
        if not is_premium and file_size > app.config['FREE_FILE_SIZE_LIMIT']:
            os.remove(filepath)
            flash(
                f'Бесплатные пользователи ограничены файлами до {app.config["FREE_FILE_SIZE_LIMIT"]}MB. Перейдите на премиум.',
                'warning')
            return redirect(url_for('premium'))

        # Обработка файла
        if filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        else:
            text = extract_text_from_image(filepath)

        # Ограничение для бесплатных пользователей
        if not is_premium and len(text) > app.config['FREE_TEXT_LIMIT']:
            text = text[:app.config['FREE_TEXT_LIMIT']] + "\n\n[Для просмотра полного текста перейдите на премиум]"

        os.remove(filepath)
        return render_template('result.html',
                               text=text,
                               is_premium=is_premium,
                               filename=filename)

    except Exception as e:
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        app.logger.error(f"File processing error: {str(e)}")
        flash('Произошла ошибка при обработке файла. Пожалуйста, попробуйте другой файл.', 'error')
        return redirect(url_for('index'))


@app.route('/premium')
def premium():
    """Страница премиум-подписки"""
    testimonials = [
        {"name": "Анна К.", "text": "Премиум сэкономил мне десятки часов работы!", "rating": 5},
        {"name": "Иван П.", "text": "Лучшее решение для обработки документов.", "rating": 5},
        {"name": "Мария С.", "text": "Окупилось в первый же день использования.", "rating": 4}
    ]
    return render_template('premium.html', testimonials=testimonials)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Пожалуйста, заполните все поля', 'error')
            return redirect(url_for('login'))

        try:
            with sqlite3.connect(os.path.join(app.instance_path, 'database.db')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, is_premium FROM users 
                    WHERE username = ? AND password = ?
                ''', (username, password))
                user = cursor.fetchone()

                if user:
                    session['user_id'] = user[0]
                    session['is_premium'] = user[1]
                    log_activity(user[0], 'login')
                    flash('Вы успешно вошли в систему!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Неверное имя пользователя или пароль', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('Произошла ошибка при входе в систему', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()

        if not username or not password:
            flash('Пожалуйста, заполните обязательные поля', 'error')
            return redirect(url_for('register'))

        try:
            with sqlite3.connect(os.path.join(app.instance_path, 'database.db')) as conn:
                cursor = conn.cursor()
                # Генерация API ключа
                api_key = os.urandom(16).hex()
                cursor.execute('''
                    INSERT INTO users (username, password, email, api_key)
                    VALUES (?, ?, ?, ?)
                ''', (username, password, email if email else None, api_key))
                conn.commit()

            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Имя пользователя или email уже заняты', 'error')
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            flash('Произошла ошибка при регистрации', 'error')

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Выход из системы"""
    if 'user_id' in session:
        log_activity(session['user_id'], 'logout')
        session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/upgrade', methods=['POST'])
def upgrade():
    """Обработка перехода на премиум"""
    if 'user_id' not in session:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('login'))

    try:
        # В реальном приложении здесь должна быть интеграция с платежной системой
        expiry_date = datetime.now() + timedelta(days=30)

        with sqlite3.connect(os.path.join(app.instance_path, 'database.db')) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_premium = 1, premium_expiry = ? 
                WHERE id = ?
            ''', (expiry_date.strftime('%Y-%m-%d'), session['user_id']))
            conn.commit()

        session['is_premium'] = 1
        log_activity(session['user_id'], 'upgrade_to_premium')
        flash('Поздравляем! Теперь у вас премиум-аккаунт.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Upgrade error: {str(e)}")
        flash('Произошла ошибка при обновлении аккаунта', 'error')
        return redirect(url_for('premium'))


@app.errorhandler(404)
def page_not_found(e):
    """Обработка 404 ошибки"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Обработка 500 ошибки"""
    app.logger.error(f"500 error: {str(e)}")
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

@app.errorhandler(404)
def page_not_found(e):
    """Обработка 404 ошибки"""
    try:
        return render_template('404.html'), 404
    except:
        return "<h1>Страница не найдена</h1><p>Запрашиваемая страница не существует.</p>", 404

@app.errorhandler(500)
def internal_error(e):
    """Обработка 500 ошибки"""
    app.logger.error(f"500 error: {str(e)}")
    try:
        return render_template('500.html'), 500
    except:
        return "<h1>Внутренняя ошибка сервера</h1><p>Пожалуйста, попробуйте позже.</p>", 500