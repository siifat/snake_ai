import sys
import random
from collections import deque
from typing import List, Tuple, Optional, Set, Dict
from time import perf_counter
import pygame


# Grid configuration
CELL_SIZE = 24
GRID_COLS = 24
GRID_ROWS = 20

# Window derives from grid
WINDOW_WIDTH = GRID_COLS * CELL_SIZE
WINDOW_HEIGHT = GRID_ROWS * CELL_SIZE

WINDOW_TITLE = "Snake AI — Step 11: Toggle + Metrics"

# Timing
FPS = 60
STEP_HZ = 10
STEP_DT = 1.0 / STEP_HZ

# Visuals
BG_COLOR = (30, 30, 30)
GRID_COLOR = (45, 45, 45)
SHOW_GRID = True

SNAKE_HEAD_COLOR = (60, 200, 90)
SNAKE_BODY_COLOR = (50, 160, 75)
FOOD_COLOR = (220, 85, 70)

PATH_COLOR = (80, 140, 220)  # planned BFS path outline
SHOW_PATH = True

HUD_COLOR = (235, 235, 235)
GAME_OVER_COLOR = (235, 180, 60)

# Directions as (dx, dy)
UP:    Tuple[int, int] = (0, -1)
DOWN:  Tuple[int, int] = (0,  1)
LEFT:  Tuple[int, int] = (-1, 0)
RIGHT: Tuple[int, int] = (1,  0)

# For AI helpers
Cell = Tuple[int, int]
DIRECTIONS_4: Tuple[Cell, Cell, Cell, Cell] = (UP, DOWN, LEFT, RIGHT)


# ------------
# Game GUI
# ------------
def init_pygame_window(width: int, height: int, title: str) -> pygame.Surface:
    pygame.init()
    pygame.display.set_caption(title)
    screen = pygame.display.set_mode((width, height))
    return screen

def handle_window_events(events) -> bool:
    for event in events:
        if event.type == pygame.QUIT:
            return False
    return True

def wants_restart(events) -> bool:
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            return True
    return False


def toggle_mode(events) -> bool:

    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            return True
    return False


def process_manual_input(events) -> Optional[Tuple[int, int]]:
    requested: Optional[Tuple[int, int]] = None
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                requested = UP
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                requested = DOWN
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                requested = LEFT
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                requested = RIGHT
    return requested

def cell_to_rect(cell: Cell) -> pygame.Rect:
    cx, cy = cell
    return pygame.Rect(cx * CELL_SIZE, cy * CELL_SIZE, CELL_SIZE, CELL_SIZE)

def draw_background(screen: pygame.Surface) -> None:
    screen.fill(BG_COLOR)

def draw_grid_overlay(screen: pygame.Surface) -> None:
    if not SHOW_GRID:
        return
    for c in range(1, GRID_COLS):
        x = c * CELL_SIZE
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT), 1)
    for r in range(1, GRID_ROWS):
        y = r * CELL_SIZE
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WINDOW_WIDTH, y), 1)


# -------------
# Snake model
# -------------
Snake = List[Cell]

def spawn_snake(initial_len: int = 4) -> Snake:
    cx = GRID_COLS // 2
    cy = GRID_ROWS // 2
    return [(cx - i, cy) for i in range(initial_len)]

def step_snake_move(snake: Snake, direction: Tuple[int, int], grow: bool = False) -> None:
    
    dx, dy = direction
    head_x, head_y = snake[0]
    new_head = (head_x + dx, head_y + dy)
    snake.insert(0, new_head)
    if not grow:
        snake.pop()


def draw_snake(screen: pygame.Surface, snake: Snake) -> None:
    if not snake:
        return
    pygame.draw.rect(screen, SNAKE_HEAD_COLOR, cell_to_rect(snake[0]))
    for snk in snake[1:]:
        pygame.draw.rect(screen, SNAKE_BODY_COLOR, cell_to_rect(snk))


def is_opposite(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return (a[0] == -b[0]) and (a[1] == -b[1])


def next_head_cell(snake: Snake, direction: Tuple[int, int]) -> Cell:
    
    dx, dy = direction
    hx, hy = snake[0]
    return (hx + dx, hy + dy)


def inside_board(cell: Cell) -> bool:
    x, y = cell
    return 0 <= x < GRID_COLS and 0 <= y < GRID_ROWS


# -------------
# Food system
# -------------
food_cell: Optional[Cell] = None  # current food position

def occupied_cells(snake: Snake) -> Set[Cell]:

    return set(snake)


def all_board_cells() -> List[Cell]:
    
    return [(x, y) for x in range(GRID_COLS) for y in range(GRID_ROWS)]


def empty_cells(snake: Snake) -> List[Cell]:
    
    occ = occupied_cells(snake)
    return [c for c in all_board_cells() if c not in occ]

def spawn_food(snake: Snake) -> Optional[Cell]:
    
    candidates = empty_cells(snake)
    if not candidates:
        return None
    return random.choice(candidates)


def draw_food(screen: pygame.Surface, cell: Optional[Cell]) -> None:
    if cell is None:
        return
    pygame.draw.rect(screen, FOOD_COLOR, cell_to_rect(cell))


# ----------
# State API 
# ----------
def get_head(snake: List[Cell]) -> Cell:
    
    return snake[0]

def get_body(snake: List[Cell]) -> List[Cell]:
    
    return list(snake[1:])

def get_food_cell() -> Optional[Cell]:
    
    return food_cell

def is_occupied(cell: Cell, snake: List[Cell]) -> bool:
    
    return cell in snake


def neighbors4(cell: Cell) -> List[Cell]:
    """
    Manhattan distance ব্যবহার
    """
    x, y = cell
    nbrs = [(x + dx, y + dy) for (dx, dy) in DIRECTIONS_4]
    return [c for c in nbrs if inside_board(c)]


def get_empty_cells(snake: List[Cell]) -> List[Cell]:
    return empty_cells(snake)


# ------------
# Game scores
# ------------
snake: Snake = []
direction: Tuple[int, int] = RIGHT         
pending_direction: Tuple[int, int] = RIGHT  
game_over: bool = False
score: int = 0
INITIAL_LEN: int = 4

# Mode state
MODE_AI: str = "AI"
MODE_MANUAL: str = "MANUAL"
mode: str = MODE_AI  # start in AI mode

# Path preview & BFS metrics
planned_path: List[Cell] = []
last_bfs_stats: Dict[str, float | int] = {"path_len": 0, "visited": 0, "ms": 0.0}


# -----------
# BFS চালাও!
# -----------
def bfs_path_with_stats(start: Cell, goal: Optional[Cell], snake: List[Cell]) -> Optional[List[Cell]]:
    
    global last_bfs_stats

    t0 = perf_counter()
    visited_count = 0

    if goal is None:
        last_bfs_stats = {"path_len": 0, "visited": 0, "ms": 0.0}
        return None

    blocked: Set[Cell] = set(snake)
    if snake:
        blocked.discard(snake[-1])

    q = deque([start])
    parent: dict[Cell, Optional[Cell]] = {start: None}

    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for nb in neighbors4(cur):
            if nb in blocked:
                continue
            if nb in parent: 
                continue
            parent[nb] = cur
            q.append(nb)
            visited_count += 1

    if goal not in parent:
        dt_ms = (perf_counter() - t0) * 1000.0
        last_bfs_stats = {"path_len": 0, "visited": visited_count, "ms": dt_ms}
        return None

    # Reconstruct path
    path: List[Cell] = []
    cur = goal
    while cur != start:
        path.append(cur)
        cur = parent[cur]
    path.reverse()

    dt_ms = (perf_counter() - t0) * 1000.0
    last_bfs_stats = {"path_len": len(path), "visited": visited_count, "ms": dt_ms}
    return path


# -----------------------------
# Collisions, update & render
# -----------------------------
def collides(next_head: Cell, snake: Snake, will_eat: bool) -> bool:
    
    if not inside_board(next_head):
        return True

    if next_head in snake:
        tail = snake[-1]
        if not will_eat and next_head == tail:
            return False
        return True

    return False

def direction_from_to(a: Cell, b: Cell) -> Tuple[int, int]:

    ax, ay = a
    bx, by = b
    return (bx - ax, by - ay)

def choose_safe_fallback_direction() -> Optional[Tuple[int, int]]:
    
    hx, hy = get_head(snake)
    for (dx, dy) in DIRECTIONS_4:
        nxt = (hx + dx, hy + dy)
        will_eat = (food_cell is not None) and (nxt == food_cell)
        if not collides(nxt, snake, will_eat):
            return (dx, dy)
    return None

def update_step() -> None:
    
    global snake, direction, pending_direction, food_cell, game_over, score, planned_path

    if game_over:
        return

    
    start = get_head(snake)
    goal = get_food_cell()
    planned_path = bfs_path_with_stats(start, goal, snake) or []

    
    if mode == MODE_AI:
        if planned_path:
            next_cell = planned_path[0]
            pending_direction = direction_from_to(start, next_cell)
        else:
            fallback = choose_safe_fallback_direction()
            if fallback is not None:
                pending_direction = fallback
            

    
    if not is_opposite(direction, pending_direction):
        direction = pending_direction

    # Predict & move
    nxt = next_head_cell(snake, direction)
    will_eat = (food_cell is not None) and (nxt == food_cell)

    if collides(nxt, snake, will_eat):
        game_over = True
        return

    step_snake_move(snake, direction, grow=bool(will_eat))

    if will_eat:
        score += 1
        food_cell = spawn_food(snake)
        if food_cell is None:
            game_over = True


def draw_hud(screen: pygame.Surface) -> None:
    
    font = pygame.font.SysFont(None, 24)
    mode_txt = f"Mode: {mode}"
    bfs_txt = f"Path: {last_bfs_stats['path_len']}  Visited: {last_bfs_stats['visited']}  t: {last_bfs_stats['ms']:.2f} ms"
    text = f"Score: {score}   {mode_txt}   {bfs_txt}   (M: Toggle, R: Restart)"
    surf = font.render(text, True, HUD_COLOR)
    screen.blit(surf, (8, 6))


def draw_game_over_overlay(screen: pygame.Surface) -> None:
    
    font_big = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 24)

    msg = "GAME OVER"
    instr = "R to Restart"

    surf1 = font_big.render(msg, True, GAME_OVER_COLOR)
    surf2 = font_small.render(instr, True, HUD_COLOR)

    rect1 = surf1.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 16))
    rect2 = surf2.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))

    screen.blit(surf1, rect1)
    screen.blit(surf2, rect2)


def draw_path_overlay(screen: pygame.Surface, path: List[Cell]) -> None:
    
    if not SHOW_PATH or not path:
        return
    for cell in path:
        pygame.draw.rect(screen, PATH_COLOR, cell_to_rect(cell), width=2)


def render(screen: pygame.Surface) -> None:
    draw_background(screen)
    draw_grid_overlay(screen)
    draw_food(screen, food_cell)
    draw_path_overlay(screen, planned_path)
    draw_snake(screen, snake)
    draw_hud(screen)
    if game_over:
        draw_game_over_overlay(screen)
    pygame.display.flip()


# -----------------------------
# Boot, restart, main loop
# -----------------------------
def restart_game() -> None:
    
    global snake, direction, pending_direction, food_cell, game_over, score, planned_path, last_bfs_stats

    snake = spawn_snake(initial_len=INITIAL_LEN)
    direction = RIGHT
    pending_direction = RIGHT
    food_cell = spawn_food(snake)
    game_over = False
    score = 0
    planned_path = []
    last_bfs_stats = {"path_len": 0, "visited": 0, "ms": 0.0}


def main() -> int:
    global mode, pending_direction

    screen = init_pygame_window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    clock = pygame.time.Clock()

    # Initialize all state
    restart_game()

    running = True
    accumulator = 0.0

    while running:
        # Fetch events once, share them
        events = pygame.event.get()

        # Window/OS events
        running = handle_window_events(events)

        # Restart on 'R' when game over (or anytime; harmless)
        if wants_restart(events):
            restart_game()

        # Toggle mode on 'M'
        if toggle_mode(events):
            mode = MODE_MANUAL if mode == MODE_AI else MODE_AI

        # Manual input only affects pending_direction in Manual mode
        if mode == MODE_MANUAL:
            req = process_manual_input(events)
            if req is not None:
                pending_direction = req  # applied safely at step time

        # Time & fixed-step
        dt = clock.tick(FPS) / 1000.0
        accumulator += dt

        while accumulator >= STEP_DT:
            update_step()
            accumulator -= STEP_DT

        render(screen)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
