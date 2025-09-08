# Chess Variations Explorer

A GUI application for browsing and studying chess opening variations with an interactive chess board. Load opening databases from text files and explore variations with visual feedback and move-by-move navigation.

## Features

- **Interactive Chess Board**: Visual 8x8 chess board with piece images
- **Opening Database**: Browse extensive collection of chess openings and variations
- **Tree Navigation**: Hierarchical sidebar showing Opening → Variation → Moves
- **Move Playback**: Click any move to jump to that position instantly
- **Step Navigation**: Navigate forward/backward through moves with arrow buttons
- **Animated Moves**: Smooth 500ms animations for piece movements
- **Visual Feedback**: 
  - Arrow indicators for the last move played
  - Red halo highlighting when king is in check
  - Proper handling of captures, castling, en passant, and promotions
- **Comprehensive Opening Library**: 70+ opening files covering major chess openings

## UI

The application features a clean interface with:
- Left sidebar for opening/variation selection
- Central chess board with piece graphics
- Navigation controls for move stepping
- Real-time position updates

## Installation

### Prerequisites

- Python 3.7+
- Required Python packages:

```bash
pip install tkinter pillow python-chess
```

### Setup

1. Clone or download this repository
2. Ensure the following directory structure:
   ```
   project/
   ├── app.py
   ├── openings/          # Opening text files
   │   ├── Caro-Kann Defense.txt
   │   ├── Sicilian Defense.txt
   │   └── ... (70+ opening files)
   └── pieces/            # Chess piece images
       ├── wp.png, wn.png, wb.png, wr.png, wq.png, wk.png
       └── bp.png, bn.png, bb.png, br.png, bq.png, bk.png
   ```

3. Run the application:
   ```bash
   cd project
   python app.py
   ```

## Usage

### Basic Navigation

1. **Select Opening**: Click on an opening name in the left sidebar
2. **Choose Variation**: Expand the opening to see available variations
3. **Play Moves**: Click on individual moves to jump to that position
4. **Step Through**: Use Left/Right arrow buttons to move one step at a time

### Understanding the Interface

- **Sidebar Tree**: Hierarchical view of openings, variations, and moves
- **Chess Board**: Interactive board showing current position
- **Move Indicators**: Last move highlighted with an arrow
- **Check Detection**: King highlighted in red when in check

### Opening File Format

The application reads opening files from the `openings/` directory. Each file follows this format:

```
** Opening Name:
* Variation Name:
1. e4 c6
2. d4 d5
3. Nc3 dxe4
----------------------------
* Another Variation:
1. e4 c6
2. d4 d5
3. e5 Bf5
----------------------------
```

- `**` denotes a main opening
- `*` denotes a variation within that opening  
- `---` separates different variations
- Standard algebraic notation (SAN) for moves

## Included Openings

The application comes with 70+ opening files covering:

- **Popular Openings**: Sicilian Defense, French Defense, Caro-Kann Defense
- **Classical Systems**: Ruy Lopez, Italian Game, Queen's Gambit
- **Modern Defenses**: King's Indian, Nimzo-Indian, Grünfeld Defense
- **Gambit Systems**: King's Gambit, Danish Gambit, Blackmar-Diemer Gambit
- **Flank Openings**: English Opening, Réti Opening, Bird Opening
- **Irregular Openings**: Grob Opening, Polish Opening, and many more

## Technical Details

### Dependencies

- **tkinter**: GUI framework (usually included with Python)
- **PIL (Pillow)**: Image processing for piece graphics
- **python-chess**: Chess logic, move validation, and position handling

### Key Components

- **Asset Parser**: Reads and validates opening files, converts to internal format
- **Board Renderer**: Draws chess board and pieces with proper coordinates
- **Move Engine**: Handles move validation, animation, and position updates
- **GUI Controller**: Manages user interaction and interface updates

### Customization

- **Animation Speed**: Modify `ANIM_MS` constant (default: 500ms)
- **Board Colors**: Adjust `LIGHT_COLOR` and `DARK_COLOR` constants
- **Piece Images**: Replace PNG files in `pieces/` directory
- **Board Size**: Change `SQUARE_SIZE` constant (default: 64px)

## Adding New Openings

To add new opening variations:

1. Create a new `.txt` file in the `openings/` directory
2. Follow the format shown above
3. Use standard algebraic notation for moves
4. Press the `Refresh` button (or just restart the application) to load new files

## Troubleshooting

### Common Contribution Issues

- **Missing piece images**: Ensure all 12 piece PNG files are in `pieces/` directory
- **Opening files not loading**: Check file format and ensure proper encoding (UTF-8)
- **Move parsing errors**: Verify moves use standard algebraic notation
- **ImportError**: cannot import name 'ImageTk' from 'PIL' => run this:

```bash
   sudo apt-get install python3-pil.imagetk
   ```


### Performance Notes

- Large opening files are parsed on startup
- Move validation uses python-chess engine for accuracy
- Animations can be disabled by setting `ANIM_MS = 0`

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions welcome! Areas for improvement:
- Additional opening databases
- Enhanced UI features
- Performance optimizations
- Mobile/web versions