import os
import random
import json
import math
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Rectangle, Color, PushMatrix, PopMatrix, Rotate, Line
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.properties import NumericProperty, StringProperty
from kivy.utils import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    if platform not in ("android", "ios"):
        Window.size = (400, 600)
except:
    pass

ACHIEVEMENTS_DEF = [
    {"id": "score_1", "name": "NOOBDA", "score": 1, "rarity": "common"},
    {"id": "score_5", "name": "Getting Started", "score": 5, "rarity": "common"},
    {"id": "score_10", "name": "Rookie", "score": 10, "rarity": "common"},
    {"id": "score_20", "name": "Flyer", "score": 20, "rarity": "common"},
    {"id": "score_40", "name": "Pro Flyer", "score": 40, "rarity": "rare"},
    {"id": "score_60", "name": "Thakrii", "score": 50, "rarity": "rare"},
    {"id": "score_70", "name": "Pro Tharki", "score": 60, "rarity": "rare"},
    {"id": "score_69", "name": "Cream lagalo Asswin", "score": 69, "rarity": "rare"},
]


class Bird:
    def __init__(self, x, y, gamewidget):
        # Responsive bird size
        bird_height = gamewidget.height * 0.065
        bird_width = bird_height * 1.3
        self.x = x
        self.y = y
        self.velocity = 0
        self.gravity = -800
        self.jump_strength = 320
        self.width = bird_width
        self.height = bird_height
        self.angle = 0

        bird_path = os.path.join(BASE_DIR, "assets", "graphics", "bird.png")
        try:
            self.texture = CoreImage(bird_path).texture
        except:
            self.texture = None

    def update(self, dt):
        self.velocity += self.gravity * dt
        self.y += self.velocity * dt

        if self.velocity > 0:
            self.angle = min(25, self.velocity * 0.08)
        else:
            self.angle = max(-90, self.velocity * 0.08)

    def jump(self):
        self.velocity = self.jump_strength

    def reset(self, x, y):
        self.x = x
        self.y = y
        self.velocity = 0
        self.angle = 0


class Pipe:
    def __init__(self, x, y, height, is_top=False, gamewidget=None):
        self.x = x
        self.y = y
        self.width = gamewidget.width * 0.2 if gamewidget else 70
        self.height = height
        self.is_top = is_top
        self.speed = 155

        if is_top:
            pipe_path = os.path.join(BASE_DIR, "assets", "graphics", "pipe_top.png")
        else:
            pipe_path = os.path.join(BASE_DIR, "assets", "graphics", "pipe_bottom.png")

        try:
            self.texture = CoreImage(pipe_path).texture
        except:
            self.texture = None

    def update(self, dt):
        self.x -= self.speed * dt

    def is_offscreen(self):
        return self.x + self.width < 0


class PipePair:
    def __init__(self, x, gap, window_height, gamewidget):
        pipe_width = gamewidget.width * 0.13
        min_gap = gamewidget.height * 0.2
        max_gap = gamewidget.height * 0.25
        gap = max(min_gap, min(max_gap, gap))
        self.gap = gap
        self.x = x
        self.scored = False

        variance = random.uniform(-18, 18)
        bottom_height = (
            random.uniform(
                window_height * 0.12, window_height - gap - window_height * 0.18
            )
            + variance
        )
        bottom_height = max(
            window_height * 0.10,
            min(window_height - gap - window_height * 0.10, bottom_height),
        )

        self.bottom_pipe = Pipe(
            x, 0, bottom_height, is_top=False, gamewidget=gamewidget
        )
        top_y = bottom_height + gap
        top_height = window_height - top_y
        self.top_pipe = Pipe(x, top_y, top_height, is_top=True, gamewidget=gamewidget)

    def update(self, dt):
        self.bottom_pipe.update(dt)
        self.top_pipe.update(dt)
        self.x = self.bottom_pipe.x

    def is_offscreen(self):
        return self.bottom_pipe.is_offscreen()

    def check_collision(self, bird):
        bird_left = bird.x - bird.width / 2
        bird_right = bird.x + bird.width / 2
        bird_top = bird.y + bird.height / 2
        bird_bottom = bird.y - bird.height / 2

        pipe_left = self.bottom_pipe.x
        pipe_right = self.bottom_pipe.x + self.bottom_pipe.width

        if bird_right > pipe_left and bird_left < pipe_right:
            if bird_bottom < self.bottom_pipe.height or bird_top > self.top_pipe.y:
                return True
        return False


class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ""
        self.background_down = ""

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        return False


class GameWidget(Widget):
    score = NumericProperty(0)
    high_score = NumericProperty(0)
    state = StringProperty("menu")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.update_layout, pos=self.update_layout)
        self.bird = None
        self.pipes = []
        self.sounds = {}
        self.game_loop = None
        self.pipe_spawn_event = None
        self.blink_time = 0
        self.dead_bird_pos = None
        self.save_path = os.path.join(BASE_DIR, "highscore.json")
        self.load_high_score()

        # achievements
        self.achievements_path = os.path.join(BASE_DIR, "achievements.json")
        self.unlocked_achievements = set()
        self.load_achievements()

        self.achievement_banner_label = Label(
            text="", font_size=24, bold=True, size_hint=(None, None), color=(1, 1, 1, 1)
        )
        self.add_widget(self.achievement_banner_label)
        self.achievement_banner_label.opacity = 0
        self.achievement_banner_visible = False
        self.achievement_banner_time = 0
        self.achievement_banner_target = ""

        self.achievements_button = StyledButton(
            text="ACHIEVEMENTS",
            size_hint=(None, None),
            font_size=22,
            bold=True,
            color=(0, 0, 0, 1),
        )
        
        self.achievements_button.bind(on_press=self.on_achievements_pressed)
        self.add_widget(self.achievements_button)

        self.achievements_close_button = StyledButton(
            text='',
            size_hint=(None, None),
            color=(0, 0, 0, 0)  # text invisible
        )
        self.achievements_close_button.bind(on_press=self.close_achievements_menu)
        self.achievements_close_button.bind(on_press=self.on_close_achievements_pressed)

        self.achievements_menu_open = False
        self.achievements_labels = []

        self.title_label = Label(
            text="FLAPPY Veejayy",
            font_size=52,
            bold=True,
            size_hint=(None, None),
            color=(1, 1, 1, 1),
            outline_width=2,
            outline_color=(0, 0, 0, 0),
        )
        self.add_widget(self.title_label)

        self.instruction_label = Label(
            text="Click to Flap",
            font_size=20,
            size_hint=(None, None),
            color=(0, 0, 0, 1),
        )
        self.add_widget(self.instruction_label)

        self.start_button = StyledButton(
            text="START",
            size_hint=(None, None),
            font_size=35,
            bold=True,
            color=(0, 0, 0, 1),
        )
        self.start_button.bind(on_press=self.start_game)
        self.start_button.bind(on_press=self.on_start_pressed)
        self.add_widget(self.start_button)

        self.developer_label = Label(
            text="by ~Rowdy", font_size=14, size_hint=(None, None), color=(1, 1, 1, 1)
        )
        self.add_widget(self.developer_label)

        self.game_over_label = Label(
            text="Chaat..se..Tamacha",
            font_size=60,
            bold=True,
            size_hint=(None, None),
            color=(0.9, 0.1, 0.1, 1),
            outline_width=2,
            outline_color=(1, 1, 1, 1),
        )

        self.score_display_label = Label(
            text="Score: 0",
            font_size=34,
            bold=True,
            size_hint=(None, None),
            color=(1, 1, 1, 1),
        )

        self.high_score_display_label = Label(
            text="High Score: 0",
            font_size=34,
            bold=True,
            size_hint=(None, None),
            color=(1, 1, 1, 1),
        )

        self.restart_button = StyledButton(
            text="RESTART",
            size_hint=(None, None),
            font_size=32,
            bold=True,
            color=(0, 0, 0, 1),
        )
        self.restart_button.bind(on_press=self.restart_game)

        self.score_label = Label(
            text="0",
            font_size=72,
            bold=True,
            size_hint=(None, None),
            color=(1, 1, 0, 1),
            outline_width=3,
            outline_color=(0, 0, 0, 1),
        )



        Clock.schedule_once(self.load_sounds, 0.1)
        Clock.schedule_once(self.play_start_sound, 0.2)
        Clock.schedule_interval(self.update_blink, 0.5)
        Clock.schedule_interval(self.draw_ui, 1 / 60)

    def play_button_click(self):
        self.play_sound('click')

    def on_start_pressed(self, *args):
        self.play_button_click()
        self.start_game()

    def on_restart_pressed(self, *args):
        self.play_button_click()
        self.restart_game()

    def on_achievements_pressed(self, *args):
        self.play_button_click()
        self.toggle_achievements_menu()

    def on_close_achievements_pressed(self, *args):
        self.play_button_click()
        self.close_achievements_menu()
    
    def close_achievements_menu(self, *args):
        if not self.achievements_menu_open:
            return
        self.achievements_menu_open = False
        self.achievements_button.disabled = False
        self.start_button.disabled = False
        
        # remove labels
        for lbl in self.achievements_labels:
            self.remove_widget(lbl)
        self.achievements_labels = []

        # remove canvas objects safely
        for attr in ('ach_box_bg', 'ach_box_border', 'ach_close_circle'):
            try:
                if hasattr(self, attr):
                    self.canvas.remove(getattr(self, attr))
                    delattr(self, attr) 
            except:
                pass

    def load_high_score(self):
        try:
            if os.path.exists(self.save_path):
                with open(self.save_path, "r") as f:
                    data = json.load(f)
                    self.high_score = int(data.get("high_score", 0))
            else:
                self.high_score = 0
        except:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {"high_score": int(self.high_score)}
            with open(self.save_path, "w") as f:
                json.dump(data, f)
        except:
            pass

    def load_achievements(self):
        try:
            if os.path.exists(self.achievements_path):
                with open(self.achievements_path, "r") as f:
                    data = json.load(f)
                    ids = data.get("unlocked", [])
                    self.unlocked_achievements = set(ids)
            else:
                self.unlocked_achievements = set()
        except:
            self.unlocked_achievements = set()

    def save_achievements(self):
        try:
            data = {"unlocked": list(self.unlocked_achievements)}
            with open(self.achievements_path, "w") as f:
                json.dump(data, f)
        except:
            pass

    def toggle_achievements_menu(self, *args):
        self.achievements_menu_open = not self.achievements_menu_open

        if self.achievements_menu_open:
            self.start_button.disabled = True
            self.achievements_button.disabled = True
        else:
            self.start_button.disabled = False
            self.achievements_button.disabled = False
        
    # clear old labels AND canvas objects SAFELY
        for lbl in self.achievements_labels:
            self.remove_widget(lbl)
        self.achievements_labels = []
    
    # Clear achievement box canvas SAFELY
        try:
            if hasattr(self, 'ach_box_bg'):
                self.canvas.before.remove(self.ach_box_bg)
                delattr(self, 'ach_box_bg')
        except:
            pass
        try:
            if hasattr(self, 'ach_box_border'):
                self.canvas.before.remove(self.ach_box_border)
                delattr(self, 'ach_box_border')
        except:
            pass

        if not self.achievements_menu_open:
            return

    # Create achievements box ON SEPARATE CANVAS LAYER
        box_width = self.width * 0.9
        box_height = self.height * 0.5
        box_x = (self.width - box_width) / 2
        box_y = (self.height - box_height) / 2

    # Use canvas (not canvas.before) for overlay
        with self.canvas:
            Color(0.05, 0.05, 0.05, 0.98)
            self.ach_box_bg = Rectangle(pos=(box_x, box_y), size=(box_width, box_height))
        
            Color(1, 0.8, 0, 1)
            self.ach_box_border = Line(rectangle=(box_x, box_y, box_width, box_height), width=4)

    # Title
        title = Label(
            text='ACHIEVEMENTS',
            font_size=min(self.height * 0.045, self.width * 0.08),
            bold=True,
            size_hint=(None, None),
            size=(box_width * 0.9, self.height * 0.07),
            color=(1, 1, 0.3, 1),
            pos=(box_x + box_width*0.05, box_y + box_height - self.height * 0.08)
        )
        self.add_widget(title)
        self.achievements_labels.append(title)

            # Close (red dot) button in top-right of box
        close_size = self.height * 0.035
        self.achievements_close_button.size = (close_size, close_size)
        self.achievements_close_button.pos = (box_x + box_width - close_size*1.5,box_y + box_height - close_size*1.5)
        self.add_widget(self.achievements_close_button)
        self.achievements_labels.append(self.achievements_close_button)

    # Red dot decoration
        with self.canvas:
            Color(0.9, 0.1, 0.1, 1)
            self.ach_close_circle = Rectangle(
                pos=self.achievements_close_button.pos,
                size=self.achievements_close_button.size
            )


    # Achievements list
        scroll_y = box_y + box_height - self.height * 0.12
        for ach in ACHIEVEMENTS_DEF:
            if scroll_y < box_y + self.height * 0.06:
                break
            
            status = "UNLOCKED" if ach["id"] in self.unlocked_achievements else "LOCKED"
            rarity = ach.get("rarity", "common").upper()
        
            lbl = Label(
               text=f"{ach['name']} [{rarity}] - {status}",
                font_size=min(self.height * 0.03, self.width * 0.05),
                bold=True,
                size_hint=(None, None),
                size=(box_width * 0.88, self.height * 0.045),
                color=(0.3, 1, 0.3, 1) if status == "UNLOCKED" else (0.8, 0.8, 0.8, 1),
                pos=(box_x + box_width*0.06, scroll_y)
            )
            self.add_widget(lbl)
            self.achievements_labels.append(lbl)
            scroll_y -= self.height * 0.05



    def check_achievements(self):
        for ach in ACHIEVEMENTS_DEF:
            if (
                self.score >= ach["score"]
                and ach["id"] not in self.unlocked_achievements
            ):
                self.unlock_achievement(ach)

    def unlock_achievement(self, ach):
        self.unlocked_achievements.add(ach["id"])
        self.save_achievements()

        # skip sound for specific achievement id
        if ach["id"] == "score_69":  # change to any id you want
            pass
        else:
            rarity = ach.get("rarity", "common")
            key = 'achievement_rare' if rarity == 'rare' else 'achievement_common'
            if key in self.sounds:
                self.sounds[key].play()

        self.achievement_banner_label.text = f"{ach['name']}"
        self.achievement_banner_visible = True
        self.achievement_banner_time = 0
        self.achievement_banner_label.opacity = 1

    def draw_wavy_border(self):
        points = []
        wave_amplitude = 8
        segments = 50

        for i in range(segments + 1):
            t = i / segments
            x = t * self.width
            y = self.height - 15 + wave_amplitude * math.sin(t * math.pi * 4)
            points.extend([x, y])

        for i in range(segments + 1):
            t = i / segments
            x = self.width - (t * self.width)
            y = 15 - wave_amplitude * math.sin(t * math.pi * 4)
            points.extend([x, y])

        return points

    def draw_button(self, button):
        with button.canvas.before:
            button.canvas.before.clear()

            # Main button background with gradient effect
            Color(0.3, 0.8, 0.3, 1)  # Darker green
            Rectangle(
                pos=(button.pos[0], button.pos[1]),
                size=(button.size[0], button.size[1]),
            )

            # Gold border + shine effect for achievements button
            if button == self.achievements_button:
                # Gold outer glow
                Color(1, 0.84, 0, 0.6)
                Line(
                    rectangle=(
                        button.pos[0] - 3,
                        button.pos[1] - 3,
                        button.size[0] + 6,
                        button.size[1] + 6,
                    ),
                    width=4,
                )

                # Inner gold border
                Color(1, 0.9, 0.4, 1)
                Line(
                    rectangle=(
                        button.pos[0],
                        button.pos[1],
                        button.size[0],
                        button.size[1],
                    ),
                    width=3,
                )

                # Shine highlight
                Color(1, 1, 1, 0.4)
                Rectangle(
                    pos=(button.pos[0] + 5, button.pos[1] + button.size[1] * 0.7),
                    size=(button.size[0] * 0.3, button.size[1] * 0.1),
                )
            else:
                # Regular button (START/RESTART)
                Color(0.5, 0.85, 0.4, 1)
                Rectangle(pos=button.pos, size=button.size)
                Color(0, 0, 0, 1)
                Line(
                    rectangle=(
                        button.pos[0],
                        button.pos[1],
                        button.size[0],
                        button.size[1],
                    ),
                    width=3,
                )

    def draw_menu_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.53, 0.81, 0.92, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

            Color(0.85, 0.65, 0.13, 1)
            Rectangle(
                pos=(0, 0), size=(self.width, self.height * 0.07)
            )  # responsive ground

            wavy_points = self.draw_wavy_border()
            if len(wavy_points) > 4:
                Color(0.35, 0.55, 0.62, 1)
                Line(points=wavy_points, width=2, close=True)

    def draw_ui(self, dt):
        if self.state == "menu":
            self.draw_menu_background()
        self.draw_button(self.start_button)
        self.draw_button(self.restart_button)
        self.draw_button(self.achievements_button)

    def update_blink(self, dt):
        self.blink_time += dt
        if self.state == "menu":
            alpha = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(self.blink_time * 4))
            self.instruction_label.color = (0, 0, 0, alpha)

    def update_layout(self, *args):
        self.title_label.font_size = min(self.height * 0.07, self.width * 0.09)
        self.instruction_label.font_size = min(self.height * 0.033, self.width * 0.05)
        self.start_button.font_size = min(self.height * 0.045, self.width * 0.07)
        self.achievements_button.font_size = min(self.height * 0.035, self.width * 0.06)
        self.achievements_button.size = (self.width * 0.5, self.height * 0.07)
        self.achievements_button.pos = (self.width * 0.25, self.height * 0.33)
        self.developer_label.font_size = min(self.height * 0.027, self.width * 0.034)
        self.game_over_label.font_size = min(self.height * 0.07, self.width * 0.09)
        self.score_display_label.font_size = min(
            self.height * 0.032, self.width * 0.048
        )
        self.high_score_display_label.font_size = min(
            self.height * 0.032, self.width * 0.048
        )
        self.restart_button.font_size = min(self.height * 0.045, self.width * 0.07)
        self.score_label.font_size = min(self.height * 0.08, self.width * 0.11)

        self.title_label.size = (self.width * 0.85, self.height * 0.12)
        self.title_label.pos = (self.width * 0.075, self.height * 0.76)
        self.instruction_label.size = (self.width * 0.8, self.height * 0.05)
        self.instruction_label.pos = (self.width * 0.10, self.height * 0.63)
        self.start_button.size = (self.width * 0.5, self.height * 0.09)
        self.start_button.pos = (self.width * 0.25, self.height * 0.44)
        self.developer_label.size = (self.width * 0.28, self.height * 0.03)
        self.developer_label.pos = (self.width * 0.70, self.height * 0.97)
        self.game_over_label.size = (self.width * 0.8, self.height * 0.11)
        self.game_over_label.pos = (self.width * 0.10, self.height * 0.72)
        self.score_display_label.size = (self.width * 0.9, self.height * 0.06)
        self.score_display_label.pos = (self.width * 0.05, self.height * 0.49)
        self.high_score_display_label.size = (self.width * 0.9, self.height * 0.06)
        self.high_score_display_label.pos = (self.width * 0.05, self.height * 0.43)
        self.restart_button.size = (self.width * 0.5, self.height * 0.09)
        self.restart_button.pos = (self.width * 0.25, self.height * 0.22)
        self.score_label.size = (self.width * 0.24, self.height * 0.09)
        self.score_label.pos = (self.width * 0.38, self.height * 0.87)
        self.achievement_banner_label.font_size = min(
            self.height * 0.035, self.width * 0.055
        )
        self.achievement_banner_label.size = (self.width * 0.5, self.height * 0.08)
        self.achievement_banner_label.pos = (self.width, self.height * 0.90)

    def load_sounds(self, dt):
        use_ogg = True  # Set this to False to use wav; True for ogg

        def find_audio(folder, name):
            ext = ".ogg" if use_ogg else ".wav"
            path = os.path.join(BASE_DIR, folder, name + ext)
            if os.path.exists(path):
                return path
            return None

        sound_files = {
            "flap": find_audio("assets/sfx", "flap"),
            "click": find_audio("assets/sfx", "click"),
            "point": find_audio("assets/sfx", "point"),
            "background_music": find_audio("assets/sfx", "background_music"),
            "achievement_common": find_audio("assets/sfx", "achievement_common"),
            "special_ashwin": find_audio("assets/sfx", "special_ashwin"),
            "achievement_rare": find_audio("assets/sfx", "achievement_rare"),
        }

        for name, path in sound_files.items():
            if path:
                try:
                    sound = SoundLoader.load(path)
                    if sound:
                        if name == "flap" or name == "point":
                            sound.volume = 0.3
                        elif name == "background_music":
                            sound.volume = 0.3
                            sound.loop = True
                        elif name == 'button':
                            sound.volume = 0.6
                        elif name.startswith("achievement_"):
                            sound.volume = 0.8
                        self.sounds[name] = sound
                except:
                    pass

        death_dir = os.path.join(BASE_DIR, "assets", "sfx", "deaths")
        start_dir = os.path.join(BASE_DIR, "assets", "sfx", "starts")

        self.sounds["deaths"] = []
        self.sounds["starts"] = []

        ext = ".ogg" if use_ogg else ".wav"
        for dir_path, sound_list, vol in [
            (death_dir, self.sounds["deaths"], 0.9),
            (start_dir, self.sounds["starts"], 1),
        ]:
            try:
                for file in os.listdir(dir_path):
                    if file.endswith(ext):
                        try:
                            sound = SoundLoader.load(os.path.join(dir_path, file))
                            if sound:
                                sound.volume = vol
                                sound_list.append(sound)
                        except:
                            pass
            except:
                pass

    def play_start_sound(self, dt):
        if self.sounds.get("starts"):
            random.choice(self.sounds["starts"]).play()

    def play_sound(self, name):
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].play()

    def start_game(self, *args):
        
        if self.state == 'playing':
            return  # already in game, do nothing

        self.state = 'playing'
        self.score = 0
        self.pipes = []
        self.dead_bird_pos = None

        self.bird = Bird(self.width * 0.25, self.height * 0.5, self)

        # make sure score_label has no parent before adding
        if self.score_label.parent is not None:
            self.remove_widget(self.score_label)

        if self.start_button.parent is not None:
            self.remove_widget(self.start_button)
        if self.instruction_label.parent is not None:
            self.remove_widget(self.instruction_label)
        if self.title_label.parent is not None:
            self.remove_widget(self.title_label)
        if self.developer_label.parent is not None:
            self.remove_widget(self.developer_label)
        if self.achievements_button.parent is not None:
            self.remove_widget(self.achievements_button)

        self.add_widget(self.score_label)

        self.game_loop = Clock.schedule_interval(self.update_game, 1 / 60)
        self.pipe_spawn_event = Clock.schedule_interval(self.spawn_pipe, 3.2)

        if 'background_music' in self.sounds:
            self.sounds['background_music'].play()


    def restart_game(self, *args):
        self.remove_widget(self.restart_button)
        self.remove_widget(self.game_over_label)
        self.remove_widget(self.score_display_label)
        self.remove_widget(self.high_score_display_label)
        self.restart_button.bind(on_press=self.on_restart_pressed)
        self.start_game()

    def spawn_pipe(self, dt):
        gap = self.height * 0.28 - (self.score * 1.5)
        pipe_pair = PipePair(self.width, gap, self.height, self)
        self.pipes.append(pipe_pair)

    def update_game(self, dt):
        if self.state != "playing":
            return

        self.bird.update(dt)

        if self.bird.y < 0 or self.bird.y > self.height - self.height * 0.07:
            self.game_over()
            return

        for pipe_pair in self.pipes[:]:
            pipe_pair.update(dt)

            if pipe_pair.check_collision(self.bird):
                self.game_over()
                return

            if (
                not pipe_pair.scored
                and pipe_pair.x + pipe_pair.bottom_pipe.width < self.bird.x
            ):
                pipe_pair.scored = True
                self.score += 1

                if self.score == 69:
                    self.play_sound("special_ashwin")

                else:
                    self.play_sound("point")

                self.check_achievements()

            if pipe_pair.is_offscreen():
                self.pipes.remove(pipe_pair)

        self.canvas.before.clear()
        with self.canvas.before:
            # Draw background
            Color(0.53, 0.81, 0.92, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

            # Ground
            Color(0.85, 0.65, 0.13, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height * 0.07))

            # Pipes
            for pipe_pair in self.pipes:
                if pipe_pair.bottom_pipe.texture:
                    Color(1, 1, 1, 1)
                    Rectangle(
                        pos=(pipe_pair.bottom_pipe.x, pipe_pair.bottom_pipe.y),
                        size=(
                            pipe_pair.bottom_pipe.width,
                            pipe_pair.bottom_pipe.height,
                        ),
                        texture=pipe_pair.bottom_pipe.texture,
                    )
                else:
                    Color(0.4, 0.4, 0.4, 1)
                    Rectangle(
                        pos=(pipe_pair.bottom_pipe.x, pipe_pair.bottom_pipe.y),
                        size=(
                            pipe_pair.bottom_pipe.width,
                            pipe_pair.bottom_pipe.height,
                        ),
                    )

                if pipe_pair.top_pipe.texture:
                    Color(1, 1, 1, 1)
                    Rectangle(
                        pos=(pipe_pair.top_pipe.x, pipe_pair.top_pipe.y),
                        size=(pipe_pair.top_pipe.width, pipe_pair.top_pipe.height),
                        texture=pipe_pair.top_pipe.texture,
                    )
                else:
                    Color(0.4, 0.4, 0.4, 1)
                    Rectangle(
                        pos=(pipe_pair.top_pipe.x, pipe_pair.top_pipe.y),
                        size=(pipe_pair.top_pipe.width, pipe_pair.top_pipe.height),
                    )

            # Bird
            PushMatrix()
            Rotate(angle=self.bird.angle, origin=(self.bird.x, self.bird.y))
            Color(1, 1, 1, 1)
            if self.bird.texture:
                Rectangle(
                    pos=(
                        self.bird.x - self.bird.width / 2,
                        self.bird.y - self.bird.height / 2,
                    ),
                    size=(self.bird.width, self.bird.height),
                    texture=self.bird.texture,
                )
            else:
                Color(1, 0.8, 0, 1)
                Rectangle(
                    pos=(
                        self.bird.x - self.bird.width / 2,
                        self.bird.y - self.bird.height / 2,
                    ),
                    size=(self.bird.width, self.bird.height),
                )
            PopMatrix()

        self.score_label.text = str(self.score)

        if self.achievement_banner_visible:
            self.achievement_banner_time += dt
            cur_x, cur_y = self.achievement_banner_label.pos
            target_x = self.width * 0.40

            # Banner background
            with self.canvas.before:
                Color(0, 0, 0, 0.9)
                banner_x = self.achievement_banner_label.pos[0]
                Rectangle(
                    pos=(banner_x, self.height * 0.90),
                    size=(self.width * 0.6, self.height * 0.08),
                )
            t = self.achievement_banner_time

            if t <= 0.5:  # slide in with ease-out
                k = t / 0.5
                k = 1 - (1 - k) * (1 - k)
                new_x = self.width + (target_x - self.width) * k
                self.achievement_banner_label.pos = (new_x, cur_y)
            elif t <= 2.2:  # stay
                self.achievement_banner_label.pos = (target_x, cur_y)
            elif t <= 2.7:  # slide out with ease-in
                k = (t - 2.2) / 0.5
                k = k * k
                new_x = target_x + (self.width - target_x) * k
                self.achievement_banner_label.pos = (new_x, cur_y)
            else:
                self.achievement_banner_visible = False
                self.achievement_banner_label.pos = (self.width, cur_y)
                self.achievement_banner_label.opacity = 0


    def game_over(self):
        self.state = "game_over"

        self.dead_bird_pos = (self.bird.x, self.bird.y, self.bird.angle)

        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

        if self.game_loop:
            self.game_loop.cancel()
        if self.pipe_spawn_event:
            self.pipe_spawn_event.cancel()

        if "background_music" in self.sounds:
            self.sounds["background_music"].stop()

        if self.sounds.get("deaths"):
            random.choice(self.sounds["deaths"]).play()

        self.remove_widget(self.score_label)

        self.score_display_label.text = f"Score: {self.score}"
        self.high_score_display_label.text = f"High Score: {self.high_score}"

        self.add_widget(self.game_over_label)
        self.add_widget(self.score_display_label)
        self.add_widget(self.high_score_display_label)
        self.add_widget(self.restart_button)
        self.add_widget(self.developer_label)

        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.53, 0.81, 0.92, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

            Color(0.85, 0.65, 0.13, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height * 0.07))

            wavy_points = self.draw_wavy_border()
            if len(wavy_points) > 4:
                Color(0.35, 0.55, 0.62, 1)
                Line(points=wavy_points, width=2, close=True)

            if self.dead_bird_pos:
                PushMatrix()
                Rotate(
                    angle=self.dead_bird_pos[2],
                    origin=(self.dead_bird_pos[0], self.dead_bird_pos[1]),
                )
                Color(1, 1, 1, 1)
                if self.bird and self.bird.texture:
                    Rectangle(
                        pos=(
                            self.dead_bird_pos[0] - self.bird.width / 2,
                            self.dead_bird_pos[1] - self.bird.height / 2,
                        ),
                        size=(self.bird.width, self.bird.height),
                        texture=self.bird.texture,
                    )
                else:
                    Color(1, 0.8, 0, 1)
                    Rectangle(
                        pos=(self.dead_bird_pos[0] - 25, self.dead_bird_pos[1] - 19),
                        size=(50, 38),
                    )
                PopMatrix()

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True

        if self.state == "playing":
            self.bird.jump()
            self.play_sound("flap")
            return True

        return False

    def on_key_down(self, window, key, *args):
        if self.state == "playing" and key == 32:
            self.bird.jump()
            self.play_sound("flap")


class FlappyApp(App):
    def build(self):
        self.title = "Flappy Veejayy"
        game = GameWidget()
        Window.bind(on_key_down=game.on_key_down)
        return game


if __name__ == "__main__":
    FlappyApp().run()
