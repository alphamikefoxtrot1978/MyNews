from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, QLabel, QLineEdit,
                              QListWidget, QHBoxLayout, QPushButton, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt

class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setFixedSize(400, 500)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        accounts_tab = QWidget()
        groups_tab = QWidget()
        tabs.addTab(accounts_tab, "Accounts")
        tabs.addTab(groups_tab, "Groups")
        layout.addWidget(tabs)

        accounts_layout = QVBoxLayout(accounts_tab)
        accounts_layout.addWidget(QLabel("Quora Email:"))
        self.quora_email = QLineEdit(self.parent.quora_email)
        accounts_layout.addWidget(self.quora_email)

        accounts_layout.addWidget(QLabel("Quora Password:"))
        self.quora_pass = QLineEdit(self.parent.quora_password)
        self.quora_pass.setEchoMode(QLineEdit.Password)
        accounts_layout.addWidget(self.quora_pass)

        accounts_layout.addWidget(QLabel("Twitter API Key:"))
        self.twitter_key = QLineEdit(self.parent.twitter_api_key)
        accounts_layout.addWidget(self.twitter_key)

        accounts_layout.addWidget(QLabel("Twitter API Secret:"))
        self.twitter_secret = QLineEdit(self.parent.twitter_api_secret)
        accounts_layout.addWidget(self.twitter_secret)

        accounts_layout.addWidget(QLabel("Twitter Access Token:"))
        self.twitter_token = QLineEdit(self.parent.twitter_access_token)
        accounts_layout.addWidget(self.twitter_token)

        accounts_layout.addWidget(QLabel("Twitter Access Secret:"))
        self.twitter_access_secret = QLineEdit(self.parent.twitter_access_secret)
        accounts_layout.addWidget(self.twitter_access_secret)

        accounts_layout.addWidget(QLabel("Logo URL:"))
        self.logo_url = QLineEdit(self.parent.logo_url)
        accounts_layout.addWidget(self.logo_url)

        accounts_layout.addWidget(QLabel("Output Image URL:"))
        self.output_url = QLineEdit(self.parent.output_image_url)
        accounts_layout.addWidget(self.output_url)

        groups_layout = QVBoxLayout(groups_tab)
        self.quora_groups_list = QListWidget()
        for group in self.parent.quora_groups:
            self.quora_groups_list.addItem(group)
        groups_layout.addWidget(self.quora_groups_list, stretch=1)

        group_buttons_layout = QHBoxLayout()
        add_group_button = QPushButton("Add Group")
        edit_group_button = QPushButton("Edit Group")
        remove_group_button = QPushButton("Remove Group")

        group_buttons_layout.addWidget(add_group_button)
        group_buttons_layout.addWidget(edit_group_button)
        group_buttons_layout.addWidget(remove_group_button)

        add_group_button.clicked.connect(self.add_quora_group)
        edit_group_button.clicked.connect(self.edit_quora_group)
        remove_group_button.clicked.connect(self.remove_quora_group)
        groups_layout.addLayout(group_buttons_layout)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_preferences)
        layout.addWidget(save_button)

    def add_quora_group(self):
        group_url, ok = QInputDialog.getText(self, "Add Quora Group", "Enter Quora Group URL:")
        if ok and group_url.strip():
            self.quora_groups_list.addItem(group_url.strip())

    def edit_quora_group(self):
        selected_items = self.quora_groups_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a group to edit.")
            return
        item = selected_items[0]
        new_url, ok = QInputDialog.getText(self, "Edit Quora Group", "Edit Quora Group URL:", text=item.text())
        if ok and new_url.strip():
            item.setText(new_url.strip())

    def remove_quora_group(self):
        selected_items = self.quora_groups_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a group to remove.")
            return
        for item in selected_items:
            self.quora_groups_list.takeItem(self.quora_groups_list.row(item))

    def save_preferences(self):
        self.parent.quora_email = self.quora_email.text()
        self.parent.quora_password = self.quora_pass.text()
        self.parent.twitter_api_key = self.twitter_key.text()
        self.parent.twitter_api_secret = self.twitter_secret.text()
        self.parent.twitter_access_token = self.twitter_token.text()
        self.parent.twitter_access_secret = self.twitter_access_secret.text()
        self.parent.logo_url = self.logo_url.text()
        self.parent.output_image_url = self.output_url.text()
        self.parent.quora_groups = [self.quora_groups_list.item(i).text() for i in range(self.quora_groups_list.count())]
        self.parent.save_config()
        self.parent.status_label.setText("Preferences saved")
        self.accept()