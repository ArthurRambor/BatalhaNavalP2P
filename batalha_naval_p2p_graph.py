import pygame
import threading
import socket
import random
import sys
import time

# Dimensões da grid
GRID_SIZE = 10
CELL_SIZE = 40
WIDTH = CELL_SIZE * GRID_SIZE
HEIGHT = CELL_SIZE * GRID_SIZE
FPS = 30

# Cores
BLUE = (0, 105, 148)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRAY = (169, 169, 169)
BLACK = (0, 0, 0)

class BatalhaNavalP2P:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH + 200, HEIGHT))
        pygame.display.set_caption("Batalha Naval P2P")
        self.clock = pygame.time.Clock()

        # Estado do jogo
        self.grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.shot_grid = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.scout_grid = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # Posicao do navio
        self.ship_x = random.randint(0, GRID_SIZE - 1)
        self.ship_y = random.randint(0, GRID_SIZE - 1)

        # Controle de rede
        self.running = True

        # Socket UDP
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(("", 5000))

        # Socket TCP
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(("", 5001))
        self.tcp_socket.listen(5)

        self.participants = []
        self.hits_by_player = {}
        self.times_hit = 0

        self.font = pygame.font.SysFont(None, 24)

        # Thread para escutar UDP
        self.udp_thread = threading.Thread(target=self.udp_listener, daemon=True)
        self.udp_thread.start()

        # Thread para escutar TCP
        self.tcp_thread = threading.Thread(target=self.tcp_listener, daemon=True)
        self.tcp_thread.start()

        self.message = ""  

        self.last_action_time = time.time()
        self.action_interval = 10
        self.next_action = None

    def udp_listener(self):
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                sender_ip = addr[0]
                print(f"[UDP] Recebido de {sender_ip}: {message}")
                # Pode estender para tratar mensagens aqui
            except:
                pass

    def tcp_listener(self):
        while self.running:
            try:
                conn, addr = self.tcp_socket.accept()
                data = conn.recv(1024)
                message = data.decode('utf-8')
                sender_ip = addr[0]
                print(f"[TCP] Recebido de {sender_ip}: {message}")
                conn.close()
            except:
                pass

    def draw_grid(self):
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, WHITE, rect, 1)

                if self.shot_grid[y][x]:
                    pygame.draw.circle(self.screen, RED, rect.center, CELL_SIZE // 4)
                elif self.scout_grid[y][x]:
                    pygame.draw.circle(self.screen, GREEN, rect.center, CELL_SIZE // 4)

        # Desenha navio
        ship_rect = pygame.Rect(self.ship_x * CELL_SIZE, self.ship_y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, GRAY, ship_rect)

    def draw_ui(self):
        x_offset = WIDTH + 10
        y_offset = 10

        lines = [
            "Batalha Naval P2P",
            "Comandos:",
            "Clique ESQ: Tiro  |  DIR: Scout",
            "Setas: Mover navio",
            "S: Sair"
        ]

        for i, line in enumerate(lines):
            text = self.font.render(line, True, WHITE)
            self.screen.blit(text, (x_offset, y_offset + i * 30))

        if self.message:
            msg_text = self.font.render(self.message, True, RED)
            self.screen.blit(msg_text, (x_offset, y_offset + 200))

    def shoot(self, x, y):
        self.shot_grid[y][x] = True
        self.message = f"Tiro em ({x}, {y}) enviado!"
        # Aqui enviaria o UDP broadcast para o comando shot

    def scout(self, x, y):
        self.scout_grid[y][x] = True
        self.message = f"Scout em ({x}, {y}) enviado!"
        # Aqui enviaria o comando scout TCP para IP escolhido

    def move_ship(self, dx, dy):
        new_x = max(0, min(GRID_SIZE - 1, self.ship_x + dx))
        new_y = max(0, min(GRID_SIZE - 1, self.ship_y + dy))
        self.ship_x = new_x
        self.ship_y = new_y
        self.message = f"Navio movido para ({self.ship_x}, {self.ship_y})"

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s:
                        self.running = False
                    elif event.key == pygame.K_LEFT:
                        self.move_ship(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        self.move_ship(1, 0)
                    elif event.key == pygame.K_UP:
                        self.move_ship(0, -1)
                    elif event.key == pygame.K_DOWN:
                        self.move_ship(0, 1)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x = event.pos[0] // CELL_SIZE
                    y = event.pos[1] // CELL_SIZE
                    if x < GRID_SIZE and y < GRID_SIZE:
                        if event.button == 1:   # Esquerdo - atirar
                            self.shoot(x, y)
                        elif event.button == 3: # Direito - scout
                            self.scout(x, y)

            self.screen.fill(BLUE)
            self.draw_grid()
            self.draw_ui()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit(0)

if __name__ == "__main__":
    game = BatalhaNavalP2P()
    game.run()
