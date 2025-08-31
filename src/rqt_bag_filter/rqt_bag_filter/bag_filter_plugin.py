import os
import subprocess
import yaml
import re

from python_qt_binding.QtWidgets import (
    QPushButton, QListWidgetItem, QLabel, QVBoxLayout, QWidget, QFileDialog,
    QMessageBox, QListWidget, QHBoxLayout, QComboBox, QSpinBox, QFormLayout,
    QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt, QProcess, QProcessEnvironment
from rqt_gui_py.plugin import Plugin


class BagFilterPlugin(Plugin):
    def __init__(self, context):
        super(BagFilterPlugin, self).__init__(context)
        self.setObjectName('BagFilterPlugin')

        self._widget = QWidget()

        # Bag selection
        self.bag_path_label = QLabel("No bag selected")
        self.select_bag_button = QPushButton("Select Bag File")
        self.select_bag_button.clicked.connect(self.select_bag)

        # Load topics button
        self.load_topics_button = QPushButton("Load Topics")
        self.load_topics_button.clicked.connect(self.load_topics)

        # Bag info group box with scrollable text inside
        self.bag_info_group = QGroupBox("Bag Info")
        bag_info_layout = QVBoxLayout()
        self.bag_info_text = QTextEdit()
        self.bag_info_text.setReadOnly(True)
        # self.bag_info_text.setFixedHeight(200)
        self.bag_info_text.setLineWrapMode(QTextEdit.NoWrap)
        bag_info_layout.addWidget(self.bag_info_text)
        self.bag_info_group.setLayout(bag_info_layout)

        # Topics checkbox list
        self.topic_list = QListWidget()

        # Profiles combobox and load button (will be placed to the right)
        self.profile_box = QComboBox()
        self.profile_box.currentIndexChanged.connect(self.apply_profile)
        self.load_profiles_button = QPushButton("Load YAML Profiles")
        self.load_profiles_button.clicked.connect(self.load_profiles)

        # Download example profiles button
        self.download_example_button = QPushButton("Download Example Profiles")
        self.download_example_button.clicked.connect(self.download_example_profiles)

        # Label to show missing topics (always visible)
        self.missing_topics_label = QLabel("No missing topics.")
        self.missing_topics_label.setStyleSheet("color: red;")
        self.missing_topics_label.setWordWrap(True)

        # Play/Stop buttons
        self.play_button = QPushButton("Play Bag with Selected Topics")
        self.play_button.clicked.connect(self.play_bag)
        self.stop_button = QPushButton("Stop Playback")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_bag)

        # Playing indicator label
        self.playing_indicator = QLabel("● Not Playing")
        self.playing_indicator.setStyleSheet("color: gray; font-weight: bold;")
        self.playing_indicator.setAlignment(Qt.AlignCenter)

        # ROS_DOMAIN_ID input spinbox
        self.domain_id_spinbox = QSpinBox()
        self.domain_id_spinbox.setRange(0, 255)
        ros_domain_env = os.environ.get("ROS_DOMAIN_ID")
        domain_id_default = int(ros_domain_env) if ros_domain_env and ros_domain_env.isdigit() else 0
        self.domain_id_spinbox.setValue(domain_id_default)
        domain_layout = QFormLayout()
        domain_layout.addRow("ROS_DOMAIN_ID:", self.domain_id_spinbox)

        # Layout setup
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.bag_path_label)
        main_layout.addWidget(self.select_bag_button)
        main_layout.addWidget(self.load_topics_button)
        main_layout.addWidget(self.bag_info_group)

        # Horizontal layout for topic list and profiles
        mid_layout = QHBoxLayout()

        # Left: topics checklist + updated label
        topics_layout = QVBoxLayout()
        topics_layout.addWidget(QLabel("Choose the topics you want to publish:"))
        topics_layout.addWidget(self.topic_list)
        mid_layout.addLayout(topics_layout, stretch=3)

        # Right: profiles and missing topics
        profile_layout = QVBoxLayout()
        profile_layout.addWidget(QLabel("Profiles"))
        profile_layout.addWidget(self.profile_box)
        profile_layout.addWidget(self.load_profiles_button)
        profile_layout.addWidget(self.download_example_button)
        profile_layout.addWidget(self.missing_topics_label)
        profile_layout.addStretch(1)
        mid_layout.addLayout(profile_layout, stretch=1)

        main_layout.addLayout(mid_layout)

        # Play/Stop and domain ID
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.addWidget(self.play_button)
        bottom_buttons_layout.addWidget(self.stop_button)
        bottom_buttons_layout.addLayout(domain_layout)
        bottom_buttons_layout.addStretch(1)

        main_layout.addLayout(bottom_buttons_layout)
        main_layout.addWidget(self.playing_indicator)

        self._widget.setLayout(main_layout)
        context.add_widget(self._widget)

        self.bag_path = None
        self.topic_names = []
        self.profiles = {}
        self.bag_process = None

    def select_bag(self):
        bag_path, _ = QFileDialog.getOpenFileName(self._widget, "Select ROS 2 Bag File")
        if bag_path:
            self.bag_path = bag_path
            self.bag_path_label.setText(f"Selected: {os.path.basename(bag_path)}")
            self.load_topics()

    def load_topics(self):
        if not self.bag_path:
            QMessageBox.warning(self._widget, "No Bag Selected", "Please select a bag file first.")
            return

        try:
            output = subprocess.check_output(['ros2', 'bag', 'info', self.bag_path], text=True)
            self.topic_list.clear()
            self.topic_names.clear()
            topic_counts = {}
            duration = ""

            # Parse duration line, example: "Duration: 1:23s"
            for line in output.splitlines():
                if "Duration:" in line:
                    duration = line.split("Duration:")[1].strip()

            # Parse topic lines with this pattern:
            # Topic: /mavros/vfr_hud | Type: mavros_msgs/msg/VfrHud | Count: 482 | Serialization Format: cdr
            topic_line_regex = re.compile(
                r"Topic:\s+(?P<topic>\S+)\s+\|\s+Type:\s+(?P<type>[^|]+)\|\s+Count:\s+(?P<count>\d+)\s+\|"
            )

            for line in output.splitlines():
                match = topic_line_regex.search(line)
                if match:
                    topic = match.group("topic")
                    count = int(match.group("count"))
                    self.topic_names.append(topic)
                    topic_counts[topic] = count
                    item = QListWidgetItem(topic)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    self.topic_list.addItem(item)

            info_text = f"📦 Bag Info:\nDuration: {duration}\nTopics:"
            for t in self.topic_names:
                count = topic_counts.get(t, "N/A")
                info_text += f"\n  • {t} — {count} msgs"

            self.bag_info_text.setPlainText(info_text)
            self.missing_topics_label.setText("No missing topics.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self._widget, "Error", f"Failed to read bag info:\n{e}")

    def load_profiles(self):
        yaml_path, _ = QFileDialog.getOpenFileName(self._widget, "Select YAML Profile File")
        if not yaml_path:
            return

        try:
            with open(yaml_path, 'r') as f:
                self.profiles = yaml.safe_load(f)
            self.profile_box.clear()
            self.profile_box.addItem("-- Select Profile --")
            self.profile_box.addItems(self.profiles.keys())
            self.missing_topics_label.setText("No missing topics.")
        except Exception as e:
            QMessageBox.critical(self._widget, "YAML Load Error", str(e))

    def apply_profile(self):
        selected_profile = self.profile_box.currentText()
        if selected_profile not in self.profiles:
            self.missing_topics_label.setText("No missing topics.")
            return

        topics = self.profiles[selected_profile]
        for i in range(self.topic_list.count()):
            item = self.topic_list.item(i)
            item.setCheckState(Qt.Checked if item.text() in topics else Qt.Unchecked)

        missing = [t for t in topics if t not in self.topic_names]
        if missing:
            self.missing_topics_label.setText(
                f"⚠️ Missing topics in bag:\n" + "\n".join(missing)
            )
        else:
            self.missing_topics_label.setText("No missing topics.")

    def play_bag(self):
        if not self.bag_path:
            QMessageBox.warning(self._widget, "No Bag Selected", "Please select a bag file first.")
            return

        selected_topics = []
        for i in range(self.topic_list.count()):
            item = self.topic_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_topics.append(item.text())

        if not selected_topics:
            QMessageBox.warning(self._widget, "No Topics Selected", "Please check at least one topic to play.")
            return

        if self.bag_process is not None:
            QMessageBox.warning(self._widget, "Playback Running", "Bag playback is already running.")
            return

        cmd = ['ros2', 'bag', 'play', self.bag_path, '--topics'] + selected_topics
        self.bag_process = QProcess(self._widget)
        self.bag_process.setProcessChannelMode(QProcess.MergedChannels)
        self.bag_process.readyReadStandardOutput.connect(self.handle_output)
        self.bag_process.finished.connect(self.playback_finished)

         # Set ROS_DOMAIN_ID environment variable before starting process
        env = QProcessEnvironment.systemEnvironment()
        env.insert("ROS_DOMAIN_ID", str(self.domain_id_spinbox.value()))
        self.bag_process.setProcessEnvironment(env)

        self.bag_process.start(cmd[0], cmd[1:])
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.playing_indicator.setText("● Playing")
        self.playing_indicator.setStyleSheet("color: green; font-weight: bold;")

    def stop_bag(self):
        if self.bag_process:
            self.bag_process.terminate()

    def playback_finished(self):
        self.bag_process = None
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.playing_indicator.setText("● Not Playing")
        self.playing_indicator.setStyleSheet("color: gray; font-weight: bold;")
        QMessageBox.information(self._widget, "Playback Finished", "Bag playback has stopped.")

    def handle_output(self):
        output = self.bag_process.readAllStandardOutput().data().decode()
        print(output)

    def download_example_profiles(self):
        yaml_content = {
            "profile1": [
                "/topic1",
                "/topic2"
            ],
            "profile1_no_topic1": [
                "/topic2",
            ],
            "profile2": [
                "topic3",
                "topic4",
            ]
        }

        save_path, _ = QFileDialog.getSaveFileName(
            self._widget,
            "Save Example Profile As",
            "example_profiles.yaml",
            "YAML Files (*.yaml)"
        )
        if not save_path:
            return

        try:
            with open(save_path, "w") as f:
                yaml.dump(yaml_content, f, default_flow_style=False)
            QMessageBox.information(self._widget, "Success", f"Example profiles saved to:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self._widget, "Error Saving File", str(e))
