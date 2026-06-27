import pygame
import random
import sys
import os
import math

pygame.init()

# Configurações de tela
# Grade no padrão "Regular" do Snake do Google: 17 x 15 blocos.
# A geometria é derivada da contagem de blocos para manter a área inteira
# e a grade alinhada ao grid de movimento (sem cortes nem defasagem).
TAMANHO_BLOCO = 32
ESPESSURA_BORDA = TAMANHO_BLOCO   # borda = 1 bloco (múltiplo do bloco -> alinhado)
COLUNAS = 17
LINHAS  = 15

# Área jogável (em px) — todos múltiplos de TAMANHO_BLOCO
AREA_X1 = ESPESSURA_BORDA
AREA_Y1 = ESPESSURA_BORDA
AREA_X2 = AREA_X1 + COLUNAS * TAMANHO_BLOCO
AREA_Y2 = AREA_Y1 + LINHAS  * TAMANHO_BLOCO

# Janela = área jogável + bordas dos dois lados
LARGURA = AREA_X2 + ESPESSURA_BORDA
ALTURA  = AREA_Y2 + ESPESSURA_BORDA

TELA = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Snake")

# Área jogável em unidades de bloco (limites de spawn da comida)
BLOCO_MIN_X = AREA_X1 // TAMANHO_BLOCO
BLOCO_MAX_X = (AREA_X2 // TAMANHO_BLOCO) - 1
BLOCO_MIN_Y = AREA_Y1 // TAMANHO_BLOCO
BLOCO_MAX_Y = (AREA_Y2 // TAMANHO_BLOCO) - 1

# posição inicial centralizada (snap para a grade)
INICIO_X = ((LARGURA // 2) // TAMANHO_BLOCO) * TAMANHO_BLOCO
INICIO_Y = ((ALTURA  // 2) // TAMANHO_BLOCO) * TAMANHO_BLOCO

# FPS
FPS_NORMAL = 10
AUMENTO_HARDCORE = 0.5

# Cores
PRETO = (15, 15, 15)
VERDE = (0, 220, 100)
VERDE_ESC = (0, 150, 70)
VERMELHO = (220, 50, 50)
BRANCO = (240, 240, 240)
CINZA = (100, 100, 100)
AMARELO = (255, 220, 50)
ROXO = (170, 90, 230)
GRADE_1 = (24, 26, 24)
GRADE_2 = (20, 22, 20)
GRADE_LIN = (32, 36, 32)

# Modo
MODO_ATUAL = "normal"

# Som de fundo
MODO_MUSICA_ATUAL = None

clock = pygame.time.Clock()

# Localiza arquivos (fonte/sons) tanto rodando como .py quanto empacotado em .exe.
# Quando vira .exe (PyInstaller --onefile), os arquivos embutidos são extraídos
# em tempo de execução para a pasta temporária apontada por sys._MEIPASS.
def caminho_recurso(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

# Fonte: tenta carregar custom, cai para padrão se não encontrar
CAMINHO_FONTE = caminho_recurso("PressStart2P-Regular.ttf")

def _carregar_fonte(tamanho):
    if os.path.isfile(CAMINHO_FONTE):
        return pygame.font.Font(CAMINHO_FONTE, tamanho)
    return pygame.font.SysFont("monospace", tamanho, bold=True)

fonte_titulo = _carregar_fonte(32)
fonte_media = _carregar_fonte(16)
fonte_pequena = _carregar_fonte(12)

# Áudio: carrega os efeitos de sounds/ ; se o mixer ou os arquivos falharem,
# o jogo segue normal (sem som), sem quebrar.
SONS = {}
try:
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    _pasta_sons = caminho_recurso("sounds")
    for _nome in ("highlight", "select", "apple", "game_over", "pause", "countdown"):
        _caminho = os.path.join(_pasta_sons, f"{_nome}.wav")
        if os.path.isfile(_caminho):
            SONS[_nome] = pygame.mixer.Sound(_caminho)
except pygame.error:
    SONS = {}

def tocar(nome):
    som = SONS.get(nome)
    if som is not None:
        som.play()

def parar_musica():
    pygame.mixer.music.stop()
    global MODO_MUSICA_ATUAL
    MODO_MUSICA_ATUAL = None

def tocar_musica_modo(modo):
    global MODO_MUSICA_ATUAL

    if not pygame.mixer.get_init():
        pygame.mixer.init()

    if pygame.mixer.music.get_busy() and MODO_MUSICA_ATUAL == modo:
        return

    pygame.mixer.music.stop()

    # Mesma trilha para todos os modos
    caminho = caminho_recurso("sounds/classica.mp3")

    if os.path.isfile(caminho):
        pygame.mixer.music.load(caminho)
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1)

        MODO_MUSICA_ATUAL = modo

# Helpers de desenho
def desenhar_texto_centralizado(texto, fonte, cor, y):
    render = fonte.render(texto, True, cor)
    rect = render.get_rect(center=(LARGURA // 2, y))
    TELA.blit(render, rect)
    return rect

def desenhar_texto_multicolor(texto, fonte, cores, y):
    # Desenha o texto centralizado, com cada caractere numa cor da lista
    # 'cores' (alternando). Retorna o rect da caixa total (p/ hover e seta).
    largura_total, altura = fonte.size(texto)
    x = LARGURA // 2 - largura_total // 2
    esquerda = x
    for i, ch in enumerate(texto):
        render = fonte.render(ch, True, cores[i % len(cores)])
        TELA.blit(render, (x, y - render.get_height() // 2))
        x += fonte.size(ch)[0]
    return pygame.Rect(esquerda, y - altura // 2, largura_total, altura)

def desenhar_bordas():
    pygame.draw.rect(TELA, CINZA, (0, 0, LARGURA, ALTURA), ESPESSURA_BORDA)

def desenhar_grade():
    if MODO_ATUAL == "copa":
        bloco = TAMANHO_BLOCO
        n_col = (AREA_X2 - AREA_X1) // bloco
        n_lin = (AREA_Y2 - AREA_Y1) // bloco
        cx = (AREA_X1 + AREA_X2) // 2
        cy = (AREA_Y1 + AREA_Y2) // 2

        GRAMA     = (30, 132, 40)
        GRAMA_ESC = (24, 116, 34)
        GRID_COPA = (44, 156, 54)

        # Listras de grama alternadas (cara de campo de verdade)
        for c in range(n_col):
            x = AREA_X1 + c * bloco
            cor = GRAMA if c % 2 == 0 else GRAMA_ESC
            pygame.draw.rect(TELA, cor, (x, AREA_Y1, bloco, AREA_Y2 - AREA_Y1))

        # Linhas de grid (sutis) para orientação durante o jogo
        for c in range(n_col + 1):
            x = AREA_X1 + c * bloco
            pygame.draw.line(TELA, GRID_COPA, (x, AREA_Y1), (x, AREA_Y2))
        for l in range(n_lin + 1):
            y = AREA_Y1 + l * bloco
            pygame.draw.line(TELA, GRID_COPA, (AREA_X1, y), (AREA_X2, y))

        # Marcações do campo (branco, por cima de tudo)
        pygame.draw.line(TELA, BRANCO, (cx, AREA_Y1), (cx, AREA_Y2), 3) # linha central
        pygame.draw.circle(TELA, BRANCO, (cx, cy), 60, 3)  # círculo central
        pygame.draw.circle(TELA, BRANCO, (cx, cy), 4) # ponto central

        # Áreas dos gols (esquerda e direita)
        area_h = 5 * bloco
        area_w = 2 * bloco
        pygame.draw.rect(TELA, BRANCO, (AREA_X1, cy - area_h // 2, area_w, area_h), 3)
        pygame.draw.rect(TELA, BRANCO, (AREA_X2 - area_w, cy - area_h // 2, area_w, area_h), 3)

        # Borda do campo
        pygame.draw.rect(
            TELA, BRANCO,
            (AREA_X1, AREA_Y1, AREA_X2 - AREA_X1, AREA_Y2 - AREA_Y1), 3
        )
        return

    bloco = TAMANHO_BLOCO
    n_col = (AREA_X2 - AREA_X1) // bloco
    n_lin = (AREA_Y2 - AREA_Y1) // bloco

    # Xadrez sutil
    for c in range(n_col):
        for l in range(n_lin):
            x = AREA_X1 + c * bloco
            y = AREA_Y1 + l * bloco
            cor = GRADE_1 if (c + l) % 2 == 0 else GRADE_2
            pygame.draw.rect(TELA, cor, (x, y, bloco, bloco))

    # Linhas finas da grade
    for c in range(n_col + 1):
        x = AREA_X1 + c * bloco
        pygame.draw.line(TELA, GRADE_LIN, (x, AREA_Y1), (x, AREA_Y2))

    for l in range(n_lin + 1):
        y = AREA_Y1 + l * bloco
        pygame.draw.line(TELA, GRADE_LIN, (AREA_X1, y), (AREA_X2, y))

def gerar_comida(cobra: set) -> tuple[int, int]:
    while True:
        x = random.randint(BLOCO_MIN_X + 1, BLOCO_MAX_X - 1) * TAMANHO_BLOCO
        y = random.randint(BLOCO_MIN_Y + 1, BLOCO_MAX_Y - 1) * TAMANHO_BLOCO
        if (x, y) not in cobra:
            return x, y

def _pentagono(cx, cy, raio, rot_graus):
    pts = []
    for k in range(5):
        ang = math.radians(rot_graus + k * 72)
        pts.append((cx + raio * math.cos(ang), cy + raio * math.sin(ang)))
    return pts

def desenhar_bola(cx, cy, r):
    PRETO_BOLA = (28, 28, 28)

    # Sombra sutil no chão (direto na tela, fica embaixo da bola)
    sombra = pygame.Surface((2 * r, r), pygame.SRCALPHA)
    pygame.draw.ellipse(sombra, (0, 0, 0, 70), (0, 0, 2 * r, r))
    TELA.blit(sombra, (cx - r, cy + r - r // 2))

    # Desenha a bola numa superfície própria e depois recorta num círculo,
    # garantindo que pentágonos/costuras não vazem para fora da borda.
    lado = 2 * r + 2
    bola = pygame.Surface((lado, lado), pygame.SRCALPHA)
    bcx = bcy = lado // 2

    # Corpo branco
    pygame.draw.circle(bola, (240, 240, 240), (bcx, bcy), r)

    # Pentágono central preto
    central = _pentagono(bcx, bcy, r * 0.40, -90)
    pygame.draw.polygon(bola, PRETO_BOLA, central)

    # Pentágonos parciais ao redor
    for k in range(5):
        ang = math.radians(-90 + k * 72 + 36)
        ox = bcx + (r * 0.80) * math.cos(ang)
        oy = bcy + (r * 0.80) * math.sin(ang)
        pp = _pentagono(ox, oy, r * 0.26, math.degrees(ang) + 90)
        pygame.draw.polygon(bola, PRETO_BOLA, pp)

    # Costuras: liga cada vértice do pentágono central à borda
    for vx, vy in central:
        ang = math.atan2(vy - bcy, vx - bcx)
        bx = bcx + r * math.cos(ang)
        by = bcy + r * math.sin(ang)
        pygame.draw.line(bola, PRETO_BOLA, (vx, vy), (bx, by), 1)

    # Brilho (3D)
    pygame.draw.circle(bola, (255, 255, 255), (int(bcx - r * 0.33), int(bcy - r * 0.33)), max(1, r // 5))

    # Máscara circular: zera tudo que estiver fora do círculo da bola
    mascara = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(mascara, (255, 255, 255, 255), (bcx, bcy), r)
    bola.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # Contorno desenhado por cima (borda limpa, depois do recorte)
    pygame.draw.circle(bola, PRETO_BOLA, (bcx, bcy), r, 2)

    TELA.blit(bola, (cx - bcx, cy - bcy))

def desenhar_comida(x, y):
    if MODO_ATUAL == "copa":
        b = TAMANHO_BLOCO
        desenhar_bola(x + b // 2, y + b // 2, b // 2 - 2)
        return

    # Maçã (modos normal, hardcore e twin)
    b = TAMANHO_BLOCO
    m = max(1, b // 12)

    pygame.draw.rect(
        TELA,
        VERMELHO,
        (x + m, y + 2 * m, b - 2 * m, b - 3 * m),
        border_radius=b // 3
    )

    pygame.draw.circle(
        TELA,
        (255, 150, 150),
        (x + b // 3, y + b // 3),
        max(2, b // 10)
    )

    pygame.draw.rect(
        TELA,
        (90, 60, 30),
        (x + b // 2 - 1, y + m, max(2, b // 12), b // 4)
    )

def desenhar_cobra(cobra_lista, direcao_x, direcao_y):
    # Segmentos arredondados com degradê, olhos e língua proporcionais ao bloco
    b = TAMANHO_BLOCO
    n = len(cobra_lista)

    for i in range(n - 1, -1, -1):
        seg_x, seg_y = cobra_lista[i]
        if MODO_ATUAL == "copa":
            cor = VERDE if i % 2 == 0 else AMARELO
        else:
            if i == 0:
                cor = VERDE
            else:
                t = i / max(n - 1, 1)
                cor = (
                    int(VERDE[0] + (VERDE_ESC[0] - VERDE[0]) * t),
                    int(VERDE[1] + (VERDE_ESC[1] - VERDE[1]) * t),
                    int(VERDE[2] + (VERDE_ESC[2] - VERDE[2]) * t),
                )
        inset = max(2, b // 7) if (i == n - 1 and n > 1) else max(1, b // 20)
        pygame.draw.rect(
            TELA, cor,
            (seg_x + inset, seg_y + inset, b - 2 * inset, b - 2 * inset),
            border_radius=b // 3
        )

    cab_x, cab_y = cobra_lista[0]
    cx, cy = cab_x + b // 2, cab_y + b // 2

    dx = (direcao_x > 0) - (direcao_x < 0)
    dy = (direcao_y > 0) - (direcao_y < 0)
    if dx == 0 and dy == 0:
        dx = 1

    perp_x, perp_y = -dy, dx
    desloc_frente = b // 5
    desloc_lado = b // 5
    raio_olho = max(2, b // 6)
    raio_pupila = max(1, b // 16)
    for sinal in (1, -1):
        ox = cx + dx * desloc_frente + perp_x * desloc_lado * sinal
        oy = cy + dy * desloc_frente + perp_y * desloc_lado * sinal
        pygame.draw.circle(TELA, BRANCO, (ox, oy), raio_olho)
        pygame.draw.circle(TELA, PRETO,  (ox + dx, oy + dy), raio_pupila)

    if (pygame.time.get_ticks() // 250) % 2 == 0:
        base_x = cx + dx * (b // 2)
        base_y = cy + dy * (b // 2)
        comp = b // 3
        ponta_x = base_x + dx * comp
        ponta_y = base_y + dy * comp
        garfo = max(2, b // 10)
        esp = max(2, b // 12)
        pygame.draw.line(TELA, VERMELHO, (base_x, base_y), (ponta_x, ponta_y), esp)
        pygame.draw.line(TELA, VERMELHO, (ponta_x, ponta_y),
                         (ponta_x + perp_x * garfo + dx * garfo, ponta_y + perp_y * garfo + dy * garfo), esp)
        pygame.draw.line(TELA, VERMELHO, (ponta_x, ponta_y),
                         (ponta_x - perp_x * garfo + dx * garfo, ponta_y - perp_y * garfo + dy * garfo), esp)

def processar_sair(eventos):
    for ev in eventos:
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

# Telas
def menu_inicial() -> str:
    parar_musica()
    # Navegação: setas/WASD + Enter/Espaço, ou mouse (hover + clique).
    # Cada opção tem uma descrição (2 linhas) e uma cor de destaque própria,
    # que só aparecem quando ela está destacada (por mouse ou teclado).
    # A cor "alternar" faz o rótulo alternar amarelo/verde letra a letra.
    opcoes = [
        ("NORMAL", "normal", ALTURA // 2 - 60, ("MODO ORIGINAL", "VELOCIDADE CONSTANTE"), AMARELO),
        ("HARDCORE", "hardcore", ALTURA // 2 - 10, ("VELOCIDADE AUMENTA", "A CADA FRUTA COLETADA"), VERMELHO),
        ("TWIN", "twin", ALTURA // 2 + 40, ("CABEÇA E CAUDA TROCAM", "A CADA FRUTA COLETADA"), ROXO),
        ("COPA", "copa", ALTURA // 2 + 90, ("CAMPO DE FUTEBOL", "BOLA E COBRA DO BRASIL"), "alternar"),
    ]
    selecionado = 0

    while True:
        TELA.fill(PRETO)

        desenhar_texto_centralizado("SNAKE", fonte_titulo, VERDE, ALTURA // 2 - 140)

        mouse_x, mouse_y = pygame.mouse.get_pos()

        rects = []
        for i, (rotulo, _valor, y, _desc, cor_dest) in enumerate(opcoes):
            if i == selecionado:
                if cor_dest == "alternar":
                    rect = desenhar_texto_multicolor(rotulo, fonte_media, (AMARELO, VERDE), y)
                else:
                    rect = desenhar_texto_centralizado(rotulo, fonte_media, cor_dest, y)
            else:
                rect = desenhar_texto_centralizado(rotulo, fonte_media, BRANCO, y)
            rects.append(rect)

            if rect.collidepoint(mouse_x, mouse_y) and i != selecionado:
                selecionado = i
                tocar("highlight")

            if i == selecionado:
                cor_seta = AMARELO if cor_dest == "alternar" else cor_dest
                seta = fonte_media.render(">", True, cor_seta)
                seta_rect = seta.get_rect(midright=(rect.left - 20, rect.centery))
                TELA.blit(seta, seta_rect)

        # Descrição contextual do modo destacado
        desc = opcoes[selecionado][3]
        desenhar_texto_centralizado(desc[0], fonte_pequena, CINZA, ALTURA // 2 + 150)
        desenhar_texto_centralizado(desc[1], fonte_pequena, CINZA, ALTURA // 2 + 175)

        pygame.display.update()
        clock.tick(60)

        for ev in pygame.event.get():
            processar_sair([ev])
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP, pygame.K_w):
                    selecionado = (selecionado - 1) % len(opcoes)
                    tocar("highlight")
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    selecionado = (selecionado + 1) % len(opcoes)
                    tocar("highlight")
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    tocar("select")
                    return opcoes[selecionado][1]
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, rect in enumerate(rects):
                    if rect.collidepoint(ev.pos):
                        tocar("select")
                        return opcoes[i][1]

def contagem_regressiva():
    for numero in [3, 2, 1]:
        tocar("countdown")
        inicio = pygame.time.get_ticks()
        while pygame.time.get_ticks() - inicio < 1000:
            for ev in pygame.event.get():
                processar_sair([ev])
            TELA.fill(PRETO)
            desenhar_grade()
            desenhar_bordas()
            desenhar_texto_centralizado(str(numero), fonte_titulo, BRANCO, ALTURA // 2)
            pygame.display.update()
            clock.tick(60)

def menu_pausa() -> str:
    tocar("pause")
    pygame.mixer.music.pause()   # pausa a música (mantém a posição)
    overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))

    opcoes = [
        ("CONTINUAR", "continuar", ALTURA // 2),
        ("VOLTAR AO MENU", "menu", ALTURA // 2 + 50),
    ]

    selecionado = 0

    def confirmar(valor):
        tocar("select")

        if valor == "continuar":
            contagem_regressiva()
            pygame.mixer.music.unpause() # retoma de onde parou, jogo voltando
            return "continuar"

        elif valor == "menu":
            parar_musica()
            return "menu"

    while True:
        TELA.blit(overlay, (0, 0))
        desenhar_texto_centralizado("PAUSADO", fonte_titulo, BRANCO, ALTURA // 2 - 70)

        mouse_x, mouse_y = pygame.mouse.get_pos()

        rects = []
        for i, (rotulo, _valor, y) in enumerate(opcoes):
            cor = AMARELO if i == selecionado else BRANCO
            rect = desenhar_texto_centralizado(rotulo, fonte_media, cor, y)
            rects.append(rect)

            if rect.collidepoint(mouse_x, mouse_y):
                selecionado = i

        pygame.display.update()
        clock.tick(60)

        for ev in pygame.event.get():
            processar_sair([ev])

            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP, pygame.K_w):
                    selecionado = (selecionado - 1) % len(opcoes)

                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    selecionado = (selecionado + 1) % len(opcoes)

                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return confirmar(opcoes[selecionado][1])

                elif ev.key == pygame.K_ESCAPE:
                    return confirmar("continuar")

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, rect in enumerate(rects):
                    if rect.collidepoint(ev.pos):
                        return confirmar(opcoes[i][1])

def tela_game_over(pontuacao: int, modo: str) -> str:
    global MODO_MUSICA_ATUAL
    pygame.mixer.music.stop()
    MODO_MUSICA_ATUAL = None
    tocar("game_over")
    while True:
        TELA.fill(PRETO)
        desenhar_texto_centralizado("GAME OVER", fonte_titulo, VERMELHO, ALTURA // 2 - 90)
        desenhar_texto_centralizado(f"SCORE: {pontuacao}",fonte_media, BRANCO, ALTURA // 2 - 10)
        desenhar_texto_centralizado(f"MODO: {modo.upper()}",fonte_pequena,CINZA, ALTURA // 2 + 35)
        desenhar_texto_centralizado("ENTER = REINICIAR", fonte_pequena, BRANCO, ALTURA // 2 + 90)
        desenhar_texto_centralizado("ESC = MENU", fonte_pequena, BRANCO, ALTURA // 2 + 130)
        pygame.display.update()
        for ev in pygame.event.get():
            processar_sair([ev])
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN:
                    return "reiniciar"
                if ev.key == pygame.K_ESCAPE:
                    return "menu"

# Loop principal do jogo
def jogo(modo: str) -> str:
    global MODO_ATUAL
    MODO_ATUAL = modo
    tocar_musica_modo(modo) # começa música do modo
    cobra_lista = [(INICIO_X, INICIO_Y)]
    cobra_set = set(cobra_lista)

    direcao_x = TAMANHO_BLOCO
    direcao_y = 0
    prox_dx = direcao_x
    prox_dy = direcao_y

    comida_x, comida_y = gerar_comida(cobra_set)
    pontuacao = 0
    velocidade = float(FPS_NORMAL)

    while True:
        for ev in pygame.event.get():
            processar_sair([ev])
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    resultado = menu_pausa()
                    if resultado == "menu":
                        return "menu"
                    continue
                if ev.key in (pygame.K_UP, pygame.K_w)    and direcao_y == 0:
                    prox_dx, prox_dy = 0, -TAMANHO_BLOCO
                elif ev.key in (pygame.K_DOWN, pygame.K_s)  and direcao_y == 0:
                    prox_dx, prox_dy = 0,  TAMANHO_BLOCO
                elif ev.key in (pygame.K_LEFT, pygame.K_a)  and direcao_x == 0:
                    prox_dx, prox_dy = -TAMANHO_BLOCO, 0
                elif ev.key in (pygame.K_RIGHT, pygame.K_d) and direcao_x == 0:
                    prox_dx, prox_dy =  TAMANHO_BLOCO, 0

        direcao_x, direcao_y = prox_dx, prox_dy

        cabeca_x = cobra_lista[0][0] + direcao_x
        cabeca_y = cobra_lista[0][1] + direcao_y
        nova_cabeca = (cabeca_x, cabeca_y)

        if (cabeca_x < AREA_X1 or cabeca_x + TAMANHO_BLOCO > AREA_X2
                or cabeca_y < AREA_Y1 or cabeca_y + TAMANHO_BLOCO > AREA_Y2):
            return tela_game_over(pontuacao, modo)

        if nova_cabeca in cobra_set:
            return tela_game_over(pontuacao, modo)

        cobra_lista.insert(0, nova_cabeca)
        cobra_set.add(nova_cabeca)

        if cabeca_x == comida_x and cabeca_y == comida_y:
            pontuacao += 1
            tocar("apple")
            comida_x, comida_y = gerar_comida(cobra_set)
            if modo == "hardcore":
                velocidade += AUMENTO_HARDCORE
            elif modo == "twin":
                # Cabeça e cauda trocam: inverte o corpo e passa a andar no
                # sentido em que a antiga cauda estava "apontando".
                cobra_lista.reverse()
                nx, ny = cobra_lista[0]
                px, py = cobra_lista[1]
                direcao_x = nx - px
                direcao_y = ny - py
                prox_dx, prox_dy = direcao_x, direcao_y
        else:
            removido = cobra_lista.pop()
            cobra_set.discard(removido)

        # Desenho
        TELA.fill(PRETO)
        desenhar_grade()
        desenhar_bordas()
        desenhar_comida(comida_x, comida_y)
        desenhar_cobra(cobra_lista, direcao_x, direcao_y)

        # HUD
        score_render = fonte_pequena.render(f"SCORE: {pontuacao}", True, BRANCO)
        TELA.blit(score_render, (ESPESSURA_BORDA + 4, ESPESSURA_BORDA + 4))
        if modo == "hardcore":
            vel_render = fonte_pequena.render(f"VEL: {velocidade:.1f}", True, AMARELO)
            vel_rect = vel_render.get_rect(topright=(LARGURA - ESPESSURA_BORDA - 4, ESPESSURA_BORDA + 4))
            TELA.blit(vel_render, vel_rect)

        pygame.display.update()
        clock.tick(velocidade)

def main():
    while True:
        modo = menu_inicial()
        resultado = jogo(modo)
        while resultado == "reiniciar":
            resultado = jogo(modo)

if __name__ == "__main__":
    main()