import sys
import json
from PyQt5.QtWidgets import QWidget, QApplication, QStackedWidget
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPainter, QColor, QPen
import time

class EyeWidget(QWidget):
    def __init__(self, eyes_data, parent=None):
        super().__init__(parent)
        print("Initializing EyeWidget")
        self.eyes_data = eyes_data
        self.is_blinking = False
        self.is_paused = False
        self.setGeometry(0, 0, 800, 480)
        self.setStyleSheet("background-color: black;")  # Black background as requested

        self.blink_duration = 200
        self.animation_cycle = 360  # Matches JSON animation length (360 frames)
        self.pause_duration = 1000  # 1 second pause in milliseconds
        self.frame_rate = 60  # 60 fps

        # Precompute positions and colors for performance
        self.eye_info = []
        self.pupil_info = []
        self.eyebrow_info = []
        self.eyelash_info = []
        self.mouth_info = None
        scale_x = 800 / 150
        scale_y = 480 / 150

        # Ensure we only process the correct number of eyes, pupils, etc.
        for layer in self.eyes_data:
            pos_data = layer["ks"]["p"]
            if pos_data.get("a", 0) == 1 and isinstance(pos_data["k"], list):
                keyframes = pos_data["k"]
            else:
                keyframes = [{"t": 0, "s": pos_data["k"]}]
            name = layer["nm"].lower()

            if "eye" in name and len(self.eye_info) < 2:
                outline_shape = layer["shapes"][0]
                outline_color = QColor.fromRgbF(*outline_shape["it"][0]["c"]["k"])
                if len(outline_shape["it"]) > 1:
                    fill_shape = outline_shape["it"][1]
                    fill_color = QColor.fromRgbF(*fill_shape["c"]["k"])
                else:
                    fill_color = QColor.fromRgbF(1, 1, 1)
                self.eye_info.append({
                    "keyframes": keyframes,
                    "outline_color": outline_color,
                    "fill_color": fill_color,
                    "eye_width": 30 * scale_x,
                    "eye_height": 30 * scale_y
                })
            elif "pupil" in name and len(self.pupil_info) < 2:
                pupil_shape = layer["shapes"][0]
                pupil_color = QColor.fromRgbF(*pupil_shape["it"][0]["c"]["k"])
                self.pupil_info.append({
                    "keyframes": keyframes,
                    "pupil_color": pupil_color,
                    "pupil_width": 15 * scale_x,
                    "pupil_height": 15 * scale_y
                })
            elif "eyebrow" in name and len(self.eyebrow_info) < 2:
                eyebrow_shape = layer["shapes"][0]
                eyebrow_color = QColor.fromRgbF(*eyebrow_shape["it"][0]["c"]["k"])
                pos_x, pos_y = keyframes[0]["s"]
                pos_x *= scale_x
                pos_y *= scale_y
                self.eyebrow_info.append({
                    "pos_x": pos_x,
                    "pos_y": pos_y,
                    "eyebrow_color": eyebrow_color,
                    "eyebrow_size": 5 * scale_x
                })
            elif "eyelash" in name and len(self.eyelash_info) < 2:
                eyelash_shape = layer["shapes"][0]
                eyelash_color = QColor.fromRgbF(*eyelash_shape["it"][0]["c"]["k"])
                pos_x, pos_y = keyframes[0]["s"]
                pos_x *= scale_x
                pos_y *= scale_y
                self.eyelash_info.append({
                    "pos_x": pos_x,
                    "pos_y": pos_y,
                    "eyelash_color": eyelash_color,
                    "eyelash_length": 5 * scale_x
                })
            elif "mouth" in name and self.mouth_info is None:
                mouth_shape = layer["shapes"][0]
                mouth_color = QColor.fromRgbF(*mouth_shape["it"][0]["c"]["k"])
                pos_x, pos_y = keyframes[0]["s"]
                pos_x *= scale_x
                pos_y *= scale_y
                self.mouth_info = {
                    "pos_x": pos_x,
                    "pos_y": pos_y,
                    "mouth_color": mouth_color,
                    "mouth_width": 20 * scale_x,
                    "mouth_height": 10 * scale_y
                }

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.toggle_blink)

        self.blink_duration_timer = QTimer(self)
        self.blink_duration_timer.timeout.connect(self.end_blink)

        self.blink_progress = 1.0  # 1.0: fully open, 0.0: fully closed
        self.blink_anim_timer = QTimer(self)
        self.blink_anim_timer.timeout.connect(self.update_blink_anim)
        self.blink_anim_duration = 200  # ms
        self.blink_anim_steps = 10
        self.blink_anim_step = 0
        self.blink_anim_direction = -1  # -1: closing, 1: opening

        # Timer for animation updates
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(1000 // self.frame_rate)

        # Timer for pause after animation cycle
        self.pause_timer = QTimer(self)
        self.pause_timer.setSingleShot(True)
        self.pause_timer.timeout.connect(self.start_blink_after_pause)

        self.current_frame = 0
        self.hide()
        print("EyeWidget initialized")

    def toggle_blink(self):
        self.is_blinking = True
        self.blink_anim_step = 0
        self.blink_anim_direction = -1
        self.blink_anim_timer.start(self.blink_anim_duration // self.blink_anim_steps)

    def update_blink_anim(self):
        if self.blink_anim_direction == -1:
            self.blink_progress = max(0.0, 1.0 - (self.blink_anim_step + 1) / self.blink_anim_steps)
            self.blink_anim_step += 1
            if self.blink_anim_step >= self.blink_anim_steps:
                self.blink_anim_direction = 1
                self.blink_anim_step = 0
        elif self.blink_anim_direction == 1:
            self.blink_progress = min(1.0, (self.blink_anim_step + 1) / self.blink_anim_steps)
            self.blink_anim_step += 1
            if self.blink_anim_step >= self.blink_anim_steps:
                self.blink_anim_timer.stop()
                self.is_blinking = False
                self.blink_progress = 1.0
                # Resume animation after blink
                self.is_paused = False
                self.animation_timer.start()
                self.current_frame = 0  # Reset frame to start new cycle
        self.update()

    def end_blink(self):
        self.is_blinking = False
        self.update()

    def update_animation(self):
        if self.is_paused:
            return
        self.current_frame = (self.current_frame + 1) % (self.animation_cycle + int(self.pause_duration * self.frame_rate / 1000))
        if self.current_frame >= self.animation_cycle:
            if not self.is_paused:
                self.is_paused = True
                self.animation_timer.stop()
                self.pause_timer.start(self.pause_duration)
        self.update()

    def start_blink_after_pause(self):
        self.toggle_blink()

    def paintEvent(self, event):
        print("Painting EyeWidget")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        # Use current_frame for animation, freeze during pause
        frame = min(self.current_frame, self.animation_cycle - 1) if self.is_paused else self.current_frame

        # Draw eyes
        for eye in self.eye_info:
            pos_x, pos_y = self.get_pupil_pos(eye["keyframes"], frame, 800/150, 480/150)
            eye_width = eye["eye_width"]
            eye_height = eye["eye_height"] * self.blink_progress
            outline_color = eye["outline_color"]
            fill_color = eye["fill_color"]

            if self.blink_progress > 0.05:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(outline_color)
                painter.drawEllipse(int(pos_x - eye_width // 2), int(pos_y - eye_height // 2), int(eye_width), int(eye_height))
                painter.setBrush(fill_color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(int(pos_x - eye_width // 2), int(pos_y - eye_height // 2), int(eye_width), int(eye_height))
            else:
                painter.setPen(QPen(outline_color, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawLine(int(pos_x - eye_width // 2), int(pos_y), int(pos_x + eye_width // 2), int(pos_y))

        # Draw pupils (only when eyes are open)
        if not self.is_blinking:
            for pupil in self.pupil_info:
                pos_x, pos_y = self.get_pupil_pos(pupil["keyframes"], frame, 800/150, 480/150)
                pupil_width = pupil["pupil_width"]
                pupil_height = pupil["pupil_height"]
                pupil_color = pupil["pupil_color"]

                painter.setBrush(pupil_color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(int(pos_x - pupil_width // 2), int(pos_y - pupil_height // 2), int(pupil_width), int(pupil_height))

        # Draw eyebrows
        for eyebrow in self.eyebrow_info:
            pos_x = eyebrow["pos_x"]
            pos_y = eyebrow["pos_y"]
            eyebrow_size = eyebrow["eyebrow_size"]
            eyebrow_color = eyebrow["eyebrow_color"]

            painter.setBrush(eyebrow_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(pos_x - eyebrow_size // 2), int(pos_y - eyebrow_size // 2), int(eyebrow_size), int(eyebrow_size))

        # Draw eyelashes (only when eyes are open)
        if not self.is_blinking:
            for eyelash in self.eyelash_info:
                pos_x = eyelash["pos_x"]
                pos_y = eyelash["pos_y"]
                eyelash_length = eyelash["eyelash_length"]
                eyelash_color = eyelash["eyelash_color"]

                painter.setPen(eyelash_color)
                painter.setBrush(Qt.NoBrush)
                painter.drawLine(int(pos_x - eyelash_length), int(pos_y), int(pos_x - eyelash_length // 2), int(pos_y - eyelash_length))
                painter.drawLine(int(pos_x), int(pos_y), int(pos_x), int(pos_y - eyelash_length))
                painter.drawLine(int(pos_x + eyelash_length), int(pos_y), int(pos_x + eyelash_length // 2), int(pos_y - eyelash_length))

        # Draw smiling mouth
        if self.mouth_info:
            pos_x = self.mouth_info["pos_x"]
            pos_y = self.mouth_info["pos_y"]
            mouth_width = self.mouth_info["mouth_width"]
            mouth_height = self.mouth_info["mouth_height"]
            mouth_color = self.mouth_info["mouth_color"]

            painter.setPen(QPen(mouth_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(int(pos_x - mouth_width // 2), int(pos_y - mouth_height // 2), int(mouth_width), int(mouth_height), 0 * 16, -180 * 16)

    def cleanup(self):
        self.blink_timer.stop()
        self.blink_duration_timer.stop()
        self.animation_timer.stop()
        self.pause_timer.stop()

    def get_pupil_pos(self, keyframes, frame, scale_x, scale_y):
        prev_kf = keyframes[0]
        next_kf = keyframes[-1]
        for i in range(len(keyframes) - 1):
            if keyframes[i]["t"] <= frame <= keyframes[i+1]["t"]:
                prev_kf = keyframes[i]
                next_kf = keyframes[i+1]
                break
        t0, t1 = prev_kf["t"], next_kf["t"]
        s0, s1 = prev_kf["s"], next_kf["s"]
        if t1 == t0:
            x, y = s0
        else:
            alpha = (frame - t0) / (t1 - t0)
            x = s0[0] + (s1[0] - s0[0]) * alpha
            y = s0[1] + (s1[1] - s0[1]) * alpha
        return x * scale_x, y * scale_y

class ScreensaverManager:
    def __init__(self, parent, container):
        self.parent = parent
        self.container = container
        self.current_scene = None
        self.screensaver_timer = QTimer(self.parent)
        self.screensaver_timer.setInterval(15000)
        self.screensaver_timer.timeout.connect(self.show_screensaver)

        try:
            with open("eye_animation.json", "r") as f:
                data = json.load(f)
                self.eyes_data = data["layers"]
        except Exception as e:
            print(f"Error loading eye_animation.json: {e}")
            self.eyes_data = []

        self.eye_widget = EyeWidget(self.eyes_data, self.container)
        self.container.addWidget(self.eye_widget)

        self.screensaver_timer.start()
        print("Screensaver timer started")

    def show_screensaver(self):
        print("Showing screensaver")
        self.current_scene = self.container.currentWidget()
        self.container.setCurrentWidget(self.eye_widget)
        self.eye_widget.show()
        self.eye_widget.update()

    def hide_screensaver(self):
        print("Hiding screensaver")
        if self.current_scene:
            self.container.setCurrentWidget(self.current_scene)
        else:
            self.container.setCurrentWidget(self.parent.stacked_widget)
        self.eye_widget.hide()

    def reset_timer(self):
        print("Resetting screensaver timer")
        self.screensaver_timer.stop()
        self.hide_screensaver()
        self.screensaver_timer.start()

    def cleanup(self):
        self.screensaver_timer.stop()
        if self.eye_widget:
            self.eye_widget.cleanup()

def main():
    app = QApplication(sys.argv)
    stacked_widget = QStackedWidget()
    screensaver_manager = ScreensaverManager(parent=stacked_widget, container=stacked_widget)
    stacked_widget.resize(800, 480)
    stacked_widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()