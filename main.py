import sys
import os
import base64
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, 
                             QFileDialog, QInputDialog, QMessageBox, QLineEdit,
                             QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStyle)
from PyQt6.QtGui import QAction, QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken

class CryptoNoteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_file = None
        self.current_password = None

    def initUI(self):
        self.setWindowTitle("Шифрований Блокнот")
        self.resize(800, 600)
        self.center()

        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(15, 15, 15, 15)

        # Панель кнопок (замість меню)
        self.btn_layout = QHBoxLayout()
        
        self.btn_new = QPushButton("Створити")
        self.btn_new.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_new.clicked.connect(self.new_file)
        
        self.btn_open = QPushButton("Відкрити")
        self.btn_open.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.btn_open.clicked.connect(self.open_file)
        
        self.btn_save = QPushButton("Зберегти")
        self.btn_save.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_save.clicked.connect(self.save_file)

        self.btn_plus = QPushButton("Текст +")
        self.btn_minus = QPushButton("Текст -")
        self.btn_plus.clicked.connect(self.zoom_in)
        self.btn_minus.clicked.connect(self.zoom_out)
        
        self.btn_layout.addWidget(self.btn_new)
        self.btn_layout.addWidget(self.btn_open)
        self.btn_layout.addWidget(self.btn_save)
        self.btn_layout.addSpacing(20) # Відступ між групами кнопок
        self.btn_layout.addWidget(self.btn_plus)
        self.btn_layout.addWidget(self.btn_minus)
        self.btn_layout.addStretch()
        self.layout.addLayout(self.btn_layout)

        # Текстовий редактор (plain text)
        self.text_edit = QPlainTextEdit()
        font = QFont("Monospace", 14)
        self.text_edit.setFont(font)
        
        self.layout.addWidget(self.text_edit)
        self.setCentralWidget(self.central_widget)

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

    def new_file(self):
        self.text_edit.clear()
        self.current_file = None
        self.current_password = None
        self.setWindowTitle("Шифрований Блокнот - Новий файл")

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

    def save_file(self):
        """Шифрує текст та зберігає у файл."""
        if not self.current_file:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Зберегти файл", "", "CryptoNote Files (*.cnot);;All Files (*)"
            )
            if file_name:
                self.current_file = file_name
            else:
                return

        if not self.current_password:
            password, ok = self.get_password("Збереження", "Введіть пароль для шифрування:")
            if not ok:
                return
            if not password:
                QMessageBox.warning(self, "Увага", "Пароль не може бути порожнім!")
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
            
            self.setWindowTitle(f"Шифрований Блокнот - {self.current_file}")
            # Зберігаємо "тихо", без набридливого повідомлення про успіх
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Помилка при збереженні:\n{str(e)}")

    def open_file(self):
        """Відкриває діалог вибору файлу."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Відкрити файл", "", "CryptoNote Files (*.cnot);;All Files (*)"
        )
        if file_name:
            self.load_file(file_name)

    def load_file(self, file_name):
        """Запитує пароль та розшифровує текст із вказаного файлу."""
        attempts = 3
        while attempts > 0:
            label = f"Пароль для файлу {os.path.basename(file_name)}:"
            if attempts < 3:
                label += f"\n(Залишилось спроб: {attempts})"
                
            password, ok = self.get_password("Відкриття", label)
            if not ok:
                return # Користувач натиснув Скасувати
                
            if not password:
                QMessageBox.warning(self, "Увага", "Пароль не може бути порожнім!")
                continue

            try:
                with open(file_name, 'rb') as f:
                    file_data = f.read()
                
                if len(file_data) <= 16:
                    raise ValueError("Невірний формат файлу або файл порожній.")

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
                self.current_file = file_name
                self.setWindowTitle(f"Шифрований Блокнот - {self.current_file}")
                return # Успішне розшифрування, виходимо

            except InvalidToken:
                attempts -= 1
                if attempts > 0:
                    QMessageBox.warning(self, "Помилка доступу", "Неправильний пароль! Спробуйте ще раз.")
                else:
                    QMessageBox.critical(self, "Помилка", "Вичерпано всі спроби. Файл не відкрито.")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Помилка при відкритті:\n{str(e)}")
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Додаємо темну тему для сучасного вигляду
    apply_dark_theme(app)
    
    window = CryptoNoteApp()
    window.show()
    
    # Відкриваємо файл, якщо він був переданий як аргумент командного рядка
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
        if os.path.exists(file_to_open):
            window.load_file(file_to_open)
            
    sys.exit(app.exec())
