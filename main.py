import sys
import os
import json
import base64
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, 
                             QFileDialog, QInputDialog, QMessageBox, QLineEdit,
                             QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStyle)
from PyQt6.QtGui import QAction, QFont, QPalette, QColor, QTextCursor
from PyQt6.QtCore import Qt
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken

TRANSLATIONS = {
    'app_title': {'uk': "Шифрований Блокнот v1.2.0", 'en': "CryptoNote v1.2.0"},
    'btn_new': {'uk': "Створити", 'en': "New"},
    'btn_open': {'uk': "Відкрити", 'en': "Open"},
    'btn_save': {'uk': "Зберегти", 'en': "Save"},
    'btn_change_pwd': {'uk': "Змінити пароль", 'en': "Change Password"},
    'btn_zoom_in': {'uk': "Текст +", 'en': "Zoom In"},
    'btn_zoom_out': {'uk': "Текст -", 'en': "Zoom Out"},
    'btn_theme': {'uk': "Тема", 'en': "Theme"},
    'btn_lang': {'uk': "EN", 'en': "UA"},
    'title_new_file': {'uk': "Новий файл", 'en': "New file"},
    'msg_save_changes_title': {'uk': "Зберегти зміни?", 'en': "Save changes?"},
    'msg_save_changes': {'uk': "У вас є незбережені зміни. Бажаєте зберегти їх?", 'en': "You have unsaved changes. Do you want to save them?"},
    'msg_warning': {'uk': "Увага", 'en': "Warning"},
    'msg_empty_pwd': {'uk': "Пароль не може бути порожнім!", 'en': "Password cannot be empty!"},
    'msg_short_pwd': {'uk': "Пароль повинен містити щонайменше 6 символів!", 'en': "Password must be at least 6 characters long!"},
    'msg_confirm_pwd': {'uk': "Повторіть пароль для підтвердження:", 'en': "Repeat password to confirm:"},
    'msg_error': {'uk': "Помилка", 'en': "Error"},
    'msg_pwd_mismatch': {'uk': "Паролі не збігаються! Спробуйте ще раз.", 'en': "Passwords do not match! Try again."},
    'msg_save_title': {'uk': "Збереження", 'en': "Saving"},
    'msg_enter_pwd': {'uk': "Введіть пароль для шифрування:", 'en': "Enter password for encryption:"},
    'msg_save_error': {'uk': "Помилка при збереженні:\n{}", 'en': "Error while saving:\n{}"},
    'msg_new_pwd_title': {'uk': "Новий пароль", 'en': "New Password"},
    'msg_enter_new_pwd': {'uk': "Введіть новий пароль для шифрування:", 'en': "Enter new password for encryption:"},
    'msg_success': {'uk': "Успіх", 'en': "Success"},
    'msg_pwd_changed_saved': {'uk': "Пароль змінено та файл успішно перезаписано!", 'en': "Password changed and file successfully overwritten!"},
    'msg_pwd_changed_warn': {'uk': "Пароль змінено. Не забудьте зберегти файл!", 'en': "Password changed. Do not forget to save the file!"},
    'msg_open_file': {'uk': "Відкрити файл", 'en': "Open File"},
    'file_filter': {'uk': "Файли CryptoNote (*.cnot);;Всі файли (*)", 'en': "CryptoNote Files (*.cnot);;All Files (*)"},
    'msg_pwd_for_file': {'uk': "Пароль для файлу {}:", 'en': "Password for file {}:"},
    'msg_attempts_left': {'uk': "\n(Залишилось спроб: {})", 'en': "\n(Attempts left: {})"},
    'msg_open_title': {'uk': "Відкриття", 'en': "Opening"},
    'msg_invalid_format': {'uk': "Невірний формат файлу або файл порожній.", 'en': "Invalid file format or file is empty."},
    'msg_access_error': {'uk': "Помилка доступу", 'en': "Access Error"},
    'msg_wrong_pwd': {'uk': "Неправильний пароль! Спробуйте ще раз.", 'en': "Wrong password! Try again."},
    'msg_attempts_exhausted': {'uk': "Вичерпано всі спроби. Файл не відкрито.", 'en': "All attempts exhausted. File not opened."},
    'msg_open_error': {'uk': "Помилка при відкритті:\n{}", 'en': "Error while opening:\n{}"},
}

class CryptoNoteApp(QMainWindow):
    SETTINGS_FILE = os.path.expanduser("~/.cryptonote_settings.json")

    def __init__(self):
        super().__init__()
        self.current_file = None
        self.current_password = None
        self.is_dark_theme = True
        self.lang = 'uk'
        self.load_settings()
        self.initUI()

    def t(self, key, *args):
        """Повертає перекладений рядок для поточного ключа."""
        text = TRANSLATIONS.get(key, {}).get(self.lang, key)
        if args:
            text = text.format(*args)
        return text

    def load_settings(self):
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.is_dark_theme = data.get("is_dark_theme", True)
                    self.lang = data.get("lang", "uk")
            except Exception:
                pass
                
    def save_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump({"is_dark_theme": self.is_dark_theme, "lang": self.lang}, f)
            os.chmod(self.SETTINGS_FILE, 0o600)
        except Exception:
            pass

    def initUI(self):
        self.setWindowTitle(self.t('app_title'))
        self.resize(800, 600)
        self.center()

        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(15, 15, 15, 15)

        # Панель кнопок (замість меню)
        self.btn_layout = QHBoxLayout()
        
        self.btn_new = QPushButton(self.t('btn_new'))
        self.btn_new.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_new.clicked.connect(self.new_file)
        
        self.btn_open = QPushButton(self.t('btn_open'))
        self.btn_open.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.btn_open.clicked.connect(self.open_file)
        
        self.btn_save = QPushButton(self.t('btn_save'))
        self.btn_save.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_save.clicked.connect(self.save_file)

        self.btn_change_pwd = QPushButton(self.t('btn_change_pwd'))
        self.btn_change_pwd.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_change_pwd.clicked.connect(self.change_password)

        self.btn_plus = QPushButton(self.t('btn_zoom_in'))
        self.btn_minus = QPushButton(self.t('btn_zoom_out'))
        self.btn_plus.clicked.connect(self.zoom_in)
        self.btn_minus.clicked.connect(self.zoom_out)
        
        self.btn_theme = QPushButton(self.t('btn_theme'))
        self.btn_theme.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        self.btn_theme.clicked.connect(self.toggle_theme)
        
        self.btn_lang = QPushButton(self.t('btn_lang'))
        self.btn_lang.clicked.connect(self.toggle_lang)
        
        self.btn_layout.addWidget(self.btn_new)
        self.btn_layout.addWidget(self.btn_open)
        self.btn_layout.addWidget(self.btn_save)
        self.btn_layout.addWidget(self.btn_change_pwd)
        self.btn_layout.addSpacing(20) # Відступ між групами кнопок
        self.btn_layout.addWidget(self.btn_plus)
        self.btn_layout.addWidget(self.btn_minus)
        self.btn_layout.addSpacing(20)
        self.btn_layout.addWidget(self.btn_theme)
        self.btn_layout.addWidget(self.btn_lang)
        self.btn_layout.addStretch()
        self.layout.addLayout(self.btn_layout)

        # Текстовий редактор (plain text)
        self.text_edit = QPlainTextEdit()
        font = QFont("Monospace", 14)
        self.text_edit.setFont(font)
        self.text_edit.document().modificationChanged.connect(self.update_title)
        
        self.layout.addWidget(self.text_edit)
        self.setCentralWidget(self.central_widget)
        self.text_edit.setFocus()
        self.update_title()

    def update_ui_texts(self):
        """Оновлює тексти всіх елементів інтерфейсу."""
        self.btn_new.setText(self.t('btn_new'))
        self.btn_open.setText(self.t('btn_open'))
        self.btn_save.setText(self.t('btn_save'))
        self.btn_change_pwd.setText(self.t('btn_change_pwd'))
        self.btn_plus.setText(self.t('btn_zoom_in'))
        self.btn_minus.setText(self.t('btn_zoom_out'))
        self.btn_theme.setText(self.t('btn_theme'))
        self.btn_lang.setText(self.t('btn_lang'))
        self.update_title()

    def toggle_lang(self):
        self.lang = 'en' if self.lang == 'uk' else 'uk'
        self.save_settings()
        self.update_ui_texts()

    def update_title(self):
        title = self.t('app_title') + " - "
        if self.current_file:
            title += os.path.basename(self.current_file)
        else:
            title += self.t('title_new_file')
            
        if self.text_edit.document().isModified():
            title += " *"
        self.setWindowTitle(title)

    def maybe_save(self):
        if not self.text_edit.document().isModified():
            return True
            
        reply = QMessageBox.question(
            self, self.t('msg_save_changes_title'), 
            self.t('msg_save_changes'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.save_file()
            return not self.text_edit.document().isModified()
        elif reply == QMessageBox.StandardButton.No:
            return True
        else:
            return False

    def closeEvent(self, event):
        if self.maybe_save():
            self.text_edit.clear()
            self.current_password = None
            event.accept()
        else:
            event.ignore()

    def center(self):
        frameGm = self.frameGeometry()
        screen = QApplication.primaryScreen().availableGeometry().center()
        frameGm.moveCenter(screen)
        self.move(frameGm.topLeft())

    def zoom_in(self):
        font = self.text_edit.font()
        font.setPointSize(font.pointSize() + 2)
        self.text_edit.setFont(font)

    def zoom_out(self):
        font = self.text_edit.font()
        new_size = font.pointSize() - 2
        if new_size > 6:
            font.setPointSize(new_size)
            self.text_edit.setFont(font)

    def toggle_theme(self):
        app = QApplication.instance()
        if self.is_dark_theme:
            # Примусово вмикаємо світлу тему
            apply_light_theme(app)
            self.is_dark_theme = False
        else:
            # Примусово вмикаємо темну тему
            apply_dark_theme(app)
            self.is_dark_theme = True
        self.save_settings()

    def new_file(self):
        if not self.maybe_save():
            return
        self.text_edit.clear()
        self.current_file = None
        self.current_password = None
        self.text_edit.document().setModified(False)
        self.text_edit.setFocus()
        self.update_title()

    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Генерує ключ з пароля за допомогою PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def get_password(self, title, label):
        """Відкриває діалог для вводу пароля зі збільшеними елементами."""
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
        
        # Збільшуємо шрифт для всього вікна
        font = dialog.font()
        font.setPointSize(14) # Встановлюємо комфортний великий розмір
        dialog.setFont(font)
        
        # Робимо вікно ширшим
        dialog.setMinimumWidth(450)
        
        ok = dialog.exec()
        password = dialog.textValue()
        return password, bool(ok)

    def get_new_password_with_confirmation(self, title, label):
        """Запитує пароль двічі для підтвердження."""
        while True:
            password, ok = self.get_password(title, label)
            if not ok:
                return None, False
            if not password:
                QMessageBox.warning(self, self.t('msg_warning'), self.t('msg_empty_pwd'))
                continue
            if len(password) < 6:
                QMessageBox.warning(self, self.t('msg_warning'), self.t('msg_short_pwd'))
                continue
                
            confirm_password, ok2 = self.get_password(title, self.t('msg_confirm_pwd'))
            if not ok2:
                return None, False
                
            if password == confirm_password:
                return password, True
            else:
                QMessageBox.warning(self, self.t('msg_error'), self.t('msg_pwd_mismatch'))

    def save_file(self):
        """Шифрує текст та зберігає у файл."""
        if not self.current_file:
            file_name, _ = QFileDialog.getSaveFileName(
                self, self.t('btn_save'), "", self.t('file_filter')
            )
            if file_name:
                if not file_name.endswith('.cnot'):
                    file_name += '.cnot'
                self.current_file = file_name
            else:
                return

        if not self.current_password:
            password, ok = self.get_new_password_with_confirmation(self.t('msg_save_title'), self.t('msg_enter_pwd'))
            if not ok:
                return
            self.current_password = password

        try:
            # Генеруємо сіль для шифрування
            salt = os.urandom(16)
            key = self.derive_key(self.current_password, salt)
            fernet = Fernet(key)
            
            # Текст для збереження
            text = self.text_edit.toPlainText().encode('utf-8')
            encrypted_text = fernet.encrypt(text)
            
            # Записуємо у файл: 16 байт солі + зашифрований текст
            with open(self.current_file, 'wb') as f:
                f.write(salt + encrypted_text)
            self.text_edit.document().setModified(False)
            self.update_title()
            # Зберігаємо "тихо", без набридливого повідомлення про успіх
        except Exception as e:
            QMessageBox.critical(self, self.t('msg_error'), self.t('msg_save_error', str(e)))

    def change_password(self):
        """Змінює пароль для поточного файлу і відразу зберігає його."""
        password, ok = self.get_new_password_with_confirmation(self.t('msg_new_pwd_title'), self.t('msg_enter_new_pwd'))
        if ok:
            self.current_password = password
            
            if self.current_file:
                self.save_file()
                QMessageBox.information(self, self.t('msg_success'), self.t('msg_pwd_changed_saved'))
            else:
                self.text_edit.document().setModified(True)
                self.update_title()
                QMessageBox.information(self, self.t('msg_success'), self.t('msg_pwd_changed_warn'))

    def open_file(self):
        """Відкриває діалог вибору файлу."""
        if not self.maybe_save():
            return
        file_name, _ = QFileDialog.getOpenFileName(
            self, self.t('msg_open_file'), "", self.t('file_filter')
        )
        if file_name:
            self.load_file(file_name)

    def load_file(self, file_name):
        """Запитує пароль та розшифровує текст із вказаного файлу."""
        attempts = 3
        while attempts > 0:
            label = self.t('msg_pwd_for_file', os.path.basename(file_name))
            if attempts < 3:
                label += self.t('msg_attempts_left', attempts)
                
            password, ok = self.get_password(self.t('msg_open_title'), label)
            if not ok:
                return # Користувач натиснув Скасувати
                
            if not password:
                QMessageBox.warning(self, self.t('msg_warning'), self.t('msg_empty_pwd'))
                continue

            try:
                with open(file_name, 'rb') as f:
                    file_data = f.read()
                
                if len(file_data) <= 16:
                    raise ValueError(self.t('msg_invalid_format'))

                # Перші 16 байт - це сіль
                salt = file_data[:16]
                encrypted_text = file_data[16:]

                # Генеруємо ключ з введеного пароля
                key = self.derive_key(password, salt)
                fernet = Fernet(key)

                # Розшифровуємо
                decrypted_text = fernet.decrypt(encrypted_text).decode('utf-8')
                
                self.current_password = password
                
                self.text_edit.setPlainText(decrypted_text)
                self.text_edit.document().setModified(False)
                self.current_file = file_name
                
                # Переміщуємо курсор в кінець тексту
                cursor = self.text_edit.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.text_edit.setTextCursor(cursor)
                self.text_edit.setFocus()
                
                self.update_title()
                return # Успішне розшифрування, виходимо

            except InvalidToken:
                attempts -= 1
                if attempts > 0:
                    QMessageBox.warning(self, self.t('msg_access_error'), self.t('msg_wrong_pwd'))
                else:
                    QMessageBox.critical(self, self.t('msg_error'), self.t('msg_attempts_exhausted'))
            except Exception as e:
                QMessageBox.critical(self, self.t('msg_error'), self.t('msg_open_error', str(e)))
                return

def apply_dark_theme(app):
    """Застосовує сучасну темну тему."""
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(dark_palette)

def apply_light_theme(app):
    """Застосовує світлу тему примусово, ігноруючи системні налаштування."""
    app.setStyle("Fusion")
    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
    light_palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    light_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
    light_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
    light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
    light_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    light_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(light_palette)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    window = CryptoNoteApp()
    
    # Застосовуємо збережену тему
    if window.is_dark_theme:
        apply_dark_theme(app)
    else:
        apply_light_theme(app)
        
    window.show()
    
    # Відкриваємо файл, якщо він був переданий як аргумент командного рядка
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
        if os.path.exists(file_to_open):
            window.load_file(file_to_open)
            
    sys.exit(app.exec())
