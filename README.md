# Flappy Bird Game

A complete implementation of the classic Flappy Bird game in Python using Pygame.

## Features

- **Portrait Mode**: 480x800 pixel window for optimal gameplay
- **Sound Effects**: 
  - Flap sound when bird jumps
  - Death sound on collision
  - Point sound when passing pipes
- **Background Music**: Plays continuously during gameplay
- **Start Menu**: Welcome screen with instructions
- **Game Over Screen**: Shows score and high score
- **Restart Functionality**: Easy restart with button or spacebar
- **Keyboard & Mouse Control**: Play with spacebar or mouse clicks
- **Smooth Physics**: Gravity and jump mechanics
- **Procedural Pipe Generation**: Random pipe heights

## Installation

1. **Ensure Python 3.7+ is installed**
   ```bash
   python --version
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

Navigate to the `flappy_bird` directory and run:

```bash
python main.py
```

## Controls

- **SPACE** or **Left Mouse Click**: Make the bird flap/jump
- **ESC**: Quit the game

## How to Play

1. Click the **START** button or press SPACE to begin
2. Keep the bird in the air by clicking or pressing SPACE
3. Navigate through the gaps between pipes
4. Each pipe passed earns 1 point
5. Avoid hitting pipes or the ground
6. After game over, click **RESTART** or press SPACE to play again

## Project Structure

```
flappy_bird/
│
├── main.py                    # Main game file
├── requirements.txt           # Python dependencies
├── README.md                  # This file
│
└── assets/
    └── sfx/
        ├── flap.wav          # Jump sound effect
        ├── death.wav         # Game over sound effect
        ├── point.wav         # Score sound effect
        └── background_music.wav  # Background music
```

## Customization

You can easily customize the game by modifying constants in `main.py`:

- **Window Size**: `SCREEN_WIDTH`, `SCREEN_HEIGHT`
- **Difficulty**: `GRAVITY`, `JUMP_STRENGTH`, `PIPE_SPEED`, `PIPE_GAP`
- **Colors**: Color constants at the top of the file
- **Frame Rate**: `FPS`

## Sound Files

The included sound files are simple generated waveforms. For a better experience, you can replace them with your own:

- Replace files in `assets/sfx/` with your own `.wav` or `.mp3` files
- Keep the same filenames or update the paths in `main.py`
- Recommended: Use royalty-free sounds from:
  - [Freesound.org](https://freesound.org)
  - [Mixkit.co](https://mixkit.co/free-sound-effects/)
  - [Zapsplat.com](https://www.zapsplat.com)

## Troubleshooting

**Sound not playing?**
- Ensure sound files exist in `assets/sfx/`
- Check that pygame.mixer is properly initialized
- The game will run without sounds if they fail to load

**Game runs too fast/slow?**
- Adjust the `FPS` constant in `main.py`
- Default is 60 FPS

**Window size issues?**
- The game is designed for portrait mode (480x800)
- Modify `SCREEN_WIDTH` and `SCREEN_HEIGHT` if needed

## Requirements

- Python 3.7 or higher
- Pygame 2.5.0 or higher

## License

This is a learning project. Feel free to modify and use as you wish.

## Credits

Game concept inspired by the original Flappy Bird by Dong Nguyen.
Implementation created as an educational Python/Pygame project.
