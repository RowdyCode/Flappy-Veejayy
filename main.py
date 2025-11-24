import os
import random
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
    if platform not in ('android', 'ios'): 
        Window.size = (400, 600)
except:
    pass


class Bird:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.velocity = 0
        self.gravity = -800
        self.jump_strength = 320
        self.width = 50
        self.height = 60
        self.angle = 0
        
        bird_path = os.path.join(BASE_DIR, 'assets', 'graphics', 'bird.png')
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
    def __init__(self, x, y, height, is_top=False):
        self.x = x
        self.y = y
        self.width = 70
        self.height = height
        self.is_top = is_top
        self.speed = 150
        
        if is_top:
            pipe_path = os.path.join(BASE_DIR, 'assets', 'graphics', 'pipe_top.png')
        else:
            pipe_path = os.path.join(BASE_DIR, 'assets', 'graphics', 'pipe_bottom.png')
        
        try:
            self.texture = CoreImage(pipe_path).texture
        except:
            self.texture = None
    
    def update(self, dt):
        self.x -= self.speed * dt
    
    def is_offscreen(self):
        return self.x + self.width < 0


class PipePair:
    def __init__(self, x, gap, window_height):
        base_gap = 170
        min_gap = 160
        max_gap = 220
        
        self.gap = max(min_gap, min(max_gap, gap))
        self.x = x
        self.scored = False
        
        variance = random.uniform(-18, 18)
        bottom_height = random.uniform(100, window_height - self.gap - 150) + variance
        bottom_height = max(80, min(window_height - self.gap - 80, bottom_height))
        
        self.bottom_pipe = Pipe(x, 0, bottom_height, is_top=False)
        top_y = bottom_height + self.gap
        top_height = window_height - top_y
        self.top_pipe = Pipe(x, top_y, top_height, is_top=True)
    
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
        self.background_normal = ''
        self.background_down = ''
        
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        return False


class GameWidget(Widget):
    score = NumericProperty(0)
    high_score = NumericProperty(0)
    state = StringProperty('menu')
    
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
        
        self.title_label = Label(
            text='FLAPPY Veejayy',
            font_size=52,
            bold=True,
            size_hint=(None, None),
            size=(400, 80),
            color=(1, 1, 1, 1),
            outline_width=2,
            outline_color=(0, 0, 0, 0)
        )
        self.add_widget(self.title_label)
        
        self.instruction_label = Label(
            text='Press SPACE or Click to Flap',
            font_size=20,
            size_hint=(None, None),
            size=(400, 40),
            color=(0, 0, 0, 1)
        )
        self.add_widget(self.instruction_label)
        
        self.start_button = StyledButton(
            text='START',
            size_hint=(None, None),
            size=(200, 55),
            font_size=32,
            bold=True,
            color=(0, 0, 0, 1)
        )
        self.start_button.bind(on_press=self.start_game)
        self.add_widget(self.start_button)
        
        self.developer_label = Label(
            text='by ~Rowdy',
            font_size=14,
            size_hint=(None, None),
            size=(180, 10),
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.developer_label)
        
        self.game_over_label = Label(
            text='GAME OVER',
            font_size=60,
            bold=True,
            size_hint=(None, None),
            size=(400, 80),
            color=(0.9, 0.1, 0.1, 1)
        )
        
        self.score_display_label = Label(
            text='Score: 0',
            font_size=34,
            bold=True,
            size_hint=(None, None),
            size=(400, 50),
            color=(1, 1, 1, 1)
        )
        
        self.high_score_display_label = Label(
            text='High Score: 0',
            font_size=34,
            bold=True,
            size_hint=(None, None),
            size=(400, 50),
            color=(1, 1, 1, 1)
        )
        
        self.restart_button = StyledButton(
            text='RESTART',
            size_hint=(None, None),
            size=(200, 55),
            font_size=32,
            bold=True,
            color=(0, 0, 0, 1)
        )
        self.restart_button.bind(on_press=self.restart_game)
        
        self.score_label = Label(
            text='0',
            font_size=72,
            bold=True,
            size_hint=(None, None),
            size=(200, 80),
            color=(1, 1, 1, 1)
        )
        
        self.bind(size=self.update_layout, pos=self.update_layout)
        Clock.schedule_once(self.load_sounds, 0.1)
        Clock.schedule_once(self.play_start_sound, 0.2)
        Clock.schedule_interval(self.update_blink, 0.5)
        Clock.schedule_interval(self.draw_ui, 1/60)
    
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
            Color(0.5, 0.85, 0.4, 1)
            Rectangle(pos=button.pos, size=button.size)
            Color(0, 0, 0, 1)
            Line(rectangle=(button.pos[0], button.pos[1], button.size[0], button.size[1]), width=3)
    
    def draw_menu_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.53, 0.81, 0.92, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height))
            
            Color(0.85, 0.65, 0.13, 1)
            Rectangle(pos=(0, 0), size=(self.width, 80))
            
            wavy_points = self.draw_wavy_border()
            if len(wavy_points) > 4:
                Color(0.35, 0.55, 0.62, 1)
                Line(points=wavy_points, width=2, close=True)
    
    def draw_ui(self, dt):
        if self.state == 'menu':
            self.draw_menu_background()
        
        self.draw_button(self.start_button)
        self.draw_button(self.restart_button)
    
    def update_blink(self, dt):
        self.blink_time += dt
        if self.state == 'menu':
            alpha = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(self.blink_time * 4))
            self.instruction_label.color = (0, 0, 0, alpha)
    
    def update_layout(self, *args):

      # Dynamic Font Sizes
      self.title_label.font_size = self.height * 0.07
      self.instruction_label.font_size = self.height * 0.033
      self.start_button.font_size = self.height * 0.045
      self.developer_label.font_size = self.height * 0.027
      self.game_over_label.font_size = self.height * 0.07
      self.score_display_label.font_size = self.height * 0.032
      self.high_score_display_label.font_size = self.height * 0.032
      self.restart_button.font_size = self.height * 0.045
      self.score_label.font_size = self.height * 0.08

    # Dynamic Sizes and Positions
      self.title_label.size = (self.width * 0.8, self.height * 0.13)
      self.title_label.pos = (self.width * 0.1, self.height * 0.75)
      self.instruction_label.size = (self.width * 0.8, self.height * 0.05)
      self.instruction_label.pos = (self.width * 0.1, self.height * 0.63)
      self.start_button.size = (self.width * 0.42, self.height * 0.08)
      self.start_button.pos = (self.width * 0.29, self.height * 0.44)
      self.developer_label.size = (self.width * 0.27, self.height * 0.025)
      self.developer_label.pos = (self.width * 0.70, self.height * 0.97)

      self.game_over_label.size = (self.width * 0.8, self.height * 0.13)
      self.game_over_label.pos = (self.width * 0.12, self.height * 0.72)
      self.score_display_label.size = (self.width * 0.9, self.height * 0.06)
      self.score_display_label.pos = (self.width * 0.05, self.height * 0.48)
      self.high_score_display_label.size = (self.width * 0.9, self.height * 0.06)
      self.high_score_display_label.pos = (self.width * 0.05, self.height * 0.41)
      self.restart_button.size = (self.width * 0.42, self.height * 0.08)
      self.restart_button.pos = (self.width * 0.28, self.height * 0.23)
      self.score_label.size = (self.width * 0.2, self.height * 0.09)
      self.score_label.pos = (self.width * 0.40, self.height * 0.88)
    
    def load_sounds(self, dt):
        use_ogg = True  # Set this to False to use wav; True for ogg

        def find_audio(folder, name):
            ext = '.ogg' if use_ogg else '.wav'
            path = os.path.join(BASE_DIR, folder, name + ext)
            if os.path.exists(path):
                return path
            return None

        sound_files = {
            'flap': find_audio('assets/sfx', 'flap'),
            'point': find_audio('assets/sfx', 'point'),
            'background_music': find_audio('assets/sfx', 'background_music')
        }

        for name, path in sound_files.items():
            if path:
                try:
                    sound = SoundLoader.load(path)
                    if sound:
                        if name == 'flap' or name == 'point':
                            sound.volume = 0.3
                        elif name == 'background_music':
                            sound.volume = 0.5
                            sound.loop = True
                        self.sounds[name] = sound
                except:
                    pass

        death_dir = os.path.join(BASE_DIR, 'assets', 'sfx', 'deaths')
        start_dir = os.path.join(BASE_DIR, 'assets', 'sfx', 'starts')

        self.sounds['deaths'] = []
        self.sounds['starts'] = []

        ext = '.ogg' if use_ogg else '.wav'
        for dir_path, sound_list, vol in [
            (death_dir, self.sounds['deaths'], 0.9),
            (start_dir, self.sounds['starts'], 1),
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
        if self.sounds.get('starts'):
            random.choice(self.sounds['starts']).play()
    
    def play_sound(self, name):
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].play()
    
    def start_game(self, *args):
        self.state = 'playing'
        self.score = 0
        self.pipes = []
        self.dead_bird_pos = None
        
        self.bird = Bird(self.width * 0.3, self.height / 2)
        
        self.remove_widget(self.start_button)
        self.remove_widget(self.instruction_label)
        self.remove_widget(self.title_label)
        self.remove_widget(self.developer_label)
        
        self.add_widget(self.score_label)
        
        self.game_loop = Clock.schedule_interval(self.update_game, 1 / 60)
        self.pipe_spawn_event = Clock.schedule_interval(self.spawn_pipe, 1.5)
        
        if 'background_music' in self.sounds:
            self.sounds['background_music'].play()
    
    def restart_game(self, *args):
        self.remove_widget(self.restart_button)
        self.remove_widget(self.game_over_label)
        self.remove_widget(self.score_display_label)
        self.remove_widget(self.high_score_display_label)
        self.start_game()
    
    def spawn_pipe(self, dt):
        gap = 170 - (self.score * 1.5)
        gap = max(160, min(220, gap))
        pipe_pair = PipePair(self.width, gap, self.height)
        self.pipes.append(pipe_pair)
    
    def update_game(self, dt):
        if self.state != 'playing':
            return
        
        self.bird.update(dt)
        
        if self.bird.y < 0 or self.bird.y > self.height:
            self.game_over()
            return
        
        for pipe_pair in self.pipes[:]:
            pipe_pair.update(dt)
            
            if pipe_pair.check_collision(self.bird):
                self.game_over()
                return
            
            if not pipe_pair.scored and pipe_pair.x + pipe_pair.bottom_pipe.width < self.bird.x:
                pipe_pair.scored = True
                self.score += 1
                self.play_sound('point')
            
            if pipe_pair.is_offscreen():
                self.pipes.remove(pipe_pair)
        
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.53, 0.81, 0.92, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height))
            
            Color(0.85, 0.65, 0.13, 1)
            Rectangle(pos=(0, 0), size=(self.width, 80))
            
            for pipe_pair in self.pipes:
                if pipe_pair.bottom_pipe.texture:
                    Color(1, 1, 1, 1)
                    Rectangle(
                        pos=(pipe_pair.bottom_pipe.x, pipe_pair.bottom_pipe.y),
                        size=(pipe_pair.bottom_pipe.width, pipe_pair.bottom_pipe.height),
                        texture=pipe_pair.bottom_pipe.texture
                    )
                else:
                    Color(0.4, 0.4, 0.4, 1)
                    Rectangle(
                        pos=(pipe_pair.bottom_pipe.x, pipe_pair.bottom_pipe.y),
                        size=(pipe_pair.bottom_pipe.width, pipe_pair.bottom_pipe.height)
                    )
                
                if pipe_pair.top_pipe.texture:
                    Color(1, 1, 1, 1)
                    Rectangle(
                        pos=(pipe_pair.top_pipe.x, pipe_pair.top_pipe.y),
                        size=(pipe_pair.top_pipe.width, pipe_pair.top_pipe.height),
                        texture=pipe_pair.top_pipe.texture
                    )
                else:
                    Color(0.4, 0.4, 0.4, 1)
                    Rectangle(
                        pos=(pipe_pair.top_pipe.x, pipe_pair.top_pipe.y),
                        size=(pipe_pair.top_pipe.width, pipe_pair.top_pipe.height)
                    )
            
            PushMatrix()
            Rotate(angle=self.bird.angle, origin=(self.bird.x, self.bird.y))
            Color(1, 1, 1, 1)
            if self.bird.texture:
                Rectangle(
                    pos=(self.bird.x - self.bird.width / 2, self.bird.y - self.bird.height / 2),
                    size=(self.bird.width, self.bird.height),
                    texture=self.bird.texture
                )
            else:
                Color(1, 0.8, 0, 1)
                Rectangle(
                    pos=(self.bird.x - self.bird.width / 2, self.bird.y - self.bird.height / 2),
                    size=(self.bird.width, self.bird.height)
                )
            PopMatrix()
        
        self.score_label.text = str(self.score)
    
    def game_over(self):
        self.state = 'game_over'
        
        self.dead_bird_pos = (self.bird.x, self.bird.y, self.bird.angle)
        
        if self.score > self.high_score:
            self.high_score = self.score
        
        if self.game_loop:
            self.game_loop.cancel()
        if self.pipe_spawn_event:
            self.pipe_spawn_event.cancel()
        
        if 'background_music' in self.sounds:
            self.sounds['background_music'].stop()
        
        if self.sounds.get('deaths'):
            random.choice(self.sounds['deaths']).play()
        
        self.remove_widget(self.score_label)
        
        self.score_display_label.text = f'Score: {self.score}'
        self.high_score_display_label.text = f'High Score: {self.high_score}'
        
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
            Rectangle(pos=(0, 0), size=(self.width, 80))
            
            wavy_points = self.draw_wavy_border()
            if len(wavy_points) > 4:
                Color(0.35, 0.55, 0.62, 1)
                Line(points=wavy_points, width=2, close=True)
            
            if self.dead_bird_pos:
                PushMatrix()
                Rotate(angle=self.dead_bird_pos[2], origin=(self.dead_bird_pos[0], self.dead_bird_pos[1]))
                Color(1, 1, 1, 1)
                if self.bird and self.bird.texture:
                    Rectangle(
                        pos=(self.dead_bird_pos[0] - self.bird.width / 2, 
                             self.dead_bird_pos[1] - self.bird.height / 2),
                        size=(self.bird.width, self.bird.height),
                        texture=self.bird.texture
                    )
                else:
                    Color(1, 0.8, 0, 1)
                    Rectangle(
                        pos=(self.dead_bird_pos[0] - 25, self.dead_bird_pos[1] - 19),
                        size=(50, 38)
                    )
                PopMatrix()
    
    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        
        if self.state == 'playing':
            self.bird.jump()
            self.play_sound('flap')
            return True
        
        return False
    
    def on_key_down(self, window, key, *args):
        if self.state == 'playing' and key == 32:
            self.bird.jump()
            self.play_sound('flap')


class FlappyApp(App):
    def build(self):
        self.title = 'Flappy Veejayy'
        game = GameWidget()
        Window.bind(on_key_down=game.on_key_down)
        return game


if __name__ == '__main__':
    FlappyApp().run()
