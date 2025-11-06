import socket
import threading
import random
import time
import sys
from datetime import datetime

class BatalhaNavalP2P:
    def __init__(self):
        # Grid 10x10
        self.grid_size = 10

        # Posição aleatória do navio
        self.ship_x = random.randint(0, self.grid_size - 1)
        self.ship_y = random.randint(0, self.grid_size - 1)

        # Lista de participantes (IPs)
        self.participants = []
        self.participants_lock = threading.Lock()

        # Sockets
        self.udp_socket = None
        self.tcp_socket = None

        # Portas
        self.UDP_PORT = 5000
        self.TCP_PORT = 5001

        # Controle de jogo
        self.running = True
        self.last_action_time = time.time()
        self.action_interval = 10  # segundos
        self.next_action = None
        self.action_lock = threading.Lock()

        # Estatísticas
        self.times_hit = 0
        self.hits_by_player = {}  # {ip: número de acertos}
        self.stats_lock = threading.Lock()

        # Obter IP local
        self.my_ip = self.get_local_ip()

        print(f"[INIT] Batalha Naval P2P iniciada")
        print(f"[INIT] Meu IP: {self.my_ip}")
        print(f"[INIT] Posição do meu navio: ({self.ship_x}, {self.ship_y})")

    def get_local_ip(self):
        """Obtém o IP local da máquina"""
        try:
            # Cria um socket para descobrir o IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def udp_listener(self):
        """Thread que escuta mensagens UDP na porta 5000"""
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(('', self.UDP_PORT))

        print(f"[UDP] Escutando na porta {self.UDP_PORT}")

        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                sender_ip = addr[0]

                # Ignora mensagens de si mesmo
                if sender_ip == self.my_ip:
                    continue

                print(f"[UDP] Recebido de {sender_ip}: {message}")
                self.handle_udp_message(message, sender_ip)
            except Exception as e:
                if self.running:
                    print(f"[UDP] Erro: {e}")

    def tcp_listener(self):
        """Thread que escuta mensagens TCP na porta 5001"""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('', self.TCP_PORT))
        self.tcp_socket.listen(5)

        print(f"[TCP] Escutando na porta {self.TCP_PORT}")

        while self.running:
            try:
                conn, addr = self.tcp_socket.accept()
                threading.Thread(target=self.handle_tcp_connection, args=(conn, addr)).start()
            except Exception as e:
                if self.running:
                    print(f"[TCP] Erro: {e}")

    def handle_tcp_connection(self, conn, addr):
        """Trata uma conexão TCP"""
        try:
            data = conn.recv(1024)
            message = data.decode('utf-8')
            sender_ip = addr[0]

            print(f"[TCP] Recebido de {sender_ip}: {message}")

            response = self.handle_tcp_message(message, sender_ip)
            if response:
                conn.send(response.encode('utf-8'))
                print(f"[TCP] Enviado para {sender_ip}: {response}")
        except Exception as e:
            print(f"[TCP] Erro ao tratar conexão: {e}")
        finally:
            conn.close()

    def handle_udp_message(self, message, sender_ip):
        """Processa mensagens UDP recebidas"""
        if message == "Conectando":
            # Adiciona participante à lista
            self.add_participant(sender_ip)

            # Responde com TCP enviando lista de participantes
            self.send_participants_list(sender_ip)

        elif message.startswith("shot:"):
            # Formato: shot:x,y
            try:
                coords = message.split(":")[1]
                x, y = map(int, coords.split(","))

                # Verifica se acertou o navio
                if x == self.ship_x and y == self.ship_y:
                    print(f"[GAME] Fui atingido por {sender_ip} em ({x}, {y})!")
                    with self.stats_lock:
                        self.times_hit += 1

                    # Responde com TCP informando hit
                    self.send_tcp_message(sender_ip, "hit")
            except Exception as e:
                print(f"[UDP] Erro ao processar shot: {e}")

        elif message == "moved":
            print(f"[GAME] {sender_ip} moveu o navio")

        elif message == "saindo":
            print(f"[GAME] {sender_ip} saiu do jogo")
            self.remove_participant(sender_ip)

    def handle_tcp_message(self, message, sender_ip):
        """Processa mensagens TCP recebidas e retorna resposta"""
        if message.startswith("participantes:"):
            # Recebe lista de participantes
            try:
                participants_str = message.split(":", 1)[1].strip()
                participants_list = eval(participants_str)  # Converte string para lista

                for ip in participants_list:
                    if ip != self.my_ip:
                        self.add_participant(ip)
            except Exception as e:
                print(f"[TCP] Erro ao processar participantes: {e}")
            return None

        elif message.startswith("scout:"):
            # Formato: scout:x,y
            try:
                coords = message.split(":")[1]
                x, y = map(int, coords.split(","))

                # Verifica se acertou o navio
                if x == self.ship_x and y == self.ship_y:
                    print(f"[GAME] Fui atingido por scout de {sender_ip} em ({x}, {y})!")
                    with self.stats_lock:
                        self.times_hit += 1
                    return "hit"
                else:
                    # Retorna informação de direção
                    info_x = 1 if self.ship_x > x else -1
                    info_y = 1 if self.ship_y > y else -1
                    return f"info:{info_x},{info_y}"
            except Exception as e:
                print(f"[TCP] Erro ao processar scout: {e}")
                return None

        elif message == "hit":
            print(f"[GAME] Acertei o navio de {sender_ip}!")
            with self.stats_lock:
                if sender_ip not in self.hits_by_player:
                    self.hits_by_player[sender_ip] = 0
                self.hits_by_player[sender_ip] += 1
            return None

        elif message.startswith("info:"):
            # Formato: info:x,y
            try:
                coords = message.split(":")[1]
                info_x, info_y = map(int, coords.split(","))
                direction_x = "direita" if info_x == 1 else "esquerda"
                direction_y = "cima" if info_y == 1 else "baixo"
                print(f"[GAME] Scout info de {sender_ip}: navio está à {direction_x} e para {direction_y}")
            except Exception as e:
                print(f"[TCP] Erro ao processar info: {e}")
            return None

        return None

    def add_participant(self, ip):
        """Adiciona participante à lista"""
        with self.participants_lock:
            if ip not in self.participants and ip != self.my_ip:
                self.participants.append(ip)
                print(f"[PARTICIPANTS] Lista atualizada: {self.participants}")

    def remove_participant(self, ip):
        """Remove participante da lista"""
        with self.participants_lock:
            if ip in self.participants:
                self.participants.remove(ip)
                print(f"[PARTICIPANTS] Lista atualizada: {self.participants}")

    def send_participants_list(self, target_ip):
        """Envia lista de participantes via TCP"""
        with self.participants_lock:
            participants_msg = f"participantes: {self.participants}"
        self.send_tcp_message(target_ip, participants_msg)

    def send_tcp_message(self, target_ip, message):
        """Envia mensagem TCP para um IP específico"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((target_ip, self.TCP_PORT))
            sock.send(message.encode('utf-8'))

            # Aguarda resposta se necessário
            sock.settimeout(2)
            try:
                response = sock.recv(1024).decode('utf-8')
                if response:
                    print(f"[TCP] Resposta de {target_ip}: {response}")
                    self.handle_tcp_message(response, target_ip)
            except socket.timeout:
                pass

            sock.close()
        except Exception as e:
            print(f"[TCP] Erro ao enviar para {target_ip}: {e}")

    def send_udp_broadcast(self, message):
        """Envia mensagem UDP em broadcast"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(message.encode('utf-8'), ('<broadcast>', self.UDP_PORT))
            sock.close()
            print(f"[UDP] Broadcast enviado: {message}")
        except Exception as e:
            print(f"[UDP] Erro ao enviar broadcast: {e}")

    def send_udp_to_participants(self, message):
        """Envia mensagem UDP para todos os participantes"""
        with self.participants_lock:
            participants_copy = self.participants.copy()

        for ip in participants_copy:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(message.encode('utf-8'), (ip, self.UDP_PORT))
                sock.close()
                print(f"[UDP] Enviado para {ip}: {message}")
            except Exception as e:
                print(f"[UDP] Erro ao enviar para {ip}: {e}")

    def action_handler(self):
        """Thread que gerencia o envio de ações com intervalo de 10 segundos"""
        while self.running:
            time.sleep(1)

            with self.action_lock:
                if self.next_action and time.time() - self.last_action_time >= self.action_interval:
                    self.execute_action(self.next_action)
                    self.next_action = None
                    self.last_action_time = time.time()

    def execute_action(self, action):
        """Executa a ação solicitada"""
        parts = action.split()

        if action.startswith("shot:"):
            # Formato: shot:x y
            try:
                coords = parts[0].split(":")[1]
                x, y = int(coords), int(parts[1])
                message = f"shot:{x},{y}"
                self.send_udp_to_participants(message)
            except Exception as e:
                print(f"[ACTION] Erro ao executar shot: {e}")

        elif action.startswith("scout:"):
            # Formato: scout:x y IP
            try:
                coords = parts[0].split(":")[1]
                x, y = int(coords), int(parts[1])
                target_ip = parts[2]
                message = f"scout:{x},{y}"
                self.send_tcp_message(target_ip, message)
            except Exception as e:
                print(f"[ACTION] Erro ao executar scout: {e}")

        elif action.startswith("move"):
            # Formato: move +/- X/Y
            try:
                direction = parts[1]  # + ou -
                axis = parts[2]  # X ou Y

                if axis.upper() == "X":
                    if direction == "+":
                        self.ship_x = min(self.ship_x + 1, self.grid_size - 1)
                    else:
                        self.ship_x = max(self.ship_x - 1, 0)
                else:  # Y
                    if direction == "+":
                        self.ship_y = min(self.ship_y + 1, self.grid_size - 1)
                    else:
                        self.ship_y = max(self.ship_y - 1, 0)

                print(f"[GAME] Nova posição do navio: ({self.ship_x}, {self.ship_y})")
                self.send_udp_to_participants("moved")

                # Adiciona mais 10 segundos ao timer
                self.action_interval = 20
            except Exception as e:
                print(f"[ACTION] Erro ao executar movimento: {e}")

    def start(self):
        """Inicia o jogo"""
        # Inicia threads de escuta
        udp_thread = threading.Thread(target=self.udp_listener, daemon=True)
        tcp_thread = threading.Thread(target=self.tcp_listener, daemon=True)
        action_thread = threading.Thread(target=self.action_handler, daemon=True)

        udp_thread.start()
        tcp_thread.start()
        action_thread.start()

        # Aguarda threads iniciarem
        time.sleep(1)

        # Envia broadcast de conexão
        self.send_udp_broadcast("Conectando")

        # Interface de usuário
        self.user_interface()

    def user_interface(self):
        """Interface de texto para o usuário"""
        print("\n" + "="*60)
        print("BATALHA NAVAL P2P - COMANDOS:")
        print("="*60)
        print("1. shot:X Y       - Atira na posição (X,Y) de todos")
        print("2. scout:X Y IP   - Scout na posição (X,Y) de um IP específico")
        print("3. move +/- X/Y   - Move o navio (+1/-1 em X ou Y)")
        print("4. sair           - Sai do jogo")
        print("="*60)
        print()

        while self.running:
            try:
                command = input("Digite o comando: ").strip()

                if command == "sair":
                    self.quit_game()
                    break

                elif command.startswith("shot:") or command.startswith("scout:") or command.startswith("move"):
                    with self.action_lock:
                        time_remaining = self.action_interval - (time.time() - self.last_action_time)
                        if time_remaining > 0:
                            print(f"[INFO] Aguarde {time_remaining:.1f} segundos antes da próxima ação")
                        self.next_action = command
                        print(f"[INFO] Ação '{command}' agendada")
                        # Reseta intervalo se foi movimento
                        if command.startswith("move"):
                            self.action_interval = 10

                else:
                    print("[INFO] Comando inválido")

            except KeyboardInterrupt:
                self.quit_game()
                break
            except Exception as e:
                print(f"[ERROR] {e}")

    def quit_game(self):
        """Sai do jogo"""
        print("\n[GAME] Saindo do jogo...")

        # Envia mensagem de saída
        self.send_udp_to_participants("saindo")

        # Calcula e exibe score
        with self.stats_lock:
            total_hits = sum(self.hits_by_player.values())
            unique_players_hit = len(self.hits_by_player)
            score = unique_players_hit - self.times_hit

            print("\n" + "="*60)
            print("SCORE FINAL")
            print("="*60)
            print(f"Vezes que fui atingido: {self.times_hit}")
            print(f"Total de acertos: {total_hits}")
            print(f"Jogadores diferentes atingidos: {unique_players_hit}")
            print(f"\nDetalhes de acertos por jogador:")
            for ip, hits in self.hits_by_player.items():
                print(f"  - {ip}: {hits} acerto(s)")
            print(f"\nSCORE FINAL: {score}")
            print("="*60)

        # Para o jogo
        self.running = False

        # Fecha sockets
        try:
            if self.udp_socket:
                self.udp_socket.close()
            if self.tcp_socket:
                self.tcp_socket.close()
        except:
            pass

        sys.exit(0)

def hello_world():
    print("Hello World")

if __name__ == "__main__":
    game = BatalhaNavalP2P()
    game.start()
