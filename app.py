"""
Small GUI app for browsing chess opening variations from text assets.

Features:
- Loads asset text files from ./openings/*.txt
- Sidebar tree: Opening -> Variation -> Moves
- Click a move to set board to that position (plays all prior moves)
- Left / Right buttons to step one move backward/forward
- Animated moves over 500 ms duration (adjustable)
- Capture: captured piece removed during move
- Draws an arrow for last move
- Highlights checked king with a red halo
- Supports castling, promotions, en-passant via python-chess parsing

Asset format example (file contents):
** Caro-Kann Defence:
* Classical Variation:
1. e4 c6
2. d4 d5
3. Nc3 dxe4
...
----------------------
* Advance Variation:
1. e4 c6
2. d4 d5
...
----------------------
"""
import os
import glob
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import chess
import re

ASSETS_DIR = "assets"
PIECE_IMGS_DIR = "pieces"  # optional folder with piece images named: wp.png, wn.png, ... bp.png, br.png etc
ANIM_MS = 500
ANIM_FRAMES = 25

SQUARE_SIZE = 64
BOARD_PADDING = 8
LIGHT_COLOR = "#F0D9B5"
DARK_COLOR = "#B58863"

# Map python-chess piece type + color to filename codes
PIECE_CODE = {
    (chess.PAWN, True): "wp",
    (chess.KNIGHT, True): "wn",
    (chess.BISHOP, True): "wb",
    (chess.ROOK, True): "wr",
    (chess.QUEEN, True): "wq",
    (chess.KING, True): "wk",
    (chess.PAWN, False): "bp",
    (chess.KNIGHT, False): "bn",
    (chess.BISHOP, False): "bb",
    (chess.ROOK, False): "br",
    (chess.QUEEN, False): "bq",
    (chess.KING, False): "bk",
}

# --- Parsing assets ---------------------------------------------------------
def parse_assets(dir_path=ASSETS_DIR):
    """
    Returns a dict:
      { opening_name: [ { 'name': variation_name, 'moves': [san1, san2, ...], 'ucis': [uci1, ...], 'states': [fen1, fen2,...] } , ... ] , ... }
    Each variation's moves are SAN as read; ucis and states are precomputed using python-chess for quick playback.
    """
    openings = {}
    files = glob.glob(os.path.join(dir_path, "*.txt"))
    if not files:
        return openings

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            text = f.read()
        lines = text.splitlines()
        cur_opening = None
        cur_variation = None
        cur_moves_lines = []
        def flush_variation():
            nonlocal cur_variation, cur_moves_lines, cur_opening
            if cur_opening is None or cur_variation is None:
                return
            moves_text = "\n".join(cur_moves_lines).strip()
            if not moves_text:
                return
            # extract move tokens like "1. e4 c6" -> ["e4","c6", ...]
            tokens = []
            for ln in cur_moves_lines:
                # remove move numbers and comments
                ln = re.sub(r"\{\s*.*?\s*\}", "", ln)  # remove braces comments
                ln = re.sub(r"\d+\.(\.\.)?", "", ln)  # remove move numbers
                ln = ln.strip()
                if not ln:
                    continue
                parts = ln.split()
                tokens.extend(parts)
            # filter out separators like "..." or headers
            tokens = [t for t in tokens if t.strip() and t.strip() not in ("...",)]
            # Now validate & convert using python-chess to UCI and FEN list
            board = chess.Board()
            ucis = []
            fens = [board.fen()]
            valid_sans = []
            for tok in tokens:
                # token might include annotations like "e4!" or "e4?" or "e4+"
                tok_clean = re.sub(r"[!?+#]+$", "", tok)
                try:
                    move = board.parse_san(tok_clean)
                    ucis.append(move.uci())
                    board.push(move)
                    fens.append(board.fen())
                    # store original token for display (with + or # if present)
                    valid_sans.append(tok)
                except Exception as e:
                    # illegal move encountered — stop parsing that variation
                    print(f"Warning: could not parse move '{tok}' in {cur_opening} -> {cur_variation}: {e}")
                    break
            variation_obj = {
                "name": cur_variation,
                "moves_san": valid_sans,
                "moves_uci": ucis,
                "states_fen": fens  # fens[0] is starting position
            }
            openings.setdefault(cur_opening, []).append(variation_obj)
            cur_moves_lines = []

        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("**"):
                # new opening
                flush_variation()
                cur_variation = None
                cur_moves_lines = []
                cur_opening = line_stripped.lstrip("* ").strip().rstrip(":")
            elif line_stripped.startswith("*"):
                # new variation inside current opening
                flush_variation()
                cur_variation = line_stripped.lstrip("* ").strip().rstrip(":")
                cur_moves_lines = []
            elif line_stripped.startswith("-") and set(line_stripped) <= set("- "):
                # separator; finalize current variation
                flush_variation()
                cur_variation = None
                cur_moves_lines = []
            else:
                if cur_variation is not None:
                    if line.strip():
                        cur_moves_lines.append(line.rstrip())
        # flush last
        flush_variation()
    return openings

# --- GUI / Board rendering -----------------------------------------------
class PieceImages:
    def __init__(self, size):
        self.size = size
        self.cache = {}
        self.has_images = False
        self.load_images()

    def load_images(self):
        if not os.path.isdir(PIECE_IMGS_DIR):
            self.has_images = False
            return
        for code in PIECE_CODE.values():
            fname = os.path.join(PIECE_IMGS_DIR, f"{code}.png")
            if not os.path.exists(fname):
                self.has_images = False
                return
        # all present
        for code in PIECE_CODE.values():
            img = Image.open(os.path.join(PIECE_IMGS_DIR, f"{code}.png")).convert("RGBA")
            img = img.resize((self.size, self.size), Image.LANCZOS)
            self.cache[code] = ImageTk.PhotoImage(img)
        self.has_images = True

    def get(self, piece: chess.Piece):
        code = PIECE_CODE[(piece.piece_type, piece.color)]
        if self.has_images:
            return self.cache[code]
        return None

# helper to convert board index to canvas coords
def square_to_xy(square_index, square_size=SQUARE_SIZE, padding=BOARD_PADDING, flip=False):
    # square_index 0..63 (a1=0 ... h8=63) per python-chess (a1 is square 0)
    file = chess.square_file(square_index)
    rank = chess.square_rank(square_index)
    # draw such that a1 bottom-left => canvas y increases downward, we want board with white at bottom
    # we will map rank 0 (a1) to bottom row
    x = padding + file * square_size
    y = padding + (7 - rank) * square_size
    return x, y

class BoardCanvas(tk.Canvas):
    def __init__(self, master, piece_imgs: PieceImages, *args, **kwargs):
        w = SQUARE_SIZE * 8 + BOARD_PADDING * 2
        h = w
        super().__init__(master, width=w, height=h, bg="white", highlightthickness=0, *args, **kwargs)
        self.square_size = SQUARE_SIZE
        self.padding = BOARD_PADDING
        self.piece_imgs = piece_imgs
        self.images_on_board = {}  # map square_index -> canvas item id
        self.text_items = {}  # fallbacks when images not available
        self.arrow_item = None
        self.check_item = None
        self.last_move = None  # (from_sq, to_sq)
        self._draw_board_squares()
        self.current_board = chess.Board()

        # pieces initial placement
        self.reset_pieces_from_board(self.current_board)

    def _draw_board_squares(self):
        s = self.square_size
        p = self.padding
        for rank in range(8):
            for file in range(8):
                x1 = p + file * s
                y1 = p + rank * s
                x2 = x1 + s
                y2 = y1 + s
                # rank 0 is top row in canvas; but our mapping uses reversed ranks. We'll color by (file + rank)
                color = LIGHT_COLOR if ((file + rank) % 2 == 0) else DARK_COLOR
                self.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def reset_pieces_from_board(self, board: chess.Board):
        # clear existing
        for item in list(self.images_on_board.values()):
            self.delete(item)
        for t in list(self.text_items.values()):
            self.delete(t)
        self.images_on_board.clear()
        self.text_items.clear()
        self.current_board = board.copy()
        # draw pieces
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece:
                x, y = square_to_xy(sq)
                cx = x + self.square_size // 2
                cy = y + self.square_size // 2
                if self.piece_imgs.has_images:
                    img = self.piece_imgs.get(piece)
                    item = self.create_image(cx, cy, image=img)
                    self.images_on_board[sq] = item
                else:
                    # fallback: text
                    label = piece.symbol()
                    item = self.create_text(cx, cy, text=label, font=("Helvetica", int(self.square_size / 2)))
                    self.text_items[sq] = item
        # remove arrow/check
        if self.arrow_item:
            self.delete(self.arrow_item)
            self.arrow_item = None
        if self.check_item:
            self.delete(self.check_item)
            self.check_item = None

    def animate_move(self, board_before: chess.Board, uci_move: str, callback=None):
        """
        Animate a move described by its UCI string on the current canvas state (which should match board_before).
        Callback called when animation completed.
        """
        move = chess.Move.from_uci(uci_move)
        from_sq = move.from_square
        to_sq = move.to_square
        captured = board_before.piece_at(to_sq) if board_before.is_capture(move) else None
        moving_piece = board_before.piece_at(from_sq)
        if moving_piece is None:
            # nothing to animate; just set final
            new_board = board_before.copy()
            new_board.push(move)
            self.reset_pieces_from_board(new_board)
            if callback:
                callback()
            return

        # find canvas item id for from_sq
        item = self.images_on_board.get(from_sq) or self.text_items.get(from_sq)
        # if using images, create a moving copy on top
        if item is None:
            # no visible piece at from_sq; fallback to force reset
            new_board = board_before.copy()
            new_board.push(move)
            self.reset_pieces_from_board(new_board)
            if callback:
                callback()
            return

        # compute pixel coords
        fx, fy = square_to_xy(from_sq)
        tx, ty = square_to_xy(to_sq)
        fx_c = fx + self.square_size // 2
        fy_c = fy + self.square_size // 2
        tx_c = tx + self.square_size // 2
        ty_c = ty + self.square_size // 2

        # create a moving clone (image or text) on top, and remove original item later
        if from_sq in self.images_on_board:
            original_img = self.itemcget(self.images_on_board[from_sq], "image")
            # Tk image name is a string; store reference via PhotoImage object (we have cached objects)
            # create a new image item using same PhotoImage
            moving_item = self.create_image(fx_c, fy_c, image=self.piece_imgs.get(moving_piece))
        else:
            # text clone
            moving_item = self.create_text(fx_c, fy_c, text=moving_piece.symbol(), font=("Helvetica", int(self.square_size/2)))

        # remove original representation immediately so board looks cleaner while animating
        if from_sq in self.images_on_board:
            self.delete(self.images_on_board[from_sq])
            del self.images_on_board[from_sq]
        if from_sq in self.text_items:
            self.delete(self.text_items[from_sq])
            del self.text_items[from_sq]

        # If capture, schedule captured piece removal at half-way point
        captured_item_sq = None
        if captured:
            # the piece being captured is at to_sq (or en-passant square)
            if to_sq in self.images_on_board or to_sq in self.text_items:
                captured_item_sq = to_sq
            elif move.is_en_passant():
                # captured pawn is behind the to_sq
                cap_sq = chess.square(chess.square_file(to_sq), chess.square_rank(to_sq) + (1 if moving_piece.color else -1))
                if cap_sq in self.images_on_board or cap_sq in self.text_items:
                    captured_item_sq = cap_sq

        frames = ANIM_FRAMES
        delay = max(1, int(ANIM_MS / frames))
        dx = (tx_c - fx_c) / frames
        dy = (ty_c - fy_c) / frames

        def frame(i=0):
            if i >= frames:
                # done: remove moving_item, place piece on destination
                self.delete(moving_item)
                # remove captured piece if still present
                if captured_item_sq is not None:
                    if captured_item_sq in self.images_on_board:
                        self.delete(self.images_on_board[captured_item_sq])
                        del self.images_on_board[captured_item_sq]
                    if captured_item_sq in self.text_items:
                        self.delete(self.text_items[captured_item_sq])
                        del self.text_items[captured_item_sq]
                # place final piece at to_sq
                piece_after = board_before.piece_at(from_sq)  # moving_piece; but board after will be pushed externally
                px = tx + self.square_size // 2
                py = ty + self.square_size // 2
                if self.piece_imgs.has_images:
                    img = self.piece_imgs.get(moving_piece)
                    item_id = self.create_image(px, py, image=img)
                    self.images_on_board[to_sq] = item_id
                else:
                    item_id = self.create_text(px, py, text=moving_piece.symbol(), font=("Helvetica", int(self.square_size/2)))
                    self.text_items[to_sq] = item_id

                # update internal board
                # we'll not maintain board_before here — caller will set board externally after animation
                # finally draw arrow for last move
                self._draw_last_move_arrow(from_sq, to_sq)
                # highlight check if any
                # callback
                if callback:
                    callback()
                return
            else:
                self.move(moving_item, dx, dy)
                # remove captured at half-way
                if captured_item_sq is not None and i == frames // 2:
                    if captured_item_sq in self.images_on_board:
                        self.delete(self.images_on_board[captured_item_sq])
                        del self.images_on_board[captured_item_sq]
                    if captured_item_sq in self.text_items:
                        self.delete(self.text_items[captured_item_sq])
                        del self.text_items[captured_item_sq]
                self.after(delay, lambda: frame(i+1))

        frame()

    def _draw_last_move_arrow(self, from_sq, to_sq):
        # remove previous arrow
        if self.arrow_item:
            self.delete(self.arrow_item)
            self.arrow_item = None
        fx, fy = square_to_xy(from_sq)
        tx, ty = square_to_xy(to_sq)
        fx_c = fx + self.square_size // 2
        fy_c = fy + self.square_size // 2
        tx_c = tx + self.square_size // 2
        ty_c = ty + self.square_size // 2
        # simple arrow: line plus triangle
        line = self.create_line(fx_c, fy_c, tx_c, ty_c, width=4, arrow="last", arrowshape=(16,20,6), fill="#0b5fff")
        self.arrow_item = line

    def highlight_check(self, board: chess.Board):
        # remove previous
        if self.check_item:
            self.delete(self.check_item)
            self.check_item = None
        if board.is_check():
            ksq = board.king(board.turn)  # king of side to move is checked by opponent; careful: is_check returns if side to move is in check
            if ksq is not None:
                x, y = square_to_xy(ksq)
                cx = x + self.square_size // 2
                cy = y + self.square_size // 2
                r = int(self.square_size*0.48)
                self.check_item = self.create_oval(cx-r, cy-r, cx+r, cy+r, outline="red", width=4)

# --- Application -----------------------------------------------------------
class OpeningViewerApp:
    def __init__(self, master):
        self.master = master
        master.title("Chess Opening Variations")
        # load assets
        self.openings = parse_assets()
        # left: tree sidebar
        left_frame = ttk.Frame(master)
        left_frame.pack(side="left", fill="y")
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(side="top", fill="x", padx=6, pady=6)
        self.load_btn = ttk.Button(btn_frame, text="Load assets folder...", command=self.choose_assets_folder)
        self.load_btn.pack(side="left", padx=(0,6))
        self.refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self.reload_assets)
        self.refresh_btn.pack(side="left")
        # treeview
        self.tree = ttk.Treeview(left_frame)
        self.tree.pack(side="top", fill="y", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # right: board + controls
        right_frame = ttk.Frame(master)
        right_frame.pack(side="left", fill="both", expand=True)
        self.piece_imgs = PieceImages(SQUARE_SIZE)
        self.board_canvas = BoardCanvas(right_frame, self.piece_imgs)
        self.board_canvas.pack(side="top", padx=8, pady=8)

        ctrls = ttk.Frame(right_frame)
        ctrls.pack(side="top", fill="x")
        self.prev_btn = ttk.Button(ctrls, text="◀ Prev", command=self.on_prev)
        self.prev_btn.pack(side="left", padx=6)
        self.next_btn = ttk.Button(ctrls, text="Next ▶", command=self.on_next)
        self.next_btn.pack(side="left")
        self.status = ttk.Label(ctrls, text="No variation selected")
        self.status.pack(side="left", padx=12)

        # internal playback state
        self.current_opening = None
        self.current_variation_idx = None
        self.current_move_index = 0  # index into moves applied (0=starting pos)
        self.playing_animation = False

        self.populate_tree()

    def choose_assets_folder(self):
        path = filedialog.askdirectory(initialdir=".")
        if path:
            global ASSETS_DIR
            ASSETS_DIR = path
            self.reload_assets()

    def reload_assets(self):
        self.openings = parse_assets(ASSETS_DIR)
        self.populate_tree()

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for opening, variations in sorted(self.openings.items()):
            oid = self.tree.insert("", "end", text=opening, open=False)
            for vidx, var in enumerate(variations):
                vid = self.tree.insert(oid, "end", text=var["name"], open=False, values=(opening, vidx))
                # add moves as children
                for midx, san in enumerate(var["moves_san"]):
                    label = f"{midx+1}. {san}"
                    # store metadata in tags or values: store (opening, vidx, midx)
                    self.tree.insert(vid, "end", text=label, values=(opening, vidx, midx))
        # reset state
        self.current_opening = None
        self.current_variation_idx = None
        self.current_move_index = 0
        self.board_canvas.reset_pieces_from_board(chess.Board())
        self.status.config(text="Loaded {} openings".format(len(self.openings)))

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        vals = self.tree.item(item, "values")
        # item values may be empty for top-level openings
        if not vals:
            # clicked opening; just toggle
            if self.tree.item(item, "open"):
                self.tree.item(item, open=False)
            else:
                self.tree.item(item, open=True)
            return
        # values stored as (opening, vidx, [midx])
        if len(vals) == 2:
            # variation clicked
            opening, vidx = vals
            self.open_variation(opening, int(vidx))
        else:
            opening, vidx, midx = vals
            self.open_and_jump(opening, int(vidx), int(midx)+1)  # midx is 0-based; we want moves applied up to that index

    def open_variation(self, opening, vidx):
        self.current_opening = opening
        self.current_variation_idx = vidx
        self.current_move_index = 0
        self.board_canvas.reset_pieces_from_board(chess.Board())
        var = self.openings[opening][vidx]
        self.status.config(text=f"{opening} — {var['name']} (0/{len(var['moves_san'])})")

    def open_and_jump(self, opening, vidx, move_count):
        """Set variation and jump to move_count (apply that many half-moves)"""
        if opening not in self.openings:
            return
        var = self.openings[opening][vidx]
        # set state
        self.current_opening = opening
        self.current_variation_idx = vidx
        self.play_move_sequence_to(move_count)

    def play_move_sequence_to(self, target_move_count):
        """
        Animate from current_move_index to target_move_count along current variation.
        target_move_count: number of moves applied (0..len)
        """
        if self.current_opening is None or self.current_variation_idx is None:
            return
        var = self.openings[self.current_opening][self.current_variation_idx]
        max_moves = len(var["moves_uci"])
        target_move_count = max(0, min(target_move_count, max_moves))
        # we'll animate step by step
        def step_to(idx_from, idx_to):
            # if idx_from == idx_to: just done
            if idx_from == idx_to:
                self.current_move_index = idx_to
                self.status.config(text=f"{self.current_opening} — {var['name']} ({self.current_move_index}/{max_moves})")
                return
            forward = idx_to > idx_from
            if forward:
                next_index = idx_from + 1
                # animate the UCI at position next_index-1
                uci = var["moves_uci"][next_index - 1]
                board_before = chess.Board(var["states_fen"][0])
                # reconstruct board_before up to next_index-1
                for m in var["moves_uci"][: next_index - 1]:
                    board_before.push(chess.Move.from_uci(m))
                # perform animation then push final state
                def after_anim():
                    # update internal board
                    board_before.push(chess.Move.from_uci(uci))
                    # reset board canvas to match board_before (which now includes move)
                    self.board_canvas.reset_pieces_from_board(board_before)
                    self.board_canvas._draw_last_move_arrow(chess.Move.from_uci(uci).from_square, chess.Move.from_uci(uci).to_square)
                    self.board_canvas.highlight_check(board_before)
                    self.current_move_index = next_index
                    self.status.config(text=f"{self.current_opening} — {var['name']} ({self.current_move_index}/{max_moves})")
                    # recursively continue
                    step_to(next_index, idx_to)
                # animate
                self.board_canvas.animate_move(board_before, uci, callback=after_anim)
            else:
                # backward: simply re-render board at truncated fen (no animation)
                new_board = chess.Board(var["states_fen"][0])
                for m in var["moves_uci"][:idx_to]:
                    new_board.push(chess.Move.from_uci(m))
                self.board_canvas.reset_pieces_from_board(new_board)
                if idx_to > 0:
                    last_m = var["moves_uci"][idx_to-1]
                    mv = chess.Move.from_uci(last_m)
                    self.board_canvas._draw_last_move_arrow(mv.from_square, mv.to_square)
                self.board_canvas.highlight_check(new_board)
                self.current_move_index = idx_to
                self.status.config(text=f"{self.current_opening} — {var['name']} ({self.current_move_index}/{max_moves})")
                # done

        # start stepping
        step_to(self.current_move_index, target_move_count)

    def on_prev(self):
        if self.current_opening is None or self.current_variation_idx is None:
            return
        self.play_move_sequence_to(self.current_move_index - 1)

    def on_next(self):
        if self.current_opening is None or self.current_variation_idx is None:
            return
        self.play_move_sequence_to(self.current_move_index + 1)

def main():
    root = tk.Tk()
    app = OpeningViewerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
