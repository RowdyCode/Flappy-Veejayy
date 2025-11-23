"""
Flappy Bird Game with custom graphics support (single top and bottom pipes)
- Random start sounds
- Random death sounds
- Dynamic gaps that shrink with score + random variance
"""

import pygame
import random
import sys
import os

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants - Portrait Mode (480x800)
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235)
GROUND_COLOR = (222, 216, 149)
BUTTON_COLOR = (100, 200, 100)
BUTTON_HOVER = (120, 220, 120)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Game variables
GRAVITY = 0.5
JUMP_STRENGTH = -9
PIPE_SPEED = 3

# Base gap parameters (dynamic gap uses these)
BASE_PIPE_GAP = 170
MIN_PIPE_GAP = 160
MAX_PIPE_GAP = 220
GAP_SHRINK_PER_SCORE = 1.5
GAP_RANDOM_VARIANCE = 18
PIPE_FREQUENCY = 1500

# Bird size fallback
BIRD_WIDTH = 40
BIRD_HEIGHT = 30

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SFX_PATH = os.path.join(BASE_DIR, "assets", "sfx")
GRAPHICS_PATH = os.path.join(BASE_DIR, "assets", "graphics")


class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        bird_image_path = os.path.join(GRAPHICS_PATH, "bird.png")

        if os.path.isfile(bird_image_path):
            self.original_image = pygame.image.load(bird_image_path).convert_alpha()
            self.image = self.original_image
            self.rect = self.image.get_rect(center=(x, y))
        else:
            self.image = pygame.Surface((BIRD_WIDTH, BIRD_HEIGHT), pygame.SRCALPHA)
            self.draw_bird()
            self.original_image = self.image
            self.rect = self.image.get_rect(center=(x, y))

        self.velocity = 0
        self.angle = 0

    def draw_bird(self):
        pygame.draw.circle(self.image, YELLOW, (20, 15), 15)
        pygame.draw.ellipse(self.image, (255, 140, 0), (10, 12, 15, 8))
        pygame.draw.circle(self.image, BLACK, (25, 12), 3)
        pygame.draw.circle(self.image, WHITE, (26, 11), 2)
        pygame.draw.polygon(self.image, (255, 100, 0), [(30, 15), (40, 15), (35, 18)])

    def update(self):
        self.velocity += GRAVITY
        self.rect.y += int(self.velocity)
        self.angle = max(-30, min(30, -self.velocity * 3))

    def jump(self):
        self.velocity = JUMP_STRENGTH

    def get_rotated_image(self):
        return pygame.transform.rotate(self.original_image, self.angle)


class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, height, is_top):
        super().__init__()
        self.is_top = is_top
        self.width = 80
        self.height = max(1, int(height))

        img_name = "pipe_bottom.png"
        pipe_img_path = os.path.join(GRAPHICS_PATH, img_name)

        if os.path.isfile(pipe_img_path):
            img = pygame.image.load(pipe_img_path).convert_alpha()
            img = pygame.transform.scale(img, (self.width, self.height))
            if is_top:
                img = pygame.transform.flip(img, False, True)
            self.image = img
        else:
            self.image = pygame.Surface((self.width, self.height))
            color = (94, 201, 82)
            border_color = (70, 150, 60)
            self.image.fill(color)
            pygame.draw.rect(self.image, border_color, (0, 0, self.width, self.height), 3)

        if is_top:
            self.rect = self.image.get_rect(topleft=(x, 0))
        else:
            self.rect = self.image.get_rect(topleft=(x, SCREEN_HEIGHT - self.height))

    def update(self):
        self.rect.x -= PIPE_SPEED
        if self.rect.right < 0:
            self.kill()


class PipePair:
    def __init__(self, x, current_score):
        gap = BASE_PIPE_GAP - (current_score * GAP_SHRINK_PER_SCORE)
        gap += random.randint(-GAP_RANDOM_VARIANCE, GAP_RANDOM_VARIANCE)
        gap = max(MIN_PIPE_GAP, min(MAX_PIPE_GAP, gap))
        self.gap = int(gap)

        top_margin = 40
        bottom_margin = 50
        max_top_height = SCREEN_HEIGHT - bottom_margin - self.gap - top_margin

        top_height = (
            top_margin
            if max_top_height < top_margin
            else random.randint(top_margin, max_top_height)
        )

        top_height = max(1, int(top_height))
        bottom_height = SCREEN_HEIGHT - top_height - self.gap

        self.top_pipe = Pipe(x, top_height, True)
        self.bottom_pipe = Pipe(x, bottom_height, False)

        self.scored = False

    def update(self):
        self.top_pipe.update()
        self.bottom_pipe.update()

    def draw(self, screen):
        screen.blit(self.top_pipe.image, self.top_pipe.rect)
        screen.blit(self.bottom_pipe.image, self.bottom_pipe.rect)

    def collides_with(self, bird):
        return (
            self.top_pipe.rect.colliderect(bird.rect)
            or self.bottom_pipe.rect.colliderect(bird.rect)
        )

    def is_offscreen(self):
        return self.top_pipe.rect.right < 0


class Button:
    def __init__(self, x, y, width, height, text, font_size=36):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.Font(None, font_size)
        self.is_hovered = False

    def draw(self, screen):
        color = BUTTON_HOVER if self.is_hovered else BUTTON_COLOR
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, self.rect, 3, border_radius=10)

        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Flappy Veejayy")
        self.clock = pygame.time.Clock()

        self.flap_sound = None
        self.point_sound = None
        self.death_sounds = []
        self.start_sounds = []

        self.load_sounds()

        # Play a random start sound at game launch
        self.play_random_start_sound()

        self.state = "menu"
        self.score = 0
        self.high_score = 0

        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)

        self.start_button = Button(SCREEN_WIDTH // 2 - 100, 400, 200, 60, "START")
        self.restart_button = Button(SCREEN_WIDTH // 2 - 100, 500, 200, 60, "RESTART")

        self.bird = None
        self.pipes = []
        self.last_pipe_time = 0

    def load_sounds(self):
        # Basic sounds
        try:
            self.flap_sound = pygame.mixer.Sound(os.path.join(SFX_PATH, "flap.wav"))
            self.flap_sound.set_volume(0.5)   
        except:
            self.flap_sound = None

        try:
            self.point_sound = pygame.mixer.Sound(os.path.join(SFX_PATH, "point.wav"))
            self.point_sound.set_volume(0.3)
        except:
            self.point_sound = None


        # Background music
        try:
            pygame.mixer.music.load(os.path.join(SFX_PATH, "background_music.wav"))
            pygame.mixer.music.set_volume(0.4)
        except:
            pass

        # === RANDOM DEATH SOUNDS ===
        death_folder = os.path.join(SFX_PATH, "deaths")
        if os.path.isdir(death_folder):
            for file in os.listdir(death_folder):
                if file.lower().endswith((".wav", ".ogg", ".mp3")):
                    try:
                        snd = pygame.mixer.Sound(os.path.join(death_folder, file))
                        snd.set_volume(0.9)
                        self.death_sounds.append(snd)
                    except:
                        pass

        # === RANDOM START SOUNDS ===
        start_folder = os.path.join(SFX_PATH, "starts")
        if os.path.isdir(start_folder):
            for file in os.listdir(start_folder):
                if file.lower().endswith((".wav", ".ogg", ".mp3")):
                    try:
                        snd = pygame.mixer.Sound(os.path.join(start_folder, file))
                        snd.set_volume(0.9)
                        self.start_sounds.append(snd)
                    except:
                        pass

        print(f"Loaded {len(self.death_sounds)} death sounds.")
        print(f"Loaded {len(self.start_sounds)} start sounds.")

    # PLAY RANDOM START SOUND
    def play_random_start_sound(self):
        if self.start_sounds:
            try:
                random.choice(self.start_sounds).play()
            except:
                pass

    # PLAY RANDOM DEATH SOUND
    def play_random_death_sound(self):
        if self.death_sounds:
            try:
                random.choice(self.death_sounds).play()
            except:
                pass

    def play_sound(self, sound):
        if sound:
            try:
                sound.play()
            except:
                pass

    def reset_game(self):
        self.bird = Bird(SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2)
        self.pipes = []
        self.score = 0
        self.last_pipe_time = pygame.time.get_ticks() - 500

    def start_music(self):
        try:
            pygame.mixer.music.play(-1)
        except:
            pass

    def stop_music(self):
        try:
            pygame.mixer.music.stop()
        except:
            pass

    def draw_menu(self):
        self.screen.fill(SKY_BLUE)
        title = self.font_large.render("FLAPPY Veejayy", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 200))

        shadow = self.font_large.render("FLAPPY Veejayy", True, (50, 50, 50))
        shadow_rect = shadow.get_rect(center=(SCREEN_WIDTH // 2 + 3, 203))

        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(title, title_rect)

        inst1 = self.font_small.render("Press SPACE or Click to Flap", True, BLACK)
        inst1_rect = inst1.get_rect(center=(SCREEN_WIDTH // 2, 300))
        self.screen.blit(inst1, inst1_rect)

        if self.high_score > 0:
            hs_text = self.font_medium.render(f"High Score: {self.high_score}", True, BLACK)
            hs_rect = hs_text.get_rect(center=(SCREEN_WIDTH // 2, 350))
            self.screen.blit(hs_text, hs_rect)

        self.start_button.draw(self.screen)

    def draw_game(self):
        self.screen.fill(SKY_BLUE)

        # Ground
        ground_rect = pygame.Rect(0, SCREEN_HEIGHT - 50, SCREEN_WIDTH, 50)
        pygame.draw.rect(self.screen, GROUND_COLOR, ground_rect)

        # Pipes
        for pipe_pair in self.pipes:
            pipe_pair.draw(self.screen)

        # Bird
        rotated_bird = self.bird.get_rotated_image()
        bird_rect = rotated_bird.get_rect(center=self.bird.rect.center)
        self.screen.blit(rotated_bird, bird_rect)

        score_text = self.font_large.render(str(self.score), True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 80))

        # Outline
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            outline = self.font_large.render(str(self.score), True, BLACK)
            outline_rect = score_rect.copy()
            outline_rect.x += ox
            outline_rect.y += oy
            self.screen.blit(outline, outline_rect)

        self.screen.blit(score_text, score_rect)

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        game_over_text = self.font_large.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(game_over_text, game_over_rect)

        score_text = self.font_medium.render(f"Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 300))
        self.screen.blit(score_text, score_rect)

        hs_text = self.font_small.render(f"High Score: {self.high_score}", True, WHITE)
        hs_rect = hs_text.get_rect(center=(SCREEN_WIDTH // 2, 360))
        self.screen.blit(hs_text, hs_rect)

        self.restart_button.draw(self.screen)

    # -- EVENTS --
    def handle_menu_events(self, event):
        if self.start_button.handle_event(event):
            self.state = "playing"
            self.reset_game()
            self.start_music()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.state = "playing"
            self.reset_game()
            self.start_music()

    def handle_playing_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.bird.jump()
            self.play_sound(self.flap_sound)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.bird.jump()
            self.play_sound(self.flap_sound)

    def handle_game_over_events(self, event):
        if self.restart_button.handle_event(event):
            self.state = "playing"
            self.reset_game()
            self.start_music()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.state = "playing"
            self.reset_game()
            self.start_music()

    # -- MAIN GAME LOGIC --
    def update_playing(self):
        self.bird.update()

        current_time = pygame.time.get_ticks()
        if current_time - self.last_pipe_time > PIPE_FREQUENCY:
            self.pipes.append(PipePair(SCREEN_WIDTH, self.score))
            self.last_pipe_time = current_time

        for pipe_pair in self.pipes[:]:
            pipe_pair.update()

            if not pipe_pair.scored and pipe_pair.top_pipe.rect.right < self.bird.rect.left:
                pipe_pair.scored = True
                self.score += 1
                self.play_sound(self.point_sound)

            if pipe_pair.collides_with(self.bird):
                self.game_over()
                return

            if pipe_pair.is_offscreen():
                self.pipes.remove(pipe_pair)

        if self.bird.rect.bottom >= SCREEN_HEIGHT - 50:
            self.game_over()

        if self.bird.rect.top <= 0:
            self.bird.rect.top = 0
            self.bird.velocity = 0

    def game_over(self):
        self.state = "game_over"
        self.play_random_death_sound()
        self.stop_music()

        if self.score > self.high_score:
            self.high_score = self.score

    def run(self):
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

                if self.state == "menu":
                    self.handle_menu_events(event)
                elif self.state == "playing":
                    self.handle_playing_events(event)
                elif self.state == "game_over":
                    self.handle_game_over_events(event)

            if self.state == "playing":
                self.update_playing()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "playing":
                self.draw_game()
            elif self.state == "game_over":
                self.draw_game()
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
