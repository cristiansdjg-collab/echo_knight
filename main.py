#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECHO KNIGHT  -  Caballero del Eco   (version 11.2 - pantalla adaptable + tactil)
=============================================================
Un juego de plataformas medieval en 2D con pixel art, totalmente a oscuras.
Solo ves lo que tus ecos iluminan: cada paso, cada golpe de espada y cada
grito de eco lanzan ondas circulares de luz que chocan con los muros
(luces y sombras con raycasting).

Cada nivel es una ARENA de combate: suelo principal + plataformas flotantes.
Derrota a TODOS los monstruos (fantasmas terrestres y murcielagos voladores);
entonces aparece la LLAVE dorada. Tomala y cruza la PUERTA de salida.

Novedades de la version 4:
  * Animaciones mas fluidas (caminar, saltar, caer) para el caballero y los enemigos.
  * El caballero nunca se pierde en la oscuridad (brillo propio + silueta).
  * Paredes mas suaves: se difuminan hacia el borde del mapa.
  * Reiniciar el nivel ahora es P (pidiendo confirmacion). Pausa = ESC.
  * Haz de luz frontal: ves hacia donde miras, mas al correr.
  * Arenas mas grandes y enemigos que tardan en despertar al aparecer.
  * Salto diagonal con impulso y tajo aereo diagonal con rebote.
  * Mecanicas nuevas: corrientes de aire ascendentes y puentes fantasma
    que se solidifican con el Super Eco (Q).

Novedades de la version 10.2:
  * ANAKIN: caballero de tunica negra, sable AZUL fosforescente, estela y FUERZA azules.
  * DARTH VADER (nuevo, escribe  darth vader  durante la partida): sprites copiados tal cual
    de la imagen, sable / estela / FUERZA rojos y la misma animacion de capa y dash.

Requisitos:   pip install pygame
Ejecutar:     python echo_knight7.py          (--sin-sonido para silenciar)
"""
import array
import math
import os
import random
import sys

import pygame

# ----------------------------------------------------------------------------
#  CONFIGURACION
# ----------------------------------------------------------------------------
TILE = 16                       # tile logico 16x16
COLS, ROWS = 24, 13             # arenas ampliadas (antes 20 x 11)
DX, DY = (COLS - 20) // 2, ROWS - 11     # desplazamiento de los disenos originales 20x11
HUD_H = 16
MAP_W, MAP_H = COLS * TILE, ROWS * TILE      # 384 x 208
LW, LH = MAP_W, MAP_H + HUD_H                # 384 x 224 (resolucion logica)
FPS = 60
AMBIENT = (0, 0, 0)             # oscuridad total
PLAYER_GLOW = 0.30              # brillo minimo alrededor del caballero (0 = nada)
GLOW_R = 20                     # radio de ese brillo
BEAM_W, BEAM_H = 76, 48         # haz de luz frontal
GRACE_T = 2.5                   # segundos que los monstruos tardan en despertar
DIAG_BOOST = 1.3                # impulso horizontal del salto diagonal

# fisica
GRAVITY = 720.0
MAX_FALL = 330.0
JUMP_V = 255.0                  # ~45 px de altura maxima (plataformas a 32 px)
WALK_SPEED = 68.0
SNEAK_SPEED = 34.0
SHIELD_MULT = 0.45
GHOUL_CHASE = 46.0
GHOUL_WANDER = 22.0
GHOUL_JUMP = 250.0
BAT_CHASE = 46.0
BAT_IDLE = 16.0

STEP_DIST = 15.0                # distancia entre ecos de pasos
MAX_HP = 3
ATTACK_RANGE = 27.0
PULSE_COOLDOWN = 3.2
ATTACK_COOLDOWN = 0.45
BOW_COOLDOWN = 0.55
ARROW_SPEED = 240.0
ARROW_GRAV = 55.0
DASH_SPEED = 330.0              # dash secreto (modo TUN)
DASH_TIME = 0.19
DASH_COOLDOWN = 0.55
WINDUP_T = 0.07                 # anticipacion del tajo (retroceso de la espada)
LAND_T = 0.16                   # duracion de la compresion al aterrizar
SUPER_CHARGE_T = 2 * BOW_COOLDOWN   # tiempo de carga del super disparo (doble que un disparo normal)
SUPER_SPEED = 520.0             # el super disparo cruza el mapa casi en linea recta

GOLD = (246, 206, 72)
PARCH = (232, 220, 190)
RED = (220, 70, 70)
CYAN = (150, 225, 255)

TUT_MSGS = [
    "TUTORIAL 1/7 · Todo está a oscuras. Muévete con A / D (o FLECHAS): cada paso lanza un eco de luz.",
    "2/7 · Salta con W, Z o FLECHA arriba. Mantén pulsado para saltar más alto. Salta moviéndote para un SALTO DIAGONAL con impulso.",
    "3/7 · Sigilo: mantén SHIFT mientras caminas. No haces eco de pasos y los monstruos te oyen menos.",
    "4/7 · Ataca con ESPACIO (o X): la espada lanza una onda ámbar, pero el ruido atrae monstruos.",
    "5/7 · SÚPER ECO: pulsa Q. Ilumina toda la sala y rebota en los muros. ¡Pero atrae monstruos!",
    "6/7 · ¡Un fantasma de práctica! Derrótalo (2 golpes). OJO: los monstruos son INVISIBLES en la oscuridad; solo los verás cerca de tu luz o con un halo cuando te ataquen. Cuando no quede ninguno aparece la llave.",
    "7/7 · ¡Ha aparecido la llave dorada! Búscala con tus ecos y tómala: las antorchas se encenderán.",
    "¡Listo! La sala se ilumina y la puerta está abierta. Más adelante hallarás un escudo (S) y un arco (F) en cofres. ¡Corre a la PUERTA!",
]

# Tipos de onda: color, radio maximo, velocidad (px logicos / s)
WAVES = {
    "step":   dict(color=(115, 160, 255), max_r=50,  speed=88),
    "attack": dict(color=(255, 186, 96),  max_r=95,  speed=175),
    "pulse":  dict(color=(170, 235, 255), max_r=520, speed=250, bw=12.0, k=6, after=0.5),
    "hurt":   dict(color=(255, 70, 60),   max_r=46,  speed=120),
    "key":    dict(color=(255, 215, 90),  max_r=95,  speed=140),
    "locked": dict(color=(255, 90, 70),   max_r=42,  speed=100),
    "death":  dict(color=(205, 100, 255), max_r=55,  speed=110),
    "block":  dict(color=(70, 140, 255),  max_r=62,  speed=135),
    "menu":   dict(color=(150, 200, 255), max_r=175, speed=85),
    "bounce": dict(color=(120, 205, 240), max_r=55,  speed=120, bw=6.0, k=4),
    "aim":    dict(color=(255, 120, 70),  max_r=38,  speed=110),
    "arrowhit": dict(color=(255, 225, 150), max_r=30, speed=90),
    "shot":   dict(color=(255, 225, 150), max_r=34,  speed=110),
    "dash":   dict(color=(150, 225, 255), max_r=70,  speed=190),
    "dash_red": dict(color=(255, 60, 40), max_r=75,  speed=200),     # modo ANAKIN
    "stab":   dict(color=(255, 90, 50),   max_r=60,  speed=150),     # espada clavada (ANAKIN)
    "fshot":  dict(color=(255, 70, 50),   max_r=34,  speed=110),     # FUERZA: disparo normal
    "farrowhit": dict(color=(255, 70, 50), max_r=30, speed=90),
    "fsuperhit": dict(color=(255, 60, 40), max_r=110, speed=230),    # FUERZA: super carga
    "fsuperlight": dict(color=(255, 50, 36), max_r=70, speed=200),
    "superhit":   dict(color=(255, 240, 180), max_r=110, speed=230),
    "superlight": dict(color=(255, 230, 150), max_r=70,  speed=200),
}
# variantes AZULES (skin ANAKIN) de las ondas rojas: se intercambian los canales R y B
for _k in ("dash_red", "stab", "fshot", "farrowhit", "fsuperhit", "fsuperlight"):
    _c = dict(WAVES[_k])
    _c["color"] = _c["color"][::-1]
    WAVES[_k + "_b"] = _c

# "|" dibuja la palabra "o" entre dos teclas alternativas
CONTROLS = [
    (["A", "D"],            "Mover (o FLECHAS izq. / der.).\nCada paso lanza un pequeño eco."),
    (["W", "|", "Z"],       "Saltar (o FLECHA arriba). Con dirección:\nsalto diagonal con impulso."),
    (["ESPACIO", "|", "X"], "Atacar: golpe + onda ámbar. En el aire:\ntajo diagonal con rebote en enemigos."),
    (["S"],                 "Escudo: mantén S o FLECHA abajo.\nSe obtiene en el cofre del nivel 2."),
    (["E"],                 "Abrir cofres / interactuar."),
    (["Q"],                 "Súper eco: ilumina la sala y solidifica\nlos PUENTES FANTASMA. ¡Atrae monstruos!"),
    (["F", "|", "C"],       "Arco (cofre del nivel 5): toca = flecha.\nMantén y suelta = SÚPER DISPARO."),
    (["SHIFT"],             "Sigilo: lento y sin eco de pasos."),
    (["P"],                 "Reiniciar el nivel (pulsa P dos veces)."),
    (["ESC"],               "Pausa."),
    (["H"],                 "Mostrar / ocultar esta ayuda."),
    (["M", "|", "F11"],     "Sonido / Pantalla completa."),
]

# ----------------------------------------------------------------------------
#  PIXEL ART  (sprites 16x16 definidos como mapas de caracteres)
# ----------------------------------------------------------------------------
PAL = {
    "k": (18, 16, 26), "s": (206, 214, 230), "S": (132, 142, 170), "d": (78, 84, 112),
    "r": (190, 36, 48), "R": (112, 20, 36), "g": (246, 206, 72), "G": (176, 128, 32),
    "f": (234, 184, 142), "b": (116, 74, 42), "w": (240, 238, 230),
    "p": (96, 74, 120), "P": (150, 128, 176), "y": (255, 232, 90), "m": (200, 40, 60),
}

KNIGHT_DOWN = [
    "................",
    ".......rr.......",
    ".....kkkkkk.....",
    "....kssssssk....",
    "....ksSSSSsk....",
    "....kskkkkSk....",
    "....kSSSSSSk....",
    ".....kkkkkk.....",
    "...kkSSSSSSkk...",
    "..kdSrrrrrrSdk..",
    "..kdSrrggrrSdk..",
    "..kfdSrrrrSdfk..",
    "...kkSrrrrSkk...",
    "....kbbbbbbk....",
    "....kSSkkSSk....",
    "....kkk..kkk....",
]
KNIGHT_RIGHT = [
    "................",
    "........rr......",
    ".....kkkkkk.....",
    "....kssssssk....",
    "....kssSSSsk....",
    "....kSSSkkkk....",
    "....kSSSSSSk....",
    ".....kkkkkk.....",
    "....kkSSSSkk....",
    "...kdSrrrrSkkk..",
    "...kdSrrrrkGGk..",
    "...kfSrrrrkGgk..",
    "....kSrrrrkGGk..",
    ".....kbbbbbkk...",
    ".....kSSkSSk....",
    ".....kkk.kkk....",
]
GHOUL = [
    "................",
    ".....kkkkkk.....",
    "....kPPPPPPk....",
    "...kPPPPPPPPk...",
    "...kPyyPPyyPk...",
    "...kPPPPPPPPk...",
    "...kPPmwmwmPk...",
    "....kPPPPPPk....",
    "..kkkpppppkkk...",
    ".kPkppppppkPk...",
    ".kPkppppppkPk...",
    ".kwk.pppp.kwk...",
    "....kppppppk....",
    "....kpp..ppk....",
    "....kkk..kkk....",
    "................",
]
# murcielago de las catacumbas (mismo estilo y paleta que el fantasma)
BAT_A = [
    "................",
    "..k..........k..",
    ".kPk...kk...kPk.",
    ".kPPk.kppk.kPPk.",
    "kPPpPkkppkkPpPPk",
    "kPk.kpmppmpk.kPk",
    "k....kppppk....k",
    ".....kpwppwk....",
    "......kkkkkk....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]
BAT_B = [
    "................",
    "................",
    ".......kk.......",
    "......kppk......",
    ".....kppppk.....",
    "..kk.kpmpmk.kk..",
    ".kPPkkppppkkPPk.",
    "kPPpPkpwppwkPpPk",
    "kPpkPPkkkkPPkpPk",
    "kk..kPPkkPPk..kk",
    "......kk.kk.....",
    "................",
    "................",
    "................",
    "................",
    "................",
]
# fotograma intermedio (alas horizontales) para un aleteo mas fluido
BAT_C = [
    "................",
    "................",
    ".......kk.......",
    "..k...kppk...k..",
    ".kPk.kppppk.kPk.",
    "kPPPkkpmppmkPPPk",
    "k...kkpwppwk...k",
    "......kkkkkk....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]
# esqueleto arquero (mira a la derecha; se voltea para la izquierda)
SKEL = [
    "................",
    ".....kkkkkk.....",
    "....kwwwwwwk....",
    "....kwrwwrwk....",
    "....kwwwwwwk....",
    ".....kwkwwk.....",
    "......kkkk......",
    "....kkwwwwkkb...",
    "...kwkwwwwkwbb..",
    "...kwk.ww.kwbGb.",
    "....kkwwwwkkbGb.",
    ".....kwkwwk.bb..",
    ".....kwwwwk.b...",
    ".....kw..wk.....",
    ".....kk..kk.....",
    "................",
]
KEY = [
    "................",
    "................",
    "....kkkk........",
    "...kggggk.......",
    "..kgGkkGgk......",
    "..kgk..kgk......",
    "..kgGkkGgk......",
    "...kggggkk......",
    "....kkkgGk......",
    ".......gGk......",
    ".......gGkkk....",
    ".......gGggk....",
    ".......gGkkk....",
    ".......gGggk....",
    "........kkk.....",
    "................",
]
CHEST = [
    "................",
    "................",
    "................",
    "................",
    "...kkkkkkkkkk...",
    "..kbbbbbbbbbbk..",
    "..kbGbbbbbbGbk..",
    "..kGGGGGGGGGGk..",
    "..kbbbbggbbbbk..",
    "..kbbbbgkgbbbk..",
    "..kbbbbggbbbbk..",
    "..kbGbbbbbbGbk..",
    "..kbbbbbbbbbbk..",
    "..kkkkkkkkkkkk..",
    "................",
    "................",
]
CHEST_OPEN = [
    "................",
    "................",
    "...kkkkkkkkkk...",
    "..kbGbbbbbbGbk..",
    "..kbbbbbbbbbbk..",
    "..kkkkkkkkkkkk..",
    "..kyyyyyyyyyyk..",
    "..kywyyyyywyyk..",
    "..kyyyyyyyyyyk..",
    "..kGGGGGGGGGGk..",
    "..kbbbbbbbbbbk..",
    "..kbGbbbbbbGbk..",
    "..kbbbbbbbbbbk..",
    "..kkkkkkkkkkkk..",
    "................",
    "................",
]
HEART = ["..##.##..", ".#######.", ".#######.", "..#####..", "...###...", "....#...."]

# --- piernas / pies alternativos para las animaciones (fotogramas extra) ---
KN_LEGS_A = [".....kSSk..kSSk.", ".....kkk....kkk."]     # paso largo (adelante)
KN_LEGS_A2 = ["....kSSk..kSSk..", "....kkk....kkk.."]    # paso largo (atras)
KN_LEGS_T = ["......kSSSk.....", "......kkkkk....."]     # piernas juntas
KN_LEGS_UP = [".....kSSSSSk....", "......kkkkk....."]    # salto: piernas recogidas
GH_LEGS_A = ["...kpp....ppk...", "...kkk....kkk...", "................"]
GH_LEGS_T = ["....kppppppk....", "....kkkkkkkk....", "................"]
SK_LEGS_A = ["....kw....wk....", "....kk....kk....", "................"]
SK_LEGS_T = ["......kwwk......", "......kkkk......", "................"]


def make_sprite(rows):
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    for y, row in enumerate(rows[:16]):
        row = row.ljust(16, ".")[:16]
        for x, ch in enumerate(row):
            c = PAL.get(ch)
            if c:
                surf.set_at((x, y), c)
    return surf


def variant(rows, cut, tail, bob=False):
    """Fotograma derivado: sustituye las filas de las piernas (desde `cut`) y,
    opcionalmente, sube el torso 1 px (rebote al caminar)."""
    head = rows[:cut] if not bob else rows[1:cut] + [rows[cut - 1]]
    return make_sprite(list(head) + list(tail))


def make_heart(color, outline):
    surf = pygame.Surface((9, 7), pygame.SRCALPHA)
    for y, row in enumerate(HEART):
        for x, ch in enumerate(row):
            if ch == "#":
                surf.set_at((x, y), color)
    return surf


def make_floor(v):
    rnd = random.Random(77 + v * 13)
    s = pygame.Surface((TILE, TILE))
    base = (88, 84, 100)
    for y in range(TILE):
        for x in range(TILE):
            n = rnd.randint(-7, 7)
            s.set_at((x, y), (base[0] + n, base[1] + n, base[2] + n + 2))
    mortar = (68, 64, 80)          # junta mas suave: se nota menos la cuadricula
    hl = (100, 96, 114)
    pygame.draw.line(s, mortar, (0, 0), (15, 0))
    pygame.draw.line(s, mortar, (0, 0), (0, 15))
    pygame.draw.line(s, hl, (1, 1), (15, 1))
    pygame.draw.line(s, hl, (1, 1), (1, 15))
    if v == 1:      # grieta
        x, y = rnd.randint(4, 10), 3
        for _ in range(9):
            s.set_at((x, y), (46, 42, 56))
            y += 1
            x += rnd.choice((-1, 0, 1))
            x = max(2, min(14, x))
    elif v == 2:    # musgo
        for _ in range(10):
            s.set_at((rnd.randint(2, 14), rnd.randint(2, 14)), (70, 104, 66))
    elif v == 3:    # mancha oscura
        pygame.draw.ellipse(s, (66, 62, 78), (4, 5, 8, 6))
    return s


def make_wall(v):
    rnd = random.Random(500 + v * 7)
    s = pygame.Surface((TILE, TILE))
    mortar = (58, 50, 62)          # mortero mas claro = menos contraste de cuadricula
    s.fill(mortar)
    for r, y0 in enumerate((0, 5, 10)):
        off = 0 if r % 2 == 0 else 4
        for bx in range(-8 + off, TILE, 8):
            x0, x1 = max(bx, 0), min(bx + 7, TILE - 1)
            if x1 < x0:
                continue
            base = rnd.randint(-10, 10)
            col = (128 + base, 100 + base, 94 + base)
            for yy in range(y0, y0 + 4):
                for xx in range(x0, x1 + 1):
                    n = rnd.randint(-5, 5)
                    c = [col[0] + n, col[1] + n, col[2] + n]
                    if yy == y0:
                        c = [c[0] + 9, c[1] + 8, c[2] + 8]
                    elif yy == y0 + 3:
                        c = [c[0] - 13, c[1] - 12, c[2] - 12]
                    s.set_at((xx, yy), tuple(max(0, min(255, q)) for q in c))
    if v == 2:
        for _ in range(8):
            s.set_at((rnd.randint(0, 15), rnd.randint(0, 15)), (74, 100, 70))
    return s


def make_door(opened):
    s = make_wall(0).copy()
    pygame.draw.rect(s, (28, 24, 34), (2, 1, 12, 15))
    pygame.draw.rect(s, (92, 86, 108), (2, 1, 12, 15), 1)
    if not opened:
        pygame.draw.rect(s, (118, 76, 44), (3, 3, 10, 13))
        for x in (5, 8, 10):
            pygame.draw.line(s, (84, 52, 30), (x, 3), (x, 15))
        pygame.draw.line(s, (156, 104, 62), (3, 3), (3, 15))
        pygame.draw.rect(s, (62, 64, 78), (3, 6, 10, 2))
        pygame.draw.rect(s, (62, 64, 78), (3, 12, 10, 2))
        pygame.draw.rect(s, GOLD, (7, 9, 3, 3))
        s.set_at((8, 10), (30, 20, 10))
    else:
        pygame.draw.rect(s, (10, 12, 22), (3, 3, 10, 13))
        pygame.draw.rect(s, (90, 230, 150), (5, 5, 6, 11))
        pygame.draw.rect(s, (200, 255, 220), (7, 7, 2, 9))
        pygame.draw.rect(s, (118, 76, 44), (3, 3, 2, 13))
    return s


def make_platform():
    """Plataforma flotante: el mismo ladrillo de make_wall, en version delgada."""
    w = make_wall(1)
    s = pygame.Surface((TILE, 6))
    s.blit(w, (0, 0), (0, 0, TILE, 6))
    pygame.draw.line(s, (190, 170, 150), (0, 0), (TILE - 1, 0))
    pygame.draw.line(s, (30, 24, 38), (0, 5), (TILE - 1, 5))
    return s


def anim_set(idle, walk, jump, fall):
    return dict(idle=idle, walk=walk, jump=jump, fall=fall)


# Skin ANAKIN: el caballero con tunica negra de Jedi oscuro (cara visible, sin casco)
AK_PAL = {
    "r": (30, 28, 40), "S": (52, 48, 64), "d": (40, 36, 50), "G": (112, 112, 126),
    "g": (190, 190, 204), "b": (96, 62, 38), "k": (10, 8, 14),
}
AK_RIGHT = list(KNIGHT_RIGHT)
AK_RIGHT[3] = "....kbbbbbbk...."
AK_RIGHT[4] = "....kbbbfffk...."
AK_RIGHT[5] = "....kbbffkfk...."
AK_RIGHT[6] = "....kffffffk...."
AK_FORCE_ROWS = list(AK_RIGHT)
AK_FORCE_ROWS[10] = "...kdSrrrrSffffk"          # brazo extendido al frente (usando la FUERZA)
AK_FORCE_ROWS[11] = "...kfSrrrrkkkkk."
AK_FORCE_ROWS[12] = "....kSrrrrk....."

# --- DARTH VADER: sprites copiados TAL CUAL de la imagen de referencia (31 x 30 celdas).
#     Se reducen a VD_W x VD_H pixeles al cargar. "u"/"x" = luces del panel del pecho.
VD_W, VD_H = 21, 20
VD_LEG0 = 27                      # primera fila de las piernas (para los pasos)
VD_PAL = {
    "0": (14, 14, 18), "1": (14, 14, 18), "2": (14, 14, 18), "3": (14, 14, 18), "4": (18, 18, 22),
    "5": (34, 34, 40), "6": (44, 44, 52), "7": (58, 58, 66), "8": (72, 72, 82), "9": (92, 92, 104),
    "a": (118, 118, 130), "b": (152, 152, 160), "u": (104, 112, 215), "x": (214, 96, 70),
}
VD_IDLE = [
    "...............................",
    "...........43335...............",
    "..........3b978b4..............",
    ".........3b97888b4.............",
    ".........2897886b0.............",
    ".........2a9aa6660.............",
    ".........06a64a660.............",
    "........39b79b3a884............",
    "........077b774a884............",
    "........079b9760a884...........",
    "........0b9b9b60a884...........",
    ".........00000008884...........",
    "..........096660333............",
    "........339898984093...........",
    ".......038b8b8b8a8494..........",
    ".......00698989666394..........",
    ".......0066abu86363992.........",
    "......40606a8x86066093.........",
    "......43606aba86066093.........",
    "......43a36666660a98093........",
    "......4a90b8.8b4a998393........",
    "......49326666649498093........",
    "......466056865a3662093........",
    "......43328505888406093........",
    "......466388463884660994.......",
    "......4662a84628a3660994.......",
    ".......000a83338a0000994.......",
    ".........2860.0680..000........",
    ".........2860.2680.............",
    "........48663.26684............",
]
VD_FORCE = [      # brazo extendido (la FUERZA)
    "...............................",
    "...........00035...............",
    "..........0b978b0..............",
    ".........0b97888b3.............",
    ".........0897886b0.............",
    ".........3a9aa6660.............",
    ".........06a63a660.............",
    "........29b79b3a883............",
    "........377b774a880............",
    "........079b9764a880...........",
    "........0b9b9.74a880...........",
    "00..02...00000008880...........",
    "2a03a90...396660000............",
    "39890900038898980090...........",
    "2a890968a8b8b8b8a8390..........",
    "3899886766a8a8a666390..........",
    ".0000666666bbu86064990.........",
    ".....000006a8x86066490.........",
    "......00606bba86066390.........",
    "......06306666660a98492........",
    "......3060b8b8b0a998390........",
    "......06306666609098390........",
    "......306056865a0660492........",
    "......06338545888306390........",
    "......066388063880664994.......",
    "......0660a80638a0663993.......",
    ".......003a80038a3333993.......",
    ".........0862.0683..343........",
    ".........0862.0682.............",
    "........08660.06680............",
]


def _vd_lift(g, left, right):
    """Paso: levanta una pierna una fila."""
    h, w = len(g), len(g[0])
    n = [r[:] for r in g]
    for use, (c0, c1) in ((left, (0, 14)), (right, (14, w))):
        if not use:
            continue
        for y in range(VD_LEG0, h):
            for x in range(c0, c1):
                ch = g[y][x]
                if ch != ".":
                    n[y - 1][x] = ch
                elif y - 1 >= VD_LEG0:
                    n[y - 1][x] = "."
        for x in range(c0, c1):
            n[h - 1][x] = "."
    return n


def _vd_bob(g):
    """Rebote: el torso sube una fila (las piernas se quedan)."""
    n = [r[:] for r in g]
    for y in range(0, VD_LEG0 - 1):
        n[y] = g[y + 1][:]
    return n


def _vd_surf(g):
    h, w = len(g), len(g[0])
    sf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            c = VD_PAL.get(g[y][x])
            if c:
                sf.set_at((x, y), c)
    return pygame.transform.smoothscale(sf, (VD_W, VD_H))


def build_vader_anim():
    idle = [list(r) for r in VD_IDLE]
    one = lambda g: _vd_surf(g).convert_alpha()
    left = dict(idle=one(idle),
                walk=[one(_vd_lift(idle, True, False)), one(_vd_bob(idle)),
                      one(_vd_lift(idle, False, True)), one(_vd_bob(idle))],
                jump=one(_vd_lift(idle, True, True)), fall=one(idle),
                force=one([list(r) for r in VD_FORCE]))
    flip = lambda sf: pygame.transform.flip(sf, True, False).convert_alpha()
    right = {k: ([flip(x) for x in v] if isinstance(v, list) else flip(v)) for k, v in left.items()}
    return {"left": left, "right": right}   # la imagen original mira a la izquierda




def build_knight_anim(pal_over=None, rows=None, force_rows=None):
    """Genera el set de animaciones del caballero (opcionalmente con otra paleta y sprite)."""
    saved = dict(PAL)
    if pal_over:
        PAL.update(pal_over)
    try:
        kn = rows or KNIGHT_RIGHT
        kr = make_sprite(kn)
        walk = [variant(kn, 14, KN_LEGS_A), variant(kn, 14, KN_LEGS_T, True),
                variant(kn, 14, KN_LEGS_A2), variant(kn, 14, KN_LEGS_T, True)]
        jump = variant(kn, 14, KN_LEGS_UP)
        fall = variant(kn, 14, KN_LEGS_A)
        right = anim_set(kr, walk, jump, fall)
        if force_rows:
            right["force"] = variant(force_rows, 14, KN_LEGS_A)
    finally:
        PAL.clear()
        PAL.update(saved)
    flip = lambda sp: pygame.transform.flip(sp, True, False).convert_alpha()
    return {
        "right": {k: ([x.convert_alpha() for x in v] if isinstance(v, list) else v.convert_alpha())
                  for k, v in right.items()},
        "left": {k: ([flip(x) for x in v] if isinstance(v, list) else flip(v))
                 for k, v in right.items()},
    }


class Textures:
    def __init__(self):
        self.floors = [make_floor(i).convert() for i in range(4)]
        self.walls = [make_wall(i).convert() for i in range(3)]
        self.plat = make_platform().convert()
        self.door_closed = make_door(False).convert()
        self.door_open = make_door(True).convert()
        kr = make_sprite(KNIGHT_RIGHT)
        self.knight = {
            "down": make_sprite(KNIGHT_DOWN).convert_alpha(),
            "right": kr.convert_alpha(),
            "left": pygame.transform.flip(kr, True, False).convert_alpha(),
        }
        # --- caballero: ciclo de 4 pasos + salto + caida
        kn = KNIGHT_RIGHT
        walk = [variant(kn, 14, KN_LEGS_A), variant(kn, 14, KN_LEGS_T, True),
                variant(kn, 14, KN_LEGS_A2), variant(kn, 14, KN_LEGS_T, True)]
        jump = variant(kn, 14, KN_LEGS_UP)
        fall = variant(kn, 14, KN_LEGS_A)
        right = anim_set(kr, walk, jump, fall)
        flip = lambda s: pygame.transform.flip(s, True, False).convert_alpha()
        self.knight_anim = {
            "right": {k: ([x.convert_alpha() for x in v] if isinstance(v, list) else v.convert_alpha())
                      for k, v in right.items()},
            "left": {k: ([flip(x) for x in v] if isinstance(v, list) else flip(v))
                     for k, v in right.items()},
        }
        self.knight_anim_ak = build_knight_anim(AK_PAL, AK_RIGHT, AK_FORCE_ROWS)   # skin ANAKIN
        self.knight_anim_vd = build_vader_anim()                                    # skin DARTH VADER
        # --- fantasma: ciclo de caminar
        self.ghoul = make_sprite(GHOUL).convert_alpha()
        self.ghoul_anim = dict(
            idle=self.ghoul,
            walk=[variant(GHOUL, 13, GH_LEGS_A).convert_alpha(),
                  variant(GHOUL, 13, GH_LEGS_T, True).convert_alpha(),
                  self.ghoul,
                  variant(GHOUL, 13, GH_LEGS_T, True).convert_alpha()])
        # --- esqueleto: ciclo de caminar (derecha / izquierda)
        sk = make_sprite(SKEL)
        swalk = [sk, variant(SKEL, 13, SK_LEGS_A), variant(SKEL, 13, SK_LEGS_T, True),
                 variant(SKEL, 13, SK_LEGS_A)]
        self.skel = {"right": sk.convert_alpha(),
                     "left": pygame.transform.flip(sk, True, False).convert_alpha()}
        self.skel_anim = {
            "right": dict(idle=self.skel["right"], walk=[x.convert_alpha() for x in swalk]),
            "left": dict(idle=self.skel["left"], walk=[flip(x) for x in swalk]),
        }
        # --- murcielago: 4 fotogramas (alas arriba, medio, abajo, medio)
        self.bat = [make_sprite(BAT_A).convert_alpha(), make_sprite(BAT_C).convert_alpha(),
                    make_sprite(BAT_B).convert_alpha(), make_sprite(BAT_C).convert_alpha()]
        self.chest = make_sprite(CHEST).convert_alpha()
        self.chest_open = make_sprite(CHEST_OPEN).convert_alpha()
        self.key = make_sprite(KEY).convert_alpha()
        self.key_dim = self.key.copy()
        self.key_dim.fill((70, 70, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.shadow = pygame.Surface((12, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(self.shadow, (0, 0, 0, 120), (0, 0, 12, 5))
        self.heart_full = make_heart((226, 54, 70), None).convert_alpha()
        self.heart_empty = make_heart((60, 44, 60), None).convert_alpha()
        self.shadow_top = pygame.Surface((TILE, 5), pygame.SRCALPHA)
        for y in range(5):
            self.shadow_top.fill((0, 0, 0, int(120 * (1 - y / 5) ** 1.3)), (0, y, TILE, 1))
        self.shadow_left = pygame.Surface((3, TILE), pygame.SRCALPHA)
        for x in range(3):
            self.shadow_left.fill((0, 0, 0, int(90 * (1 - x / 3))), (x, 0, 1, TILE))
        self.edge_light = pygame.Surface((TILE, 1), pygame.SRCALPHA)
        self.edge_light.fill((210, 190, 170, 70))
        # --- puentes fantasma (activo / dormido)
        self.ghost_on = pygame.Surface((TILE, 6), pygame.SRCALPHA)
        self.ghost_on.fill((110, 215, 245, 170))
        pygame.draw.line(self.ghost_on, (220, 250, 255, 235), (0, 0), (TILE - 1, 0))
        pygame.draw.line(self.ghost_on, (60, 140, 190, 210), (0, 5), (TILE - 1, 5))
        self.ghost_on = self.ghost_on.convert_alpha()
        self.ghost_off = pygame.Surface((TILE, 6), pygame.SRCALPHA)
        self.ghost_off.fill((110, 215, 245, 34))
        pygame.draw.line(self.ghost_off, (150, 220, 240, 95), (0, 0), (TILE - 1, 0))
        self.ghost_off = self.ghost_off.convert_alpha()
        # --- difuminado de los bordes del mapa (suaviza el limite estricto)
        ef = pygame.Surface((MAP_W, MAP_H))
        ef.fill((255, 255, 255))
        FADE = 34
        for i in range(FADE):
            v = int(255 * (0.58 + 0.42 * (i / FADE) ** 1.3))
            pygame.draw.rect(ef, (v, v, v), (i, i, MAP_W - 2 * i, MAP_H - 2 * i), 1)
        self.edge_fade = ef.convert()


# ----------------------------------------------------------------------------
#  UTILIDADES DE LUZ
# ----------------------------------------------------------------------------
_TRIG = {}


def trig(n):
    if n not in _TRIG:
        _TRIG[n] = ([math.cos(2 * math.pi * i / n) for i in range(n)],
                    [math.sin(2 * math.pi * i / n) for i in range(n)])
    return _TRIG[n]


def cast_rays(level, ox, oy, maxr, n):
    """Lanza n rayos desde (ox,oy). Devuelve la distancia a la que cada rayo
    toca un muro (+7 px para que la cara del muro tambien se ilumine)."""
    cs, sn = trig(n)
    out = []
    for i in range(n):
        cx, cy = cs[i], sn[i]
        d = 0.0
        hit = maxr
        while d < maxr:
            d += 2.0
            if level.is_wall(int((ox + cx * d) // TILE), int((oy + cy * d) // TILE)):
                hit = d
                break
        out.append(min(hit + 7.0, maxr + 7.0))
    return out


def make_radial(radius, color, strength):
    d = radius * 2
    s = pygame.Surface((d, d))
    s.fill((0, 0, 0))
    for y in range(d):
        for x in range(d):
            dist = math.hypot(x - radius + 0.5, y - radius + 0.5)
            if dist < radius:
                v = (1 - dist / radius) ** 1.6 * strength
                s.set_at((x, y), (int(color[0] * v), int(color[1] * v), int(color[2] * v)))
    return s.convert()


def make_beam(w, h, color, strength):
    """Haz de luz elipsoidal (se coloca delante del caballero)."""
    s = pygame.Surface((w, h))
    s.fill((0, 0, 0))
    for y in range(h):
        for x in range(w):
            nx = (x + 0.5 - w / 2) / (w / 2)
            ny = (y + 0.5 - h / 2) / (h / 2)
            d = math.hypot(nx, ny)
            if d < 1:
                v = (1 - d) ** 1.3 * strength
                s.set_at((x, y), (int(color[0] * v), int(color[1] * v), int(color[2] * v)))
    return s.convert()


def make_torch_surfs(level, ox, oy, radius, tint):
    """Luz estatica de antorcha con sombras (3 niveles de parpadeo)."""
    n, K = 96, 12
    rays = cast_rays(level, ox, oy, radius, n)
    cs, sn = trig(n)
    base = pygame.Surface((MAP_W, MAP_H))
    base.fill((0, 0, 0))
    for k in range(K - 1, -1, -1):
        ro = radius * (k + 1) / K
        ri = radius * k / K
        inten = (1 - (k + 0.5) / K) ** 1.5
        col = (int(tint[0] * inten), int(tint[1] * inten), int(tint[2] * inten))
        for i in range(n):
            j = (i + 1) % n
            d0, d1 = rays[i], rays[j]
            o0, o1 = min(ro, d0), min(ro, d1)
            i0, i1 = min(ri, d0), min(ri, d1)
            if o0 <= i0 and o1 <= i1:
                continue
            pts = [(ox + cs[i] * i0, oy + sn[i] * i0), (ox + cs[i] * o0, oy + sn[i] * o0),
                   (ox + cs[j] * o1, oy + sn[j] * o1), (ox + cs[j] * i1, oy + sn[j] * i1)]
            pygame.draw.polygon(base, col, pts)
    base = base.convert()
    out = []
    for f in (0.74, 0.88, 1.0):
        s = base.copy()
        v = int(255 * f)
        s.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
        out.append(s)
    return out


# ----------------------------------------------------------------------------
#  FISICA (cajas con x = centro, y = PIES)
# ----------------------------------------------------------------------------
def solid_hit(lv, x, y, hw, h, is_player):
    x0, x1 = int((x - hw) // TILE), int((x + hw - 0.01) // TILE)
    y0, y1 = int((y - h) // TILE), int((y - 0.01) // TILE)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if lv.blocks(tx, ty, is_player):
                return True
    return False


def move_body(lv, b, dt):
    """Movimiento con gravedad: muros solidos y plataformas de un solo sentido
    (se atraviesan desde abajo y se pisan desde arriba)."""
    b.hit_wall = False
    nx = b.x + b.vx * dt
    if solid_hit(lv, nx, b.y, b.hw, b.h, b.is_player):
        b.hit_wall = True
        b.vx = 0.0
    else:
        b.x = nx
    ny = b.y + b.vy * dt
    b.on_ground = False
    if b.vy >= 0:
        row = int((ny - 0.01) // TILE)
        if solid_hit(lv, b.x, ny, b.hw, b.h, b.is_player):
            b.y = row * TILE
            b.vy = 0.0
            b.on_ground = True
        else:
            land = False
            if ny > row * TILE and b.y <= row * TILE + 0.01:
                for tx in range(int((b.x - b.hw) // TILE), int((b.x + b.hw - 0.01) // TILE) + 1):
                    if lv.is_plat(tx, row):
                        land = True
                        break
            if land:
                b.y = row * TILE
                b.vy = 0.0
                b.on_ground = True
            else:
                b.y = ny
    else:
        if solid_hit(lv, b.x, ny, b.hw, b.h, b.is_player):
            b.vy = 0.0
        else:
            b.y = ny


def move_fly(lv, b, dt):
    nx = b.x + b.vx * dt
    if solid_hit(lv, nx, b.y, b.hw, b.h, False):
        b.vx *= -0.3
    else:
        b.x = nx
    ny = b.y + b.vy * dt
    if solid_hit(lv, b.x, ny, b.hw, b.h, False):
        b.vy *= -0.3
    else:
        b.y = ny


def boxes_overlap(a, b):
    return (abs(a.x - b.x) < a.hw + b.hw and
            abs((a.y - a.h / 2) - (b.y - b.h / 2)) < (a.h + b.h) / 2)


# ----------------------------------------------------------------------------
#  ARENAS  (suelo principal + plataformas flotantes)
# ----------------------------------------------------------------------------
# Los disenos se escriben en las coordenadas ORIGINALES (rejilla 20 x 11) y
# arena() los desplaza (DX, DY) al nuevo tamano mas grande.
# Plataformas: (fila, col_inicio, col_fin). Cada salto sube 2 filas (32 px).
# Entidades: (col, fila) de la casilla donde aparecen.
# ghosts: puentes fantasma (fila, col_ini, col_fin) -> se solidifican con el Super Eco.
# vents:  corrientes de aire ascendentes (col, altura_en_tiles), 2 casillas de ancho.
DEFAULT_TORCHES = ((6, 0), (12, 0), (18, 0), (0, 7), (COLS - 1, 6), (9, ROWS - 1), (15, ROWS - 1))
LEDGES = ((2, 6, 9), (2, 14, 17))       # repisas altas en coordenadas NUEVAS (usan el espacio extra)


def arena(name, plats, ghouls, bats, key, start, chest=None, torches=None,
          skels=(), chest_item="shield", ghosts=(), vents=(), ledges=True):
    if torches is None:
        torches = DEFAULT_TORCHES
    g = [["."] * COLS for _ in range(ROWS)]
    for x in range(COLS):
        g[0][x] = "#"
        g[ROWS - 1][x] = "#"
    for y in range(ROWS):
        g[y][0] = "#"
        g[y][COLS - 1] = "#"
    for (r, c0, c1) in plats:
        for c in range(c0 + DX, c1 + DX + 1):
            g[r + DY][c] = "="
    if ledges:
        for (r, c0, c1) in LEDGES:
            for c in range(c0, c1 + 1):
                if g[r][c] == ".":
                    g[r][c] = "="
    for (r, c0, c1) in ghosts:
        for c in range(c0 + DX, c1 + DX + 1):
            if g[r + DY][c] == ".":
                g[r + DY][c] = "~"
    for (tx, ty) in torches:
        g[ty][tx] = "T"
    g[ROWS - 2][COLS - 1] = "E"                  # puerta de salida (a ras de suelo)
    sh = lambda q: (q[0] + DX, q[1] + DY)
    vrects = []
    for (c, hgt) in vents:
        x0 = (c + DX) * TILE
        vrects.append((x0, (ROWS - 1 - hgt) * TILE, x0 + 2 * TILE, (ROWS - 1) * TILE))
    return dict(name=name, rows=["".join(r) for r in g],
                ghouls=[sh(q) for q in ghouls], bats=[sh(q) for q in bats],
                key=sh(key) if key else None, start=sh(start),
                chest=sh(chest) if chest else None, skels=[sh(q) for q in skels],
                chest_item=chest_item, vents=vrects)


LEVELS = [
    arena("La Cripta Antigua",
          plats=[(8, 2, 5), (8, 14, 17), (6, 7, 12), (4, 2, 6), (4, 13, 17)],
          ghouls=[(11, 9), (9, 5)], bats=[(4, 2)], key=(15, 3), start=(2, 9), ledges=False),
    arena("Pasadizos Olvidados",
          plats=[(8, 3, 6), (8, 12, 16), (6, 8, 11), (4, 1, 6), (4, 13, 18), (2, 7, 12)],
          ghouls=[(10, 9), (14, 7), (9, 5)], bats=[(3, 3), (16, 2)],
          key=(10, 1), start=(2, 9), chest=(16, 3), vents=[(9, 6)]),
    arena("Catacumbas Susurrantes",
          plats=[(8, 1, 4), (8, 8, 11), (8, 15, 18), (6, 4, 7), (6, 12, 15),
                 (4, 1, 3), (4, 8, 11), (4, 16, 18), (2, 5, 14)],
          ghouls=[(6, 9), (14, 9), (9, 7), (13, 5)], bats=[(3, 2), (17, 2), (10, 3)],
          key=(9, 1), start=(2, 9), ghosts=[(4, 4, 7), (4, 12, 15)], vents=[(13, 6)]),
    arena("El Corazón del Abismo",
          plats=[(8, 1, 3), (8, 8, 11), (8, 16, 18), (6, 4, 7), (6, 12, 15),
                 (4, 1, 3), (4, 8, 11), (4, 16, 18), (2, 5, 7), (2, 12, 14)],
          ghouls=[(6, 9), (10, 9), (14, 9), (9, 7), (13, 5)],
          bats=[(3, 3), (17, 3), (6, 1), (10, 2)], key=(13, 1), start=(2, 9),
          ghosts=[(2, 8, 11), (4, 4, 7), (4, 12, 15)], vents=[(5, 7)]),
    # ---- niveles nuevos -------------------------------------------------
    arena("El Arsenal Maldito",                       # nivel 5: cofre con el ARCO
          plats=[(8, 1, 4), (8, 15, 18), (6, 5, 8), (6, 11, 14), (4, 2, 6), (4, 13, 17), (2, 7, 12)],
          ghouls=[(7, 5), (12, 9), (3, 3)], bats=[(10, 4), (16, 6)],
          key=(9, 1), start=(2, 9), chest=(15, 3), chest_item="bow",
          ghosts=[(6, 9, 10)], vents=[(9, 7)]),
    arena("La Torre del Arquero",                     # nivel 6: aparecen los esqueletos
          plats=[(8, 1, 4), (8, 8, 11), (8, 15, 18), (6, 4, 7), (6, 12, 15),
                 (4, 1, 3), (4, 8, 11), (4, 16, 18), (2, 5, 14)],
          ghouls=[(6, 9), (9, 7)], bats=[(3, 2), (10, 3)], skels=[(17, 3), (2, 3)],
          key=(9, 1), start=(2, 9), ghosts=[(4, 4, 7), (4, 12, 15)], vents=[(16, 7)]),
    arena("Salón de Huesos",                          # nivel 7
          plats=[(8, 2, 5), (8, 8, 11), (8, 14, 17), (6, 5, 8), (6, 11, 14),
                 (4, 2, 5), (4, 8, 11), (4, 14, 17), (2, 5, 8), (2, 11, 14)],
          ghouls=[(8, 9), (12, 9), (6, 5)], bats=[(10, 6), (16, 4)], skels=[(15, 3), (3, 3)],
          key=(7, 1), start=(2, 9), ghosts=[(4, 6, 7), (4, 12, 13)], vents=[(6, 7), (12, 7)]),
    arena("El Trono del Eco",                         # nivel 8
          plats=[(8, 1, 3), (8, 8, 11), (8, 16, 18), (6, 4, 7), (6, 12, 15),
                 (4, 1, 3), (4, 8, 11), (4, 16, 18), (2, 5, 7), (2, 12, 14)],
          ghouls=[(6, 9), (14, 9), (5, 5)], bats=[(3, 6), (17, 6), (10, 1)],
          skels=[(9, 3), (17, 3), (2, 3)], key=(13, 1), start=(2, 9),
          ghosts=[(2, 8, 11), (4, 4, 7), (4, 12, 15)], vents=[(5, 7), (13, 7)]),
    # ---- ampliacion: niveles 9 a 14 -----------------------------------------
    arena("La Escalera Rota",                         # nivel 9: escalera en zigzag
          plats=[(8, 1, 3), (8, 16, 18), (6, 4, 7), (6, 12, 15), (4, 8, 11), (2, 2, 5), (2, 14, 17)],
          ghouls=[(8, 9), (14, 9), (5, 5)], bats=[(10, 3), (3, 3)], skels=[(17, 7)],
          key=(3, 1), start=(2, 9), vents=[(9, 7)]),
    arena("Puentes Etéreos",                          # nivel 10: casi todo son puentes fantasma
          plats=[(8, 1, 3), (8, 16, 18), (4, 8, 11), (2, 5, 14)],
          ghouls=[(6, 9), (14, 9), (9, 3)], bats=[(3, 4), (16, 4), (10, 6)], skels=[(2, 7)],
          key=(9, 1), start=(2, 9), ghosts=[(6, 4, 6), (6, 13, 15), (8, 8, 11)]),
    arena("Foso de Flechas",                          # nivel 11: muchos esqueletos
          plats=[(8, 2, 5), (8, 14, 17), (6, 8, 11), (4, 3, 6), (4, 13, 16), (2, 8, 11)],
          ghouls=[(9, 9), (9, 5)], bats=[(10, 4), (6, 6)], skels=[(3, 7), (16, 7), (15, 3)],
          key=(9, 1), start=(2, 9)),
    arena("Torres Gemelas",                           # nivel 12: dos torres unidas por un puente fantasma
          plats=[(8, 2, 4), (6, 2, 4), (4, 2, 4), (2, 2, 4),
                 (8, 15, 17), (6, 15, 17), (4, 15, 17), (2, 15, 17), (6, 8, 11)],
          ghouls=[(10, 5), (5, 9), (14, 9)], bats=[(9, 3), (6, 2), (13, 2)], skels=[(3, 1), (16, 1)],
          key=(9, 1), start=(2, 9), ghosts=[(2, 5, 14)], vents=[(9, 7)]),
    arena("Corrientes Cruzadas",                      # nivel 13: se sube a golpe de corrientes de aire
          plats=[(8, 8, 11), (4, 3, 6), (4, 13, 16), (2, 8, 11)],
          ghouls=[(5, 9), (14, 9), (9, 7)], bats=[(6, 4), (13, 4), (9, 3), (3, 2)], skels=[(16, 3)],
          key=(9, 1), start=(2, 9), vents=[(3, 7), (9, 7), (15, 7)]),
    arena("La Cámara del Eco Final",                  # nivel 14: final
          plats=[(8, 1, 4), (8, 8, 11), (8, 15, 18), (6, 3, 6), (6, 13, 16), (4, 8, 11),
                 (4, 1, 2), (4, 17, 18), (2, 4, 7), (2, 12, 15)],
          ghouls=[(6, 9), (10, 7), (14, 9), (8, 3)], bats=[(2, 2), (17, 2), (10, 5)],
          skels=[(2, 3), (18, 3), (16, 5)], key=(5, 1), start=(2, 9),
          ghosts=[(2, 8, 11)], vents=[(9, 7)]),
]

MENU_ARENA = arena("Menu", plats=[(8, 2, 5), (8, 14, 17), (6, 8, 11)], ghouls=[], bats=[],
                   key=None, start=(3, 9), ledges=False)

# Sala de practica del mini tutorial (el fantasma aparece mas adelante, ver tut_advance)
TUTORIAL_ARENA = arena("Sala de Práctica", plats=[(8, 7, 11)], ghouls=[], bats=[],
                       key=(16, 9), start=(2, 9), ledges=False)


# ----------------------------------------------------------------------------
#  CLASES DEL JUEGO
# ----------------------------------------------------------------------------
class Level:
    def __init__(self, spec, textures):
        self.name = spec["name"]
        self.tex = textures
        self.grid = [list(r) for r in spec["rows"]]
        feet = lambda c, r: (c * TILE + 8, (r + 1) * TILE)
        self.start = feet(*spec["start"])
        self.ghoul_spawns = [feet(c, r) for c, r in spec["ghouls"]]
        self.bat_spawns = [(c * TILE + 8, r * TILE + 8) for c, r in spec["bats"]]
        self.key = (spec["key"][0] * TILE + 8, (spec["key"][1] + 1) * TILE - 8) if spec["key"] else None
        self.chest = feet(*spec["chest"]) if spec["chest"] else None
        self.chest_item = spec.get("chest_item", "shield")
        self.skel_spawns = [feet(c, r) for c, r in spec.get("skels", [])]
        self.vents = list(spec.get("vents", []))
        self.door = (COLS - 1, ROWS - 2)
        self.door_open = False
        self.torches = [(x, y) for y, row in enumerate(self.grid) for x, ch in enumerate(row) if ch == "T"]
        self.ghost_cells = [(x, y) for y, row in enumerate(self.grid) for x, ch in enumerate(row) if ch == "~"]
        self.ghost_t = {}                      # casilla -> segundos que le quedan solida
        self.static = self.bake()
        self.torch_lights = []
        for (tx, ty) in self.torches:
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                if not self.is_wall(tx + dx, ty + dy):
                    ox, oy = tx * TILE + 8 + dx * 10, ty * TILE + 8 + dy * 10
                    surfs = make_torch_surfs(self, ox, oy, 100, (255, 168, 84))
                    self.torch_lights.append(dict(tile=(tx, ty), surfs=surfs,
                                                  phase=random.random() * 6.28))
                    break

    # --- consultas
    def is_wall(self, tx, ty):
        if tx < 0 or ty < 0 or tx >= COLS or ty >= ROWS:
            return True
        return self.grid[ty][tx] in "#TE"

    def is_plat(self, tx, ty):
        if tx < 0 or ty < 0 or tx >= COLS or ty >= ROWS:
            return False
        ch = self.grid[ty][tx]
        if ch == "=":
            return True
        if ch == "~":                          # puente fantasma: solido solo si esta activo
            return self.ghost_t.get((tx, ty), 0.0) > 0.0
        return False

    def blocks(self, tx, ty, is_player):
        if tx < 0 or ty < 0 or tx >= COLS or ty >= ROWS:
            return True
        ch = self.grid[ty][tx]
        if ch == "E":
            return not (is_player and self.door_open)
        return ch in "#T"

    # --- capa estatica pre-renderizada
    def bake(self):
        T = self.tex
        surf = pygame.Surface((MAP_W, MAP_H))
        rnd = random.Random(42)
        for y in range(ROWS):
            for x in range(COLS):
                if self.grid[y][x] in "#TE":
                    surf.blit(T.walls[(x * 7 + y * 3) % len(T.walls)], (x * TILE, y * TILE))
                else:
                    surf.blit(T.floors[(x * 5 + y * 11 + rnd.randint(0, 3)) % len(T.floors)],
                              (x * TILE, y * TILE))
        for y in range(ROWS):
            for x in range(COLS):
                px, py = x * TILE, y * TILE
                if not self.is_wall(x, y):
                    if self.is_wall(x, y - 1):
                        surf.blit(T.shadow_top, (px, py))
                    if self.is_wall(x - 1, y):
                        surf.blit(T.shadow_left, (px, py))
                    if self.grid[y][x] == "=":
                        surf.blit(T.shadow_top, (px, py + 6))
                        surf.blit(T.plat, (px, py))
                    elif rnd.random() < 0.09:          # escombros y huesos
                        cx, cy = px + rnd.randint(4, 11), py + rnd.randint(4, 11)
                        if rnd.random() < 0.5:
                            for _ in range(4):
                                surf.set_at((cx + rnd.randint(-2, 2), cy + rnd.randint(-2, 2)), (66, 62, 76))
                            surf.set_at((cx, cy), (118, 114, 130))
                        else:
                            for i in range(-2, 3):
                                surf.set_at((cx + i, cy), (206, 198, 176))
                            surf.set_at((cx - 2, cy - 1), (206, 198, 176))
                            surf.set_at((cx + 2, cy + 1), (206, 198, 176))
                elif y > 0 and not self.is_wall(x, y - 1):
                    surf.blit(T.edge_light, (px, py))
        # rejillas de las corrientes de aire en el suelo
        for (x0, y0, x1, y1) in self.vents:
            for tx in range(x0 // TILE, x1 // TILE):
                gx, gy = tx * TILE, (ROWS - 2) * TILE
                pygame.draw.rect(surf, (30, 36, 50), (gx + 2, gy + 9, 12, 7))
                for i in range(3):
                    pygame.draw.line(surf, (96, 160, 190), (gx + 3 + i * 4, gy + 10), (gx + 3 + i * 4, gy + 14))
        surf.blit(T.edge_fade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)   # bordes difuminados
        return surf.convert()


class Wave:
    __slots__ = ("x", "y", "r", "kind", "color", "max_r", "speed", "rays", "n",
                 "bw", "kk", "after", "bounces")

    def __init__(self, x, y, kind, rays, n, scale=1.0):
        cfg = WAVES[kind]
        self.x, self.y, self.kind = x, y, kind
        self.color = cfg["color"]
        self.max_r = cfg["max_r"] * scale
        self.speed = cfg["speed"]
        self.r = 2.0
        self.rays = rays
        self.n = n
        self.bw = cfg.get("bw", 5.0)         # grosor de cada anillo
        self.kk = cfg.get("k", 5)            # numero de anillos
        self.after = cfg.get("after", 0.0)   # luz que queda detras del frente
        self.bounces = []                    # rebotes pendientes (distancia, x, y)


class Player:
    is_player = True
    hw = 4.5
    h = 14.0

    def __init__(self, x, y):
        self.x, self.y = x, y            # y = pies
        self.vx = self.vy = 0.0
        self.face = 1
        self.on_ground = False
        self.hit_wall = False
        self.hp = MAX_HP
        self.inv = 0.0
        self.stun = 0.0
        self.attack_cd = 0.0
        self.attack_t = 0.0
        self.pulse_cd = 0.0
        self.shoot_cd = 0.0
        self.shoot_t = 0.0
        self.step_acc = 0.0
        self.walk = 0.0
        self.sneak = False
        self.shield = False
        self.coyote = 0.0
        self.jbuf = 0.0
        self.moved_total = 0.0
        self.boost = 1.0                 # impulso del salto diagonal
        self.look = 0.0                  # desplazamiento suavizado del haz frontal
        self.sf = 0.0                    # fraccion de velocidad (0..1)
        self.pogo = 0.0                  # evita cortar el rebote del tajo aereo
        self.air_atk = False
        self.in_vent = False
        self.dash_t = 0.0                # dash secreto (modo TUN)
        self.dash_cd = 0.0
        self.dash_dir = 1
        self.dash_hit = set()
        self.windup = 0.0                # anticipacion del tajo
        self.land_t = 0.0                # compresion al aterrizar
        self.land_pow = 0.0
        self.tilt = 0.0                  # inclinacion del sprite (grados, + = hacia delante)
        self.charging = False            # carga del arco (tecla de disparo mantenida)
        self.charge = 0.0


class Ghoul:
    """Fantasma terrestre: patrulla, te oye, te persigue y salta a las plataformas."""
    is_player = False
    kind = "ghoul"
    hw = 5.0
    h = 14.0

    def __init__(self, x, y, seed):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.hp = 2
        self.rnd = random.Random(seed)
        self.wdir = self.rnd.choice((-1, 1))
        self.wander_t = self.rnd.uniform(0.5, 2.0)
        self.chase_t = 0.0
        self.stun = 0.0
        self.jump_cd = 0.0
        self.on_ground = False
        self.hit_wall = False
        self.phase = self.rnd.random() * 6.28

    def ground_ahead(self, lv, d):
        tx = int((self.x + d * (self.hw + 2)) // TILE)
        ty = int(self.y // TILE)
        return lv.blocks(tx, ty, False) or lv.is_plat(tx, ty)

    def update(self, dt, g):
        lv, p = g.level, g.player
        A = g.aggr
        self.jump_cd -= dt
        self.stun -= dt
        dist = math.hypot(p.x - self.x, p.y - self.y)
        reach = 38 if p.sneak else 95
        if dist < reach and abs(p.y - self.y) < 70 and g.grace <= 0:
            self.chase_t = max(self.chase_t, 2.5)
        if self.stun <= 0 and self.on_ground:
            tvx = 0.0
            if self.chase_t > 0:
                self.chase_t -= dt
                dx = p.x - self.x
                d = 1 if dx > 0 else -1
                self.wdir = d
                if abs(dx) > 3:
                    tvx = d * GHOUL_CHASE * A
                above = self.y - p.y > 14
                below = p.y - self.y > 14
                ahead = self.ground_ahead(lv, d)
                if self.jump_cd <= 0 and abs(dx) > 3:
                    if above and abs(dx) < 44:                       # saltar a la plataforma
                        self.vy, self.jump_cd = -GHOUL_JUMP, 0.9
                    elif self.hit_wall:
                        self.vy, self.jump_cd = -215.0, 0.9
                    elif not ahead and not below and abs(dx) < 80:   # saltar un hueco
                        self.vy, self.jump_cd = -215.0, 0.9
                        tvx = d * GHOUL_CHASE * 1.5 * A
                if not ahead and not below and self.vy == 0:
                    tvx = 0.0                                          # no se tira al vacio
            else:
                self.wander_t -= dt
                if self.wander_t <= 0:
                    self.wander_t = self.rnd.uniform(1.0, 3.0)
                    self.wdir = self.rnd.choice((-1, 0, 1))
                if self.wdir:
                    if self.hit_wall or not self.ground_ahead(lv, self.wdir):
                        self.wdir = -self.wdir
                    tvx = self.wdir * GHOUL_WANDER
            self.vx = tvx if self.vy == 0 else self.vx
        elif self.stun > 0 and self.on_ground:
            self.vx *= 0.85 ** (dt * 60)
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        move_body(lv, self, dt)


class Bat:
    """Murcielago volador: ronda su guarida y se lanza en picado contra el jugador."""
    is_player = False
    kind = "bat"
    hw = 5.0
    h = 9.0

    def __init__(self, cx, cy, seed):
        self.x, self.y = cx, cy + self.h / 2          # y = "pies" (parte baja)
        self.home = (cx, cy)
        self.vx = self.vy = 0.0
        self.hp = 1
        self.rnd = random.Random(seed)
        self.phase = self.rnd.random() * 6.28
        self.t = self.rnd.random() * 6.28
        self.chase_t = 0.0
        self.retreat = 0.0
        self.stun = 0.0

    def update(self, dt, g):
        lv, p = g.level, g.player
        A = g.aggr
        self.t += dt
        cx, cy = self.x, self.y - self.h / 2
        pcx, pcy = p.x, p.y - 8
        dist = math.hypot(pcx - cx, pcy - cy)
        if dist < (30 if p.sneak else 78) and g.grace <= 0:
            self.chase_t = max(self.chase_t, 3.5)
        if self.stun > 0:
            self.stun -= dt
            f = 0.88 ** (dt * 60)
            self.vx *= f
            self.vy *= f
        else:
            wob = 0.0
            if self.retreat > 0:
                self.retreat -= dt
                tx, ty = pcx + math.sin(self.t * 2) * 40, pcy - 48
                speed = BAT_CHASE * A
            elif self.chase_t > 0:
                self.chase_t -= dt
                tx, ty = pcx, pcy
                speed = BAT_CHASE * A
                wob = math.sin(self.t * 7 + self.phase) * 20
            else:
                tx = self.home[0] + math.sin(self.t * 1.3 + self.phase) * 14
                ty = self.home[1] + math.sin(self.t * 2.1 + self.phase) * 8
                speed = BAT_IDLE
            vx, vy = tx - cx, ty - cy
            d = math.hypot(vx, vy) or 1.0
            ux, uy = vx / d, vy / d
            spd = speed if d > 3 else 0.0
            dvx = ux * spd + (-uy) * wob
            dvy = uy * spd + ux * wob
            k = min(1.0, dt * 6)
            self.vx += (dvx - self.vx) * k
            self.vy += (dvy - self.vy) * k
        move_fly(lv, self, dt)


class Skeleton(Ghoul):
    """Esqueleto arquero: te oye, mantiene la distancia y dispara flechas en linea
    recta. Antes de disparar se queda quieto y emite un eco rojo de aviso."""
    kind = "skel"
    hw = 4.5

    def __init__(self, x, y, seed):
        Ghoul.__init__(self, x, y, seed)
        self.shoot_cd = self.rnd.uniform(2.5, 3.5)
        self.aim = 0.0
        self.face = -1
        self.strafe_dir = self.rnd.choice((-1, 1))
        self.strafe_t = self.rnd.uniform(0.5, 1.5)

    def strafe(self, lv, dt):
        """Patrulla lateral: cambia de sentido cada cierto tiempo, ante un muro o un borde."""
        if not self.ground_ahead(lv, 1) and not self.ground_ahead(lv, -1):
            return 0
        self.strafe_t -= dt
        if self.strafe_t <= 0:
            self.strafe_dir = self.rnd.choice((-1, 1))
            self.strafe_t = self.rnd.uniform(0.9, 2.0)
        if self.hit_wall or not self.ground_ahead(lv, self.strafe_dir):
            self.strafe_dir = -self.strafe_dir
            self.strafe_t = self.rnd.uniform(0.9, 2.0)
        return self.strafe_dir

    def update(self, dt, g):
        lv, p = g.level, g.player
        self.stun -= dt
        self.jump_cd -= dt
        self.shoot_cd -= dt
        dx, dy = p.x - self.x, p.y - self.y
        if math.hypot(dx, dy) < (40 if p.sneak else 130) and abs(dy) < 60 and g.grace <= 0:
            self.chase_t = max(self.chase_t, 3.0)
        if self.stun <= 0 and self.on_ground:
            tvx = 0.0
            if self.chase_t > 0:
                self.chase_t -= dt
                d = 1 if dx > 0 else -1
                self.face = d
                if self.aim > 0:
                    self.aim -= dt
                    tvx = self.strafe(lv, dt) * 9.0          # sigue desplazandose despacio al apuntar
                    if self.aim <= 0:
                        g.enemy_shoot(self)
                else:
                    adx = abs(dx)
                    if abs(dy) < 26:                         # a tiro: se mueve mientras combate
                        if adx > 95 and self.ground_ahead(lv, d):
                            tvx = d * 30.0                   # se acerca hasta tener distancia de tiro
                        elif adx < 45 and self.ground_ahead(lv, -d):
                            tvx = -d * 28.0                  # mantiene la distancia
                        else:
                            tvx = self.strafe(lv, dt) * 22.0     # patrulla / esquiva de lado
                        if self.shoot_cd <= 0 and adx < 170:
                            self.aim = 0.45
                            self.shoot_cd = 1.9
                            g.add_wave(self.x, self.y - 8, "aim")
                    else:                                    # no alineado: persigue y salta como un fantasma
                        above = self.y - p.y > 14
                        if adx > 6 and self.ground_ahead(lv, d):
                            tvx = d * 30.0
                        if self.jump_cd <= 0 and adx > 3:
                            if above and adx < 44:
                                self.vy, self.jump_cd = -GHOUL_JUMP, 1.0
                                tvx = d * 30.0
                            elif self.hit_wall:
                                self.vy, self.jump_cd = -215.0, 1.0
            else:
                self.aim = 0.0
                self.wander_t -= dt
                if self.wander_t <= 0:
                    self.wander_t = self.rnd.uniform(1.0, 3.0)
                    self.wdir = self.rnd.choice((-1, 0, 1))
                if self.wdir:
                    if self.hit_wall or not self.ground_ahead(lv, self.wdir):
                        self.wdir = -self.wdir
                    tvx = self.wdir * 20.0
                    self.face = self.wdir
            self.vx = tvx
        elif self.stun > 0 and self.on_ground:
            self.aim = 0.0
            self.vx *= 0.85 ** (dt * 60)
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        move_body(lv, self, dt)


class Arrow:
    """Flecha del jugador ("player") o del esqueleto ("enemy")."""
    kind = "arrow"

    def __init__(self, x, y, vx, vy, owner, grav, power=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.owner, self.grav = owner, grav
        self.life = 2.5
        self.power = power               # super disparo: atraviesa y mata de un golpe
        self.force = False               # True = carga roja de la FUERZA (skin ANAKIN)
        self.hit = set()
        self.t = 0.0
        self.wt = 0.0                    # temporizador de las ondas de luz del super disparo


# ----------------------------------------------------------------------------
#  SONIDO (sintetizado, sin archivos externos)
# ----------------------------------------------------------------------------
def synth(f0, f1, dur, vol=0.3, kind="sine", decay=2.5, noise=0.0, rate=22050):
    n = int(rate * dur)
    buf = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        phase += 2 * math.pi * f / rate
        if kind == "sine":
            v = math.sin(phase)
        elif kind == "square":
            v = 1.0 if math.sin(phase) > 0 else -1.0
        else:
            v = random.uniform(-1, 1)
        if noise:
            v += random.uniform(-1, 1) * noise
        v *= (1 - t) ** decay * vol
        buf.append(int(max(-1.0, min(1.0, v)) * 32767))
    return buf


def to_sound(buf):
    return pygame.mixer.Sound(buffer=buf.tobytes())


def build_sounds():
    s = {}
    s["step"] = to_sound(synth(640, 560, 0.09, 0.16, decay=3))
    s["jump"] = to_sound(synth(260, 520, 0.12, 0.2, decay=2))
    s["slash"] = to_sound(synth(900, 200, 0.16, 0.25, kind="noise", decay=2))
    s["pulse"] = to_sound(synth(220, 900, 0.55, 0.28, decay=1.8))
    s["hit"] = to_sound(synth(190, 80, 0.14, 0.3, kind="square", decay=2))
    s["hurt"] = to_sound(synth(130, 55, 0.28, 0.35, kind="square", decay=1.5, noise=0.4))
    s["block"] = to_sound(synth(520, 340, 0.16, 0.35, kind="square", decay=1.6))
    s["locked"] = to_sound(synth(95, 70, 0.22, 0.4, decay=1.5))
    s["heart"] = to_sound(synth(58, 44, 0.16, 0.6, decay=2))
    s["bow"] = to_sound(synth(620, 240, 0.12, 0.22, kind="square", decay=2.5))
    s["dash"] = to_sound(synth(380, 1250, 0.2, 0.22, kind="noise", decay=2.2))
    sup = array.array("h")
    sup.extend(synth(180, 1500, 0.28, 0.3, kind="noise", decay=1.6))
    sup.extend(synth(1500, 400, 0.22, 0.25, decay=2.0))
    s["super"] = to_sound(sup)
    arp = array.array("h")
    for f in (523, 659, 784, 1046):
        arp.extend(synth(f, f, 0.09, 0.25, decay=1.2))
    s["key"] = to_sound(arp)
    win = array.array("h")
    for f in (392, 523, 659, 784):
        win.extend(synth(f, f, 0.14, 0.28, kind="square", decay=1.0))
    s["win"] = to_sound(win)
    return s


# ----------------------------------------------------------------------------
#  JUEGO
# ----------------------------------------------------------------------------
class Game:
    def __init__(self, sound=True):
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass
        pygame.init()
        info = pygame.display.Info()
        h = info.current_h or 0
        k = 3
        if h > 0:                                  # la arena es mas alta: escala segun la pantalla
            k = max(2, min(5, (h - 110) // LH))
        self.k = k
        self.SW, self.SH = LW * k, LH * k
        self.touch_ui = ("ANDROID_ARGUMENT" in os.environ) or sys.platform == "ios"
        self.win = pygame.display.set_mode((self.SW, self.SH), pygame.RESIZABLE)
        self.screen = pygame.Surface((self.SW, self.SH)).convert()   # superficie virtual
        self.geo = (0, 0, 1.0)                  # (offset x, offset y, escala) de la presentacion
        self.pts = {}                           # dedos / raton activos: id -> (x, y) en pixeles de ventana
        self.prev_ids = set()
        self.prev_btn = set()
        self.btn_held = set()
        self.touch_sneak = False
        self.btn_cache = {}
        pygame.display.set_caption("Echo Knight")
        self.clock = pygame.time.Clock()
        self.canvas = pygame.Surface((LW, LH)).convert()
        self.scaled = pygame.Surface((self.SW, self.SH)).convert()
        self.view = pygame.Surface((MAP_W, MAP_H)).convert()
        self.light = pygame.Surface((MAP_W, MAP_H)).convert()
        self.tmp = pygame.Surface((MAP_W, MAP_H)).convert()
        self.tl = pygame.Surface((MAP_W, MAP_H)).convert()      # luz de antorchas
        self.font = pygame.font.Font(None, 16)
        self.text_cache = {}
        self.tex = Textures()
        self.glow_player = make_radial(GLOW_R, (190, 195, 235), PLAYER_GLOW)
        self.beam = make_beam(BEAM_W, BEAM_H, (185, 212, 240), 0.42)
        self.glow_arrow = make_radial(9, (255, 225, 150), 0.6)
        self.glow_arrow_e = make_radial(8, (255, 110, 80), 0.55)
        self.glow_key = [make_radial(15, (255, 210, 90), s) for s in (0.25, 0.45, 0.7)]
        self.glow_door = make_radial(20, (110, 255, 170), 0.5)
        self.glow_dash = make_radial(14, (120, 215, 255), 0.6)
        self.glow_fxset = {}                                         # luces del sable / FUERZA por skin
        for _nm, _sw in (("vader", False), ("anakin", True)):
            _cc = (lambda c: c[::-1]) if _sw else (lambda c: c)
            self.glow_fxset[_nm] = dict(
                dash=make_radial(14, _cc((255, 50, 36)), 0.7), sword=make_radial(17, _cc((255, 40, 28)), 0.55),
                stab=make_radial(30, _cc((255, 70, 40)), 0.9), force=make_radial(11, _cc((255, 60, 40)), 0.75),
                big=make_radial(30, _cc((255, 45, 32)), 0.95))
        self.glow_super = make_radial(30, (255, 235, 170), 0.95)
        # brillo propio de los monstruos (se suma a la luz: se distingue cada tipo en la oscuridad)
        self.glow_mon = {"ghoul": make_radial(13, (170, 125, 255), 0.34),
                         "skel": make_radial(13, (235, 235, 205), 0.34),
                         "bat": make_radial(11, (255, 130, 200), 0.34)}
        self.vign = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        for i in range(9):                       # solo un MARCO rojo, nada de pantalla roja
            a = int(255 * (1 - i / 9) ** 1.4)
            pygame.draw.rect(self.vign, (235, 25, 25, a), (i, i, MAP_W - 2 * i, MAP_H - 2 * i), 1)
        self.flash = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        self.sounds = {}
        self.muted = not sound
        if sound:
            try:
                self.sounds = build_sounds()
            except Exception:
                self.sounds = {}
        self.fullscreen = False
        self.time = 0.0
        self.state = "menu"
        self.help = False
        self.level_idx = 0
        self.total_time = 0.0
        self.kills = 0
        self.has_shield = False
        self.toast_text = ""
        self.toast_t = 0.0
        self.menu_t = 0.0
        self.shield_warned = False
        self.has_bow = False
        self.tutorial = False
        self.restart_arm = 0.0           # confirmacion de reinicio (pulsar P dos veces)
        self.ghost_hint = False
        self.tun_mode = False            # modo desarrollador (se activa escribiendo "tun")
        self.cheat_buf = ""
        self.anakin_mode = False         # True si hay una skin de FUERZA activa (anakin o darth vader)
        self.skin = None                 # None | "anakin" | "vader"
        self.ak_stab = None              # espada clavada tras el dash: [x, y_suelo, dir, t, t_max]
        self._pdraw = None
        self.menu_level = Level(MENU_ARENA, self.tex)
        self.load_menu()

    # ------------------------------------------------------------ utilidades
    def sfx(self, name):
        if not self.muted and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass

    def toast(self, text, t=3.0):
        self.toast_text, self.toast_t = text, t

    def get_input(self):
        k = pygame.key.get_pressed()
        h = self.btn_held if self.touch_ui else ()
        return dict(
            left=int(k[pygame.K_a] or k[pygame.K_LEFT] or "left" in h),
            right=int(k[pygame.K_d] or k[pygame.K_RIGHT] or "right" in h),
            jump=bool(k[pygame.K_w] or k[pygame.K_UP] or k[pygame.K_z] or "jump" in h),
            shield=bool(k[pygame.K_s] or k[pygame.K_DOWN] or "shield" in h),
            sneak=bool(k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT] or (self.touch_ui and self.touch_sneak)),
        )

    def reset_runtime(self):
        self.waves = []
        self.has_key = False
        self.key_visible = False
        self.chest_open = False
        self.reveal = 0.0
        self.t_level = 0.0
        self.tut = 0
        self.attacks = 0
        self.pulses = 0
        self.jumps = 0
        self.sealed_cd = 0.0
        self.heart_t = 0.0
        self.hurt_flash = 0.0
        self.block_flash = 0.0
        self.danger = 0.0
        self.clear_t = 0.0
        self.arrows = []
        self.torch_fade = 0.0            # 0 = antorchas apagadas, 1 = encendidas
        self.tut_spawned = False
        self.sneak_dist = 0.0
        self.grace = 0.0                 # los monstruos aun no te detectan
        self.aggr = 1.0                  # factor de agresividad (sube tras aparecer)
        self.trail = []                  # estela del dash: [sprite, x, y, vida, vida_max]
        self.sparks = []                 # chispas del dash: [x, y, vx, vy, vida, vida_max, color]
        self.winds = []                  # estelas de viento de las flechas

    # ------------------------------------------------------------ niveles
    def load_menu(self):
        self.level = self.menu_level
        sx, sy = self.level.start
        self.player = Player(sx, sy)
        self.player.on_ground = True
        self.monsters = []
        self.reset_runtime()
        self.menu_t = 0.0

    def start_game(self, tutorial=True):
        self.level_idx = 0
        self.total_time = 0.0
        self.kills = 0
        self.has_shield = False          # escudo y arco se pierden al empezar partida nueva
        self.has_bow = False
        self.shield_warned = False
        self.load_level(-1 if tutorial else 0)

    def load_level(self, idx):
        spec = TUTORIAL_ARENA if idx < 0 else LEVELS[idx]
        self.tutorial = idx < 0
        self.level_idx = idx
        self.level = Level(spec, self.tex)
        sx, sy = self.level.start
        self.player = Player(sx, sy)
        self.monsters = [Ghoul(x, y, idx * 100 + i) for i, (x, y) in enumerate(self.level.ghoul_spawns)]
        self.monsters += [Bat(x, y, idx * 100 + 50 + i) for i, (x, y) in enumerate(self.level.bat_spawns)]
        self.monsters += [Skeleton(x, y, idx * 100 + 80 + i) for i, (x, y) in enumerate(self.level.skel_spawns)]
        self.reset_runtime()
        self.ak_stab = None
        self.restart_arm = 0.0
        self.chest_open = bool(self.level.chest) and (
            self.has_bow if self.level.chest_item == "bow" else self.has_shield)
        self.state = "play"
        self.help = False
        self.add_wave(sx, sy - 8, "attack", 0.75)
        if idx >= 0:
            msg = "Nivel %d: %s. Derrota a TODOS los monstruos para que aparezca la llave." % (idx + 1, self.level.name)
            if self.level.chest and not self.chest_open:
                msg += " Hay un cofre en la sala: pulsa E junto a él."
            if idx == 1:
                msg += " Las CORRIENTES DE AIRE (partículas cian) te elevan sin saltar."
            if idx == 2:
                msg += " Pulsa Q para solidificar los PUENTES FANTASMA durante unos segundos."
            if idx == 5:
                msg += " ¡Cuidado! Los ESQUELETOS ARQUEROS disparan flechas: esquívalas o bloquéalas."
            if idx == 8:
                msg += " Sube en zigzag por la escalera de plataformas."
            if idx == 10:
                msg += " ¡Hay muchos esqueletos! Ahora patrullan y esquivan mientras disparan."
            if idx == 13:
                msg += " ¡La última arena! Usa todo lo aprendido."
            self.toast(msg, 5.0)

    # ------------------------------------------------------------ ondas
    def add_wave(self, x, y, kind, scale=1.0):
        mr = WAVES[kind]["max_r"] * scale
        n = 96 if mr > 200 else (72 if mr > 100 else (36 if kind == "bounce" else 56))
        rays = cast_rays(self.level, x, y, mr, n)
        w = Wave(x, y, kind, rays, n, scale)
        if kind == "pulse":                     # puntos donde el super eco REBOTA en los muros
            cs, sn = trig(n)
            for i in range(0, n, 8):
                dh = rays[i] - 7.0
                if 8 < dh < mr - 8:
                    w.bounces.append((dh, x + cs[i] * (dh - 5), y + sn[i] * (dh - 5)))
            w.bounces.sort()
        self.waves.append(w)
        if len(self.waves) > 40:
            self.waves.pop(0)

    def make_noise(self, x, y, radius):
        for m in self.monsters:
            if math.hypot(m.x - x, m.y - y) < radius:
                m.chase_t = max(m.chase_t, 4.0)

    def draw_wave(self, w):
        BW, K = w.bw, w.kk
        fade = max(0.0, 1.0 - w.r / w.max_r) ** 0.75
        if fade <= 0.01:
            return
        n, rays = w.n, w.rays
        cs, sn = trig(n)
        x, y, r = w.x, w.y, w.r
        rect = pygame.Rect(int(x - r - 10), int(y - r - 10), int(2 * r + 20), int(2 * r + 20)).clip(self.tmp.get_rect())
        if rect.w <= 0 or rect.h <= 0:
            return
        self.tmp.fill((0, 0, 0), rect)
        cr, cg, cb = w.color
        poly = pygame.draw.polygon
        tmp = self.tmp
        for k in range(K - 1, -1, -1):
            ro = r - k * BW
            if ro <= 0:
                continue
            ri = max(0.0, ro - BW)
            inten = fade * (1 - k / K) ** 1.4
            col = (int(cr * inten), int(cg * inten), int(cb * inten))
            for i in range(n):
                j = i + 1 if i + 1 < n else 0
                d0, d1 = rays[i], rays[j]
                o0 = ro if ro < d0 else d0
                o1 = ro if ro < d1 else d1
                i0 = ri if ri < d0 else d0
                i1 = ri if ri < d1 else d1
                if o0 <= i0 and o1 <= i1:
                    continue
                poly(tmp, col, ((x + cs[i] * i0, y + sn[i] * i0), (x + cs[i] * o0, y + sn[i] * o0),
                                (x + cs[j] * o1, y + sn[j] * o1), (x + cs[j] * i1, y + sn[j] * i1)))
        if w.after > 0:                          # la sala sigue iluminada tras el frente
            ro = r - K * BW
            if ro > 0:
                inten = fade * w.after
                col = (int(cr * inten), int(cg * inten), int(cb * inten))
                for i in range(n):
                    j = i + 1 if i + 1 < n else 0
                    o0 = ro if ro < rays[i] else rays[i]
                    o1 = ro if ro < rays[j] else rays[j]
                    poly(tmp, col, ((x, y), (x + cs[i] * o0, y + sn[i] * o0),
                                    (x + cs[j] * o1, y + sn[j] * o1)))
        self.light.blit(tmp, rect.topleft, rect, special_flags=pygame.BLEND_RGB_MAX)

    # ------------------------------------------------------------ acciones
    def check_cleared(self):
        """La llave solo aparece cuando no queda ningun monstruo."""
        lv = self.level
        if self.monsters or self.key_visible or not lv.key:
            return
        if self.tutorial and not self.tut_spawned:
            return
        self.key_visible = True
        self.add_wave(lv.key[0], lv.key[1], "key", 1.2)
        self.sfx("key")
        self.toast("¡Todos los monstruos han caído! Ha aparecido la llave dorada.", 3.5)

    def do_attack(self):
        """Inicia el ataque: primero la espada retrocede (anticipacion) y el tajo
        se ejecuta en perform_attack cuando termina WINDUP_T."""
        p = self.player
        if (p.attack_cd > 0 or p.shield or p.stun > 0 or p.dash_t > 0 or p.windup > 0
                or self.state != "play"):
            return
        p.attack_cd = ATTACK_COOLDOWN
        p.windup = WINDUP_T
        p.air_atk = not p.on_ground

    def perform_attack(self):
        p = self.player
        p.attack_t = 0.16
        self.attacks += 1
        air = not p.on_ground
        p.air_atk = air                          # tajo aereo: diagonal hacia abajo
        self.add_wave(p.x, p.y - 8, "attack")
        self.sfx("slash")
        self.make_noise(p.x, p.y, 100)
        if p.face > 0:
            x0, x1 = p.x - 4, p.x + ATTACK_RANGE
        else:
            x0, x1 = p.x - ATTACK_RANGE, p.x + 4
        y0, y1 = (p.y - 14, p.y + 14) if air else (p.y - 22, p.y + 2)
        hits = 0
        for m in self.monsters[:]:
            if m.x + m.hw < x0 or m.x - m.hw > x1 or m.y < y0 or m.y - m.h > y1:
                continue
            self.damage_monster(m, p.face)
            hits += 1
        if air and hits:                         # rebote al golpear desde el aire
            p.vy = -190.0
            p.pogo = 0.2
            p.on_ground = False
        self.check_cleared()

    # --- skins secretas: ANAKIN (azul) y DARTH VADER (rojo)
    def tc(self, c):
        """Color de un efecto segun la skin: rojo (DARTH VADER) o azul (ANAKIN, canales R y B cambiados)."""
        return (c[2], c[1], c[0]) if self.skin == "anakin" else c

    def fxk(self, name):
        """Nombre de la onda segun la skin (las de ANAKIN terminan en _b)."""
        return name + "_b" if self.skin == "anakin" else name

    def hand_pos(self, p):
        """Mano con la que se usa la FUERZA (de aqui sale la carga)."""
        if self.skin == "vader":
            return p.x + p.face * 11.0, p.y - 12.0
        return p.x + p.face * 9.0, p.y - 5.5

    def sword_hand(self, p):
        """Mano que empuna el sable."""
        if self.skin == "vader":
            return p.x + p.face * 6.0, p.y - 7.0
        return p.x + p.face * 5.0, p.y - 5.5

    def set_skin(self, skin):
        p = self.player
        p.charging, p.charge = False, 0.0
        self.ak_stab = None
        self.trail = []
        self.skin = None if self.skin == skin else skin
        self.anakin_mode = self.skin is not None
        self.add_wave(p.x, p.y - 8, self.fxk("dash_red") if self.anakin_mode else "dash", 1.4)
        self.sfx("key")
        if self.skin == "anakin":
            self.toast("SKIN ANAKIN: sable azul, capa y DASH con R. Escribe anakin otra vez para quitarla "
                       "(o darth vader para el otro personaje).", 3.8)
        elif self.skin == "vader":
            self.toast("DARTH VADER: sable rojo, capa y DASH con R. Escribe darth vader otra vez para quitarlo.", 3.8)
        else:
            self.toast("Skin desactivada.", 2.5)

    # --- modo TUN: palabra secreta + dash con estela
    def feed_secret(self, ch):
        """Detecta la palabra secreta "tun" escrita durante la partida."""
        ch = ch.lower()
        if len(ch) != 1 or not ch.isalpha():
            return
        self.cheat_buf = (self.cheat_buf + ch)[-12:]
        for word, skin in (("anakin", "anakin"), ("darthvader", "vader")):
            if self.cheat_buf.endswith(word):
                self.cheat_buf = ""
                self.set_skin(skin)
                return
        if self.cheat_buf[-3:] == "tun":
            self.cheat_buf = ""
            self.tun_mode = not self.tun_mode
            p = self.player
            self.add_wave(p.x, p.y - 8, "dash", 1.4)
            self.sfx("key")
            self.toast("MODO TUN activado: pulsa R para hacer el DASH." if self.tun_mode
                       else "Modo TUN desactivado.", 3.0)

    def do_dash(self):
        p = self.player
        if (not (self.tun_mode or self.anakin_mode) or self.state != "play" or p.dash_cd > 0
                or p.dash_t > 0 or p.stun > 0 or p.windup > 0):
            return
        inp = self.get_input()
        d = inp["right"] - inp["left"]
        p.dash_dir = d if d else p.face
        p.face = p.dash_dir
        p.dash_t = DASH_TIME
        p.dash_cd = DASH_COOLDOWN
        p.dash_hit = set()
        p.vy = 0.0
        p.boost = 1.0
        self.ak_stab = None
        self.add_wave(p.x, p.y - 8, self.fxk("dash_red") if self.anakin_mode else "dash")
        self.sfx("dash")
        self.make_noise(p.x, p.y, 70)
        for _ in range(14):                      # rafaga de chispas al arrancar
            a = random.uniform(-0.9, 0.9)
            sp = random.uniform(40.0, 130.0)
            life = random.uniform(0.25, 0.5)
            self.sparks.append([p.x - p.dash_dir * 4, p.y - random.uniform(2.0, 13.0),
                                -p.dash_dir * sp * math.cos(a), -sp * math.sin(a) * 0.8,
                                life, life, self.tc(random.choice(((255, 200, 150), (255, 90, 50), (255, 255, 255))))
                                if self.anakin_mode else
                                random.choice(((190, 240, 255), (130, 215, 255), (255, 255, 255)))])

    def dash_trail(self, p):
        """Deja una imagen residual (silueta cian) del caballero en cada fotograma del dash."""
        spr, bx, by = self.player_sprite(p)
        t = spr.copy()
        t.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)      # conserva solo el alfa
        t.fill(self.tc((255, 50, 36)) + (0,) if self.anakin_mode else (140, 225, 255, 0),
               special_flags=pygame.BLEND_RGBA_ADD)                        # tinte cian (rojo / azul segun la skin)
        self.trail.append([t, bx, by, 0.30, 0.30])
        if len(self.trail) > 24:
            self.trail.pop(0)
        for _ in range(2):
            life = random.uniform(0.2, 0.4)
            self.sparks.append([p.x - p.dash_dir * random.uniform(3, 8), p.y - random.uniform(1.0, 14.0),
                                -p.dash_dir * random.uniform(10, 40), random.uniform(-25, 10),
                                life, life, self.tc((255, 110, 70)) if self.anakin_mode else (170, 235, 255)])

    def ak_stab_start(self, p):
        """Fin del dash en modo ANAKIN: clava la espada en el suelo con una explosion de brasas."""
        d = p.dash_dir
        sx = p.x + d * 13
        gy = p.y                                 # el dash no tiene gravedad: sigue a ras de suelo
        self.ak_stab = [sx, gy, d, 0.55, 0.55]
        self.add_wave(sx, gy - 3, self.fxk("stab"), 1.0)
        self.make_noise(p.x, p.y, 60)
        for _ in range(26):
            a = random.uniform(-2.9, -0.25)
            sp = random.uniform(35.0, 120.0)
            life = random.uniform(0.3, 0.7)
            self.sparks.append([sx, gy - 1, math.cos(a) * sp, math.sin(a) * sp, life, life,
                                self.tc(random.choice(((255, 220, 160), (255, 90, 50), (255, 40, 30), (255, 150, 60))))])

    def update_fx(self, dt):
        if self.ak_stab:
            self.ak_stab[3] -= dt
            if self.ak_stab[3] <= 0:
                self.ak_stab = None
        for tr in self.trail:
            tr[3] -= dt
        self.trail = [tr for tr in self.trail if tr[3] > 0]
        for w in self.winds:
            w[4] -= dt
        self.winds = [w for w in self.winds if w[4] > 0]
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 120.0 * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]

    def do_pulse(self):
        p = self.player
        if p.pulse_cd > 0 or self.state != "play":
            return
        p.pulse_cd = PULSE_COOLDOWN
        self.pulses += 1
        self.add_wave(p.x, p.y - 8, "pulse")
        self.sfx("pulse")
        self.make_noise(p.x, p.y, 260)
        woke = False                             # el super eco solidifica los puentes fantasma
        for cell in self.level.ghost_cells:
            cx, cy = cell[0] * TILE + 8, cell[1] * TILE + 3
            if math.hypot(p.x - cx, (p.y - 8) - cy) < 300:
                self.level.ghost_t[cell] = 7.0
                woke = True
        if woke and not self.ghost_hint:
            self.ghost_hint = True
            self.toast("¡Los puentes fantasma se solidifican unos segundos!", 3.0)

    def damage_monster(self, m, dirn, kill=False):
        m.hp = 0 if kill else m.hp - 1
        m.vx = dirn * 130
        m.vy = -30 if m.kind == "bat" else -80
        m.stun = 0.35
        m.chase_t = 4.0
        self.sfx("hit")
        self.add_wave(m.x, m.y - m.h / 2, "hurt")
        if m.hp <= 0:
            if m in self.monsters:
                self.monsters.remove(m)
            if not self.tutorial:
                self.kills += 1
            self.add_wave(m.x, m.y - m.h / 2, "death")
            self.check_cleared()

    def start_charge(self):
        """Pulsar el disparo empieza a cargar el arco; al soltar se dispara (ver release_fire)."""
        p = self.player
        if (self.has_bow or self.anakin_mode) and self.state == "play" and not p.charging:
            p.charging = True
            p.charge = 0.0

    def release_fire(self):
        p = self.player
        was, c = p.charging, p.charge
        p.charging, p.charge = False, 0.0
        if was and self.state == "play" and not self.help:
            self.do_shoot(c)

    def do_shoot(self, charge=0.0):
        p = self.player
        if (not (self.has_bow or self.anakin_mode) or self.state != "play" or p.shoot_cd > 0
                or p.shield or p.stun > 0):
            return
        force = self.anakin_mode                          # skin ANAKIN: la FUERZA reemplaza al arco
        if force:
            bx, by = self.hand_pos(p)                     # mano extendida
        else:
            bx, by = p.x + p.face * 6, p.y - 9
        if charge >= SUPER_CHARGE_T:                      # SUPER DISPARO cargado
            p.shoot_cd, p.shoot_t = BOW_COOLDOWN * 1.8, 0.3
            a = Arrow(bx, by, p.face * SUPER_SPEED, 0.0, "player", 0.0, power=True)
            a.life = 1.6
            a.force = force
            self.arrows.append(a)
            self.add_wave(bx, by, self.fxk("fsuperhit") if force else "superhit", 0.8)
            self.sfx("super")
            self.make_noise(p.x, p.y, 140)
            for _ in range(20):
                ang = random.uniform(-0.7, 0.7)
                sp = random.uniform(60.0, 190.0)
                life = random.uniform(0.2, 0.45)
                self.sparks.append([bx, by + random.uniform(-3, 3), p.face * sp * math.cos(ang),
                                    sp * math.sin(ang), life, life,
                                    self.tc(random.choice(((255, 90, 60), (255, 40, 30), (255, 210, 190))))
                                    if force else (255, 236, 170)])
            return
        p.shoot_cd, p.shoot_t = BOW_COOLDOWN, 0.18
        a = Arrow(bx, by, p.face * ARROW_SPEED, -14.0, "player", ARROW_GRAV)
        a.force = force
        self.arrows.append(a)
        self.add_wave(bx, by, self.fxk("fshot") if force else "shot")
        self.sfx("bow")
        self.make_noise(p.x, p.y, 50)

    def arrow_fx(self, a, px, py, dt):
        """Estela de viento de las flechas: cinta que se desvanece + remolinos de particulas."""
        sup = a.power
        life = 0.55 if sup else 0.24
        if a.force:
            col = self.tc((255, 60, 44) if sup else (255, 110, 80))
        elif sup:
            col = (255, 236, 170)
        else:
            col = (235, 245, 255) if a.owner == "player" else (255, 130, 100)
        self.winds.append([px, py, a.x, a.y, life, life, col, 3 if sup else 1, sup])
        if len(self.winds) > 160:
            del self.winds[:len(self.winds) - 160]
        ln = math.hypot(a.vx, a.vy) or 1.0
        nx, ny = -a.vy / ln, a.vx / ln
        for _ in range(3 if sup else 1):
            off = random.uniform(-3.0, 3.0) * (2.0 if sup else 1.0)
            l2 = random.uniform(0.18, 0.4)
            self.sparks.append([a.x + nx * off, a.y + ny * off,
                                -a.vx * 0.08 + nx * off * 4, -a.vy * 0.08 + ny * off * 4 - 6,
                                l2, l2, col])
        if sup:                                           # el super disparo ilumina todo su recorrido
            a.wt -= dt
            if a.wt <= 0:
                a.wt = 0.07
                self.add_wave(a.x, a.y, self.fxk("fsuperlight") if a.force else "superlight")

    def enemy_shoot(self, m):
        self.arrows.append(Arrow(m.x + m.face * 7, m.y - 9, m.face * 150.0, 0.0, "enemy", 0.0))
        self.sfx("bow")

    def update_arrows(self, dt):
        lv, p = self.level, self.player
        for a in self.arrows[:]:
            px, py = a.x, a.y
            a.life -= dt
            a.t += dt
            steps = max(1, int(math.ceil(math.hypot(a.vx, a.vy) * dt / 6.0)))   # subpasos: no atraviesa muros
            sdt = dt / steps
            wall = False
            for _ in range(steps):
                a.x += a.vx * sdt
                a.y += a.vy * sdt
                a.vy += a.grav * sdt
                if lv.is_wall(int(a.x // TILE), int(a.y // TILE)):
                    wall = True
                    break
            self.arrow_fx(a, px, py, dt)
            if a.life <= 0 or wall:
                self.arrows.remove(a)
                if a.power and wall:
                    self.add_wave(px, py, self.fxk("fsuperhit") if a.force else "superhit")
                elif a.life > 0:
                    self.add_wave(px, py, self.fxk("farrowhit") if a.force else "arrowhit")
                continue
            if a.owner == "player":
                lo, hi = min(px, a.x), max(px, a.x)
                for m in self.monsters[:]:
                    if lo - m.hw - 2 < m.x < hi + m.hw + 2 and m.y - m.h - 2 < a.y < m.y + 2:
                        dirn = 1 if a.vx > 0 else -1
                        if a.power:                       # atraviesa y mata de un solo golpe
                            if id(m) in a.hit:
                                continue
                            a.hit.add(id(m))
                            self.add_wave(m.x, m.y - m.h / 2, self.fxk("fsuperhit") if a.force else "superhit", 0.6)
                            self.damage_monster(m, dirn, kill=True)
                        else:
                            self.arrows.remove(a)
                            self.damage_monster(m, dirn)
                            break
            elif p.inv <= 0 and p.dash_t <= 0 and abs(a.x - p.x) < p.hw + 2 and p.y - p.h - 1 < a.y < p.y + 1:
                self.arrows.remove(a)
                self.hurt_player(a)
                if self.state != "play":
                    return

    def tut_advance(self):
        self.tut += 1
        self.attacks = self.pulses = self.jumps = 0
        self.sneak_dist = 0.0
        if self.tut == 5 and not self.tut_spawned:       # aparece el fantasma de practica
            self.tut_spawned = True
            gx, gy = (14 + DX) * TILE + 8, (ROWS - 1) * TILE
            self.monsters.append(Ghoul(gx, gy, 999))
            self.add_wave(gx, gy - 8, "death")

    def near_chest(self):
        c = self.level.chest
        p = self.player
        return bool(c) and not self.chest_open and abs(p.x - c[0]) < 16 and abs(p.y - c[1]) < 20

    def try_open_chest(self):
        if self.state != "play" or not self.near_chest():
            return
        c = self.level.chest
        self.chest_open = True
        self.add_wave(c[0], c[1] - 8, "key", 1.1)
        self.sfx("key")
        if self.level.chest_item == "bow":
            self.has_bow = True
            self.toast("¡Cofre abierto! Obtienes el ARCO: toca F o C para disparar; mantén pulsado "
                       "y suelta para un SÚPER DISPARO que cruza el mapa y mata de un golpe.", 6.0)
        else:
            self.has_shield = True
            self.toast("¡Cofre abierto! Obtienes el ESCUDO: mantén S o FLECHA abajo para bloquear "
                       "(un bloqueo perfecto lanza un eco azul).", 5.0)

    def try_restart(self):
        """Reiniciar el nivel exige pulsar P dos veces (evita pulsaciones accidentales)."""
        if self.restart_arm > 0:
            self.restart_arm = 0.0
            self.load_level(self.level_idx)
        else:
            self.restart_arm = 2.0
            self.toast("¿Reiniciar el nivel? Pulsa P otra vez para confirmar.", 2.0)

    def hurt_player(self, m):
        p = self.player
        front = (m.x - p.x) * p.face >= -2
        if m.kind == "bat":
            m.retreat = 1.0
        d = 1 if m.x >= p.x else -1
        if p.shield and front:                                  # BLOQUEO
            p.inv = 0.4
            m.stun = 0.45
            m.vx = d * 140
            m.vy = -40 if m.kind == "bat" else -60
            p.vx -= d * 50
            self.block_flash = 0.15
            self.add_wave(p.x, p.y - 8, "block")
            self.sfx("block")
            return
        p.hp -= 1
        p.inv = 1.3
        p.stun = 0.25
        p.vx = -d * 120
        p.vy = -150
        p.on_ground = False
        self.hurt_flash = 0.5
        self.add_wave(p.x, p.y - 8, "hurt")
        self.sfx("hurt")
        if p.hp <= 0:
            self.state = "dead"

    # ------------------------------------------------------------ eventos
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.toast("Pantalla completa: %s  (F11)" % ("ACTIVADA" if self.fullscreen else "desactivada"), 2.0)
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            flags = pygame.FULLSCREEN if self.fullscreen else 0
            self.win = pygame.display.set_mode((self.SW, self.SH), flags | pygame.RESIZABLE)

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if self.pointer_event(e):
                continue
            if e.type == pygame.KEYUP:
                if e.key in (pygame.K_f, pygame.K_c):
                    self.release_fire()                  # soltar = disparar (normal o super)
                continue
            if e.type != pygame.KEYDOWN:
                continue
            key = e.key
            if key == pygame.K_F11:
                self.toggle_fullscreen()
                continue
            if key == pygame.K_m:
                self.muted = not self.muted
                continue
            if key == pygame.K_F10:                      # mostrar / ocultar controles tactiles
                self.touch_ui = not self.touch_ui
                continue
            st = self.state
            if st == "menu":
                if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self.start_game(True)
                elif key == pygame.K_n:
                    self.start_game(False)
                elif key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif st == "play":
                if e.unicode:                            # comando secreto: se lee SIEMPRE, incluso con la ayuda abierta
                    skin0, tun0 = self.skin, self.tun_mode
                    self.feed_secret(e.unicode)
                    if (self.skin, self.tun_mode) != (skin0, tun0):
                        self.help = False                # la "h" de "darth" abre la ayuda: se cierra al completar
                        continue
                if self.help:
                    if key in (pygame.K_h, pygame.K_ESCAPE, pygame.K_RETURN):
                        self.help = False
                    continue
                if key in (pygame.K_SPACE, pygame.K_x):
                    self.do_attack()
                elif key in (pygame.K_w, pygame.K_UP, pygame.K_z):
                    self.player.jbuf = 0.12
                elif key == pygame.K_q:
                    self.do_pulse()
                elif key in (pygame.K_f, pygame.K_c):
                    self.start_charge()
                elif key == pygame.K_r:
                    self.do_dash()
                elif key == pygame.K_e:
                    self.try_open_chest()
                elif key in (pygame.K_s, pygame.K_DOWN):
                    if not self.has_shield and self.level_idx >= 1 and not self.shield_warned:
                        self.shield_warned = True
                        self.toast("Todavía no tienes escudo. Busca el cofre de esta sala.", 3.0)
                elif key == pygame.K_h:
                    self.help = True
                elif key == pygame.K_p:
                    self.try_restart()
                elif key == pygame.K_ESCAPE:
                    self.state = "paused"
            elif st == "paused":
                if key == pygame.K_ESCAPE:
                    self.state = "play"
                elif key == pygame.K_p:
                    self.try_restart()
                elif key == pygame.K_h:
                    self.state = "play"
                    self.help = True
            elif st == "dead":
                if key in (pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.load_level(self.level_idx)
                elif key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.load_menu()
            elif st == "victory":
                if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    self.state = "menu"
                    self.load_menu()
        self.process_touch()

    # ------------------------------------------------------------ pantalla adaptable + tactil
    def fit(self):
        """Adapta la escala interna al tamano actual de la ventana / pantalla."""
        w, h = self.win.get_size()
        k = max(2, min(6, int(min(w / LW, h / LH) + 0.5)))
        if k != self.k:
            self.k = k
            self.SW, self.SH = LW * k, LH * k
            self.screen = pygame.Surface((self.SW, self.SH)).convert()
            self.scaled = pygame.Surface((self.SW, self.SH)).convert()
            self.text_cache.clear()

    def present(self):
        """Escala la imagen virtual a la ventana conservando proporcion (barras negras) y pinta los controles."""
        w, h = self.win.get_size()
        s = min(w / self.SW, h / self.SH)
        nw, nh = max(1, int(self.SW * s)), max(1, int(self.SH * s))
        ox, oy = (w - nw) // 2, (h - nh) // 2
        self.geo = (ox, oy, s)
        self.win.fill((0, 0, 0))
        if (nw, nh) == (self.SW, self.SH):
            self.win.blit(self.screen, (ox, oy))
        else:
            self.win.blit(pygame.transform.scale(self.screen, (nw, nh)), (ox, oy))
        if self.touch_ui and self.state == "play" and not self.help:
            self.draw_touch()
        pygame.display.flip()

    def to_virtual(self, x, y):
        ox, oy, s = self.geo
        return (x - ox) / s, (y - oy) / s

    def pointer_event(self, e):
        t = e.type
        FD, FM, FU = (getattr(pygame, n, -1) for n in ("FINGERDOWN", "FINGERMOTION", "FINGERUP"))
        if t in (FD, FM):
            w, h = self.win.get_size()
            self.pts[e.finger_id] = (e.x * w, e.y * h)
            self.touch_ui = True
            return True
        if t == FU:
            self.pts.pop(e.finger_id, None)
            return True
        mouse = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP)
        if t in mouse and getattr(e, "touch", False):      # raton sintetico del tactil: ya lo cubren los FINGER
            return True
        if t == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.pts["m"] = e.pos
            return True
        if t == pygame.MOUSEMOTION and "m" in self.pts:
            self.pts["m"] = e.pos
            return True
        if t == pygame.MOUSEBUTTONUP and e.button == 1:
            self.pts.pop("m", None)
            return True
        if t == pygame.VIDEORESIZE and pygame.version.vernum[0] < 2:
            self.win = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            return True
        return False

    def touch_buttons(self):
        """Botones tactiles visibles: nombre -> (cx, cy, radio) en pixeles de ventana."""
        w, h = self.win.get_size()
        r = max(26, int(min(w, h) * 0.085))
        B = {"left": (1.5 * r, h - 1.5 * r, r), "right": (4.1 * r, h - 1.5 * r, r),
             "jump": (w - 1.5 * r, h - 1.5 * r, r), "attack": (w - 4.1 * r, h - 1.5 * r, r),
             "pulse": (w - 1.5 * r, h - 4.0 * r, 0.8 * r),
             "sneak": (4.1 * r, h - 4.0 * r, 0.7 * r),
             "pause": (w - 0.9 * r, 0.9 * r, 0.6 * r), "restart": (w - 2.5 * r, 0.9 * r, 0.6 * r)}
        if self.has_bow or self.anakin_mode:
            B["fire"] = (w - 4.1 * r, h - 4.0 * r, 0.8 * r)
        if self.has_shield:
            B["shield"] = (1.5 * r, h - 4.0 * r, 0.8 * r)
        if self.tun_mode or self.anakin_mode:
            B["dash"] = (w - 6.7 * r, h - 1.6 * r, 0.8 * r)
        if self.state == "play" and self.near_chest():
            B["use"] = (w - 6.7 * r, h - 4.0 * r, 0.8 * r)
        return B

    def process_touch(self):
        st = self.state
        new_ids = set(self.pts) - self.prev_ids
        self.prev_ids = set(self.pts)
        cur = set()
        if self.touch_ui:
            for n, (cx, cy, rad) in self.touch_buttons().items():
                if any(math.hypot(x - cx, y - cy) <= rad * 1.25 for (x, y) in self.pts.values()):
                    cur.add(n)
        if st != "play" or self.help:
            self.btn_held = set()
            self.prev_btn = cur
            for i in new_ids:
                if i in self.pts:
                    self.tap(st, *self.pts[i])
            return
        newb, rel = cur - self.prev_btn, self.prev_btn - cur
        self.prev_btn = cur
        self.btn_held = cur
        for n in newb:
            self.btn_down(n)
        for n in rel:
            if n == "fire":
                self.release_fire()

    def tap(self, st, x, y):
        if st == "menu":
            vx, vy = self.to_virtual(x, y)
            self.start_game(not (vy > 0.88 * self.SH and vx < 0.40 * self.SW))
        elif st == "play" and self.help:
            self.help = False
        elif st == "paused":
            self.state = "play"
        elif st == "dead" and self.reveal > 0.6:
            self.load_level(self.level_idx)
        elif st == "victory":
            self.state = "menu"
            self.load_menu()

    def btn_down(self, n):
        p = self.player
        if n == "jump":
            p.jbuf = 0.12
        elif n == "attack":
            self.do_attack()
        elif n == "pulse":
            self.do_pulse()
        elif n == "fire":
            self.start_charge()
        elif n == "sneak":
            self.touch_sneak = not self.touch_sneak
        elif n == "dash":
            self.do_dash()
        elif n == "use":
            self.try_open_chest()
        elif n == "pause":
            self.state = "paused"
        elif n == "restart":
            self.try_restart()

    def btn_surf(self, name, rad, on):
        label = {"attack": "GOLPE", "pulse": "ECO", "shield": "ESC", "sneak": "SIG", "dash": "DASH",
                 "use": "E", "pause": "II", "restart": "REI",
                 "fire": "FUERZA" if self.anakin_mode else "ARCO"}.get(name, "")
        key = (name, rad, on, label)
        if key in self.btn_cache:
            return self.btn_cache[key]
        d = rad * 2
        sf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(sf, (255, 255, 255, 105 if on else 44), (rad, rad), rad)
        pygame.draw.circle(sf, (255, 255, 255, 170), (rad, rad), rad, max(2, rad // 14))
        c = (255, 255, 255, 230)
        if name in ("left", "right", "jump"):
            a = rad * 0.42
            pts = {"left": [(rad - a, rad), (rad + a * 0.6, rad - a), (rad + a * 0.6, rad + a)],
                   "right": [(rad + a, rad), (rad - a * 0.6, rad - a), (rad - a * 0.6, rad + a)],
                   "jump": [(rad, rad - a), (rad - a, rad + a * 0.6), (rad + a, rad + a * 0.6)]}[name]
            pygame.draw.polygon(sf, c, pts)
        else:
            f = pygame.font.Font(None, max(14, int(rad * (0.9 if len(label) < 3 else 0.62))))
            t = f.render(label, True, (255, 255, 255))
            sf.blit(t, (rad - t.get_width() // 2, rad - t.get_height() // 2))
        self.btn_cache[key] = sf
        return sf

    def draw_touch(self):
        for n, (cx, cy, rad) in self.touch_buttons().items():
            on = n in self.btn_held or (n == "sneak" and self.touch_sneak)
            sf = self.btn_surf(n, int(rad), on)
            self.win.blit(sf, (int(cx - rad), int(cy - rad)))

    # ------------------------------------------------------------ actualizacion
    def update(self, dt):
        self.time += dt
        tgt = 1.0 if self.has_key else 0.0        # las antorchas se encienden con la llave
        self.torch_fade += max(-2.0 * dt, min(0.7 * dt, tgt - self.torch_fade))
        if self.toast_t > 0:
            self.toast_t -= dt
        if self.restart_arm > 0:
            self.restart_arm -= dt
        st = self.state
        if st == "menu":
            self.menu_t += dt
            if self.menu_t > 1.9 or not self.waves:
                self.menu_t = 0.0
                self.add_wave(self.player.x, self.player.y - 8, "menu")
            self.update_waves(dt)
        elif st == "play":
            if not self.help:
                self.update_play(dt)
        elif st == "dead":
            self.reveal = min(1.0, self.reveal + dt * 0.7)
            self.update_waves(dt)
            self.update_fx(dt)
            self.hurt_flash = max(0.0, self.hurt_flash - dt)
        elif st == "clear":
            self.reveal = min(0.8, self.reveal + dt * 0.7)
            self.clear_t -= dt
            self.update_waves(dt)
            self.update_fx(dt)
            if self.clear_t <= 0:
                if self.level_idx + 1 < len(LEVELS):
                    if self.tutorial:
                        self.total_time = 0.0
                    self.load_level(self.level_idx + 1)
                else:
                    self.state = "victory"
        elif st == "victory":
            self.reveal = min(1.0, self.reveal + dt * 0.5)

    def update_waves(self, dt):
        for w in self.waves[:]:
            w.r += w.speed * dt
            while w.bounces and w.r >= w.bounces[0][0]:      # el eco rebota en el muro
                _, bx, by = w.bounces.pop(0)
                self.add_wave(bx, by, "bounce")
            if w.r >= w.max_r and w in self.waves:
                self.waves.remove(w)

    def update_play(self, dt):
        inp = self.get_input()
        p, lv = self.player, self.level
        self.t_level += dt
        self.total_time += dt
        # los monstruos tardan en despertar y luego ganan agresividad poco a poco
        if self.tutorial:
            self.grace, self.aggr = 0.0, 1.0
        else:
            self.grace = max(0.0, GRACE_T - self.t_level)
            self.aggr = 0.7 + 0.3 * min(1.0, max(0.0, self.t_level - GRACE_T) / 3.0)
        p.inv = max(0.0, p.inv - dt)
        p.stun = max(0.0, p.stun - dt)
        p.attack_cd = max(0.0, p.attack_cd - dt)
        p.attack_t = max(0.0, p.attack_t - dt)
        p.pulse_cd = max(0.0, p.pulse_cd - dt)
        p.shoot_cd = max(0.0, p.shoot_cd - dt)
        p.shoot_t = max(0.0, p.shoot_t - dt)
        p.jbuf = max(0.0, p.jbuf - dt)
        p.pogo = max(0.0, p.pogo - dt)
        p.land_t = max(0.0, p.land_t - dt)
        p.dash_cd = max(0.0, p.dash_cd - dt)
        dashing = p.dash_t > 0
        p.dash_t = max(0.0, p.dash_t - dt)
        if dashing and p.dash_t <= 0:                    # fin del dash: salida suave
            p.vx = max(-WALK_SPEED * 1.5, min(WALK_SPEED * 1.5, p.vx))
            if self.anakin_mode:
                self.ak_stab_start(p)                    # clava la espada en el suelo
        if p.charging and (self.has_bow or self.anakin_mode):     # carga del arco / FUERZA / super disparo
            was_full = p.charge >= SUPER_CHARGE_T
            p.charge = min(SUPER_CHARGE_T + 0.4, p.charge + dt)
            q = min(1.0, p.charge / SUPER_CHARGE_T)
            if p.charge >= SUPER_CHARGE_T and not was_full:
                self.sfx("key")
                self.add_wave(p.x, p.y - 8, "key", 0.7)
            if q > 0.25 and random.random() < 0.4 + 0.5 * q:      # energia que converge en el arco
                ang = random.uniform(0.0, 6.283)
                cxb, cyb = p.x + p.face * 7, p.y - 9
                if self.anakin_mode:
                    cxb, cyb = self.hand_pos(p)
                l2 = 0.22
                self.sparks.append([cxb + math.cos(ang) * 16, cyb + math.sin(ang) * 16,
                                    -math.cos(ang) * 16 / l2, -math.sin(ang) * 16 / l2,
                                    l2, l2, self.tc((255, 70, 50) if random.random() < 0.7 else (255, 200, 170))
                                    if self.anakin_mode else (255, 232, 165)])
        if p.windup > 0:                                 # anticipacion -> tajo
            if p.stun > 0:
                p.windup = 0.0
            else:
                p.windup -= dt
                if p.windup <= 0:
                    p.windup = 0.0
                    self.perform_attack()
        self.sealed_cd = max(0.0, self.sealed_cd - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.block_flash = max(0.0, self.block_flash - dt)
        if lv.ghost_t:                                   # puentes fantasma: cuenta atras
            lv.ghost_t = {c: t - dt for c, t in lv.ghost_t.items() if t - dt > 0}

        # --- control horizontal
        p.sneak = inp["sneak"]
        p.shield = bool(self.has_shield and inp["shield"] and p.stun <= 0 and p.dash_t <= 0)
        dx = inp["right"] - inp["left"]
        if p.dash_t > 0:                                 # dash: velocidad fija y sin gravedad
            p.vx = p.dash_dir * DASH_SPEED
        elif p.stun <= 0:
            sp = SNEAK_SPEED if p.sneak else WALK_SPEED
            if p.shield:
                sp *= SHIELD_MULT
            sp *= p.boost                                # impulso del salto diagonal
            target = dx * sp
            acc = (1100.0 if dx == 0 else 900.0) if p.on_ground else 520.0
            step = acc * dt
            p.vx += max(-step, min(step, target - p.vx))
            if dx:
                p.face = 1 if dx > 0 else -1
        else:
            p.vx *= 0.9 ** (dt * 60)

        # --- corrientes de aire
        p.in_vent = any(x0 < p.x < x1 and y0 - 4 < p.y <= y1 + 1 for (x0, y0, x1, y1) in lv.vents)

        # --- salto (coyote time + buffer + altura variable + impulso diagonal)
        if p.on_ground:
            p.coyote = 0.1
        else:
            p.coyote = max(0.0, p.coyote - dt)
        if p.jbuf > 0 and p.coyote > 0 and p.stun <= 0:
            p.vy = -JUMP_V
            if dx:                                       # SALTO DIAGONAL: impulso horizontal extra
                p.boost = DIAG_BOOST
                p.vx = dx * (SNEAK_SPEED if p.sneak else WALK_SPEED) * DIAG_BOOST
            p.coyote = p.jbuf = 0.0
            p.dash_t = 0.0                               # saltar cancela el dash
            p.on_ground = False
            self.jumps += 1
            self.sfx("jump")
        if not inp["jump"] and p.vy < -110 and p.pogo <= 0 and not p.in_vent:
            p.vy = -110.0

        # --- fisica
        was_ground = p.on_ground
        p.vy = min(p.vy + GRAVITY * dt, MAX_FALL)
        if p.in_vent and p.vy > -135.0:
            p.vy = max(-135.0, p.vy - 1500.0 * dt)       # la corriente te eleva
        if p.dash_t > 0:
            p.vy = 0.0                                   # el dash flota en linea recta
        fall = p.vy
        ox = p.x
        move_body(lv, p, dt)
        if p.dash_t > 0 and p.hit_wall:                  # el dash se corta contra un muro
            p.dash_t = 0.0
            self.add_wave(p.x + p.dash_dir * 6, p.y - 8, "arrowhit")
        if p.on_ground:
            p.boost = 1.0
        moved = abs(p.x - ox)
        if p.on_ground:
            p.walk += moved
            p.step_acc += moved
            p.moved_total += moved
            if not was_ground and fall > 90:                    # compresion al aterrizar
                p.land_t = LAND_T
                p.land_pow = max(0.35, min(1.0, fall / 300.0))
            if not was_ground and fall > 170:                   # eco de aterrizaje
                self.add_wave(p.x, p.y - 3, "step", 1.4)
                self.sfx("step")
        if p.sneak:
            p.step_acc = 0.0
        elif p.on_ground and p.step_acc >= STEP_DIST:
            p.step_acc -= STEP_DIST
            self.add_wave(p.x, p.y - 3, "step")
            self.sfx("step")

        # --- haz de luz frontal: se adelanta mas cuanto mas rapido corres
        p.sf = min(1.0, abs(p.vx) / WALK_SPEED)
        p.look += (p.face * (10.0 + 16.0 * p.sf) - p.look) * min(1.0, dt * 8.0)

        # --- inclinacion del sprite: hacia delante al correr a maxima velocidad (y en el dash)
        if p.dash_t > 0:
            want = 14.0 * p.dash_dir
        elif p.windup > 0:
            want = -5.0 * p.face                         # se echa hacia atras al armar el tajo
        elif p.on_ground and not p.sneak and p.sf > 0.8 and abs(p.vx) > 1:
            want = 7.0 * (1 if p.vx > 0 else -1) * min(1.0, (p.sf - 0.8) / 0.2)
        else:
            want = 0.0
        p.tilt += (want - p.tilt) * min(1.0, dt * 14.0)
        if p.dash_t > 0:
            self.dash_trail(p)
        self.update_fx(dt)

        # --- monstruos
        for m in self.monsters[:]:
            m.update(dt, self)
            # alerta: el halo aparece cuando el monstruo te ataca y se apaga si lo pierdes
            hunting = (self.tutorial or m.chase_t > 0 or getattr(m, "retreat", 0.0) > 0
                       or getattr(m, "aim", 0.0) > 0)
            m.alert = getattr(m, "alert", 0.0)
            m.alert += ((1.0 if hunting else 0.0) - m.alert) * min(1.0, dt * 6.0)
            if p.dash_t > 0:                             # embestida: golpea una vez a cada monstruo
                if id(m) not in p.dash_hit and boxes_overlap(m, p):
                    p.dash_hit.add(id(m))
                    self.damage_monster(m, p.dash_dir)
                continue
            if p.inv <= 0 and boxes_overlap(m, p):
                self.hurt_player(m)
                if self.state != "play":
                    return

        self.update_arrows(dt)
        if self.state != "play":
            return

        pcx, pcy = p.x, p.y - 7
        # --- llave
        if lv.key and self.key_visible and not self.has_key and math.hypot(pcx - lv.key[0], pcy - lv.key[1]) < 11:
            self.has_key = True
            lv.door_open = True
            self.add_wave(lv.key[0], lv.key[1], "key")
            self.sfx("key")
            self.toast("¡Has tomado la llave! Las antorchas se encienden y la puerta de salida se abre.", 3.5)
        # --- puerta
        if lv.door:
            dcx, dcy = lv.door[0] * TILE + 8, lv.door[1] * TILE + 8
            dd = math.hypot(pcx - dcx, pcy - dcy)
            if not self.has_key and dd < 17 and self.sealed_cd <= 0:
                self.sealed_cd = 2.0
                self.add_wave(p.x, p.y - 8, "locked")
                self.sfx("locked")
                if self.monsters:
                    self.toast("La puerta está sellada. Derrota a todos los monstruos (quedan %d)." % len(self.monsters), 2.8)
                else:
                    self.toast("La puerta está sellada. Encuentra la llave dorada.", 2.8)
            elif self.has_key and dd < 12:
                self.state = "clear"
                self.clear_t = 2.0
                self.sfx("win")
                return

        # --- peligro / latido
        nearest = min((math.hypot(m.x - p.x, (m.y - m.h / 2) - (p.y - 7)) for m in self.monsters), default=999)
        self.danger = max(0.0, 1.0 - nearest / 64.0)
        if self.danger > 0.05:
            self.heart_t -= dt
            if self.heart_t <= 0:
                self.heart_t = 1.1 - 0.7 * self.danger
                self.sfx("heart")

        # --- mini tutorial (sala de practica)
        if self.tutorial:
            if p.sneak and p.on_ground:
                self.sneak_dist += moved
            t = self.tut
            if t == 0 and p.moved_total > 50:
                self.tut_advance()
            elif t == 1 and self.jumps > 0:
                self.tut_advance()
            elif t == 2 and self.sneak_dist > 25:
                self.tut_advance()
            elif t == 3 and self.attacks > 0:
                self.tut_advance()
            elif t == 4 and self.pulses > 0:
                self.tut_advance()
            elif t == 5 and self.key_visible:
                self.tut_advance()
            elif t == 6 and self.has_key:
                self.tut_advance()
        self.update_waves(dt)

    # ------------------------------------------------------------ dibujo
    def knight_frame(self, e):
        """Elige el fotograma del caballero: reposo, caminar (4 pasos), salto o caida."""
        T = self.tex
        A = {"vader": T.knight_anim_vd, "anakin": T.knight_anim_ak}.get(self.skin, T.knight_anim)[
            "right" if e.face > 0 else "left"]
        if self.anakin_mode and (e.charging or e.shoot_t > 0) and "force" in A:
            return A["force"]                                  # usando la FUERZA (brazo extendido)
        if not e.on_ground:
            return A["jump"] if e.vy < 0 else A["fall"]
        if abs(e.vx) > 6 and self.state in ("play", "paused", "clear"):
            return A["walk"][int(e.walk / 5) % 4]
        return A["idle"]

    def rim_sprite(self, spr, color, fill_k, rim_k, gain=1.0):
        """Silueta legible sobre la oscuridad: contorno de color de 1 px + relleno tenue.
        Se devuelve como superficie RGB sobre NEGRO y se dibuja con BLEND_RGB_MAX: el negro
        no cambia nada, asi que es imposible que aparezca un cuadro oscuro alrededor."""
        w, h = spr.get_size()
        tint = spr.copy()
        tint.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        tint.fill(tuple(color) + (0,), special_flags=pygame.BLEND_RGBA_ADD)
        out = pygame.Surface((w + 2, h + 2))
        out.fill((0, 0, 0))
        for ox, oy in ((0, 1), (2, 1), (1, 0), (1, 2)):
            out.blit(tint, (ox, oy))
        q = int(255 * max(0.0, min(1.0, rim_k)))
        out.fill((q, q, q), special_flags=pygame.BLEND_RGB_MULT)
        out.blit(self.faded(spr, 255 * max(0.0, min(1.0, fill_k))), (1, 1))
        g = int(255 * max(0.0, min(1.0, gain)))
        if g < 255:
            out.fill((g, g, g), special_flags=pygame.BLEND_RGB_MULT)
        return out

    def faded(self, spr, alpha):
        """Copia del sprite con el alfa multiplicado: los pixeles transparentes siguen
        siendo 100% transparentes (sin cuadro de fondo)."""
        s = spr.copy()
        s.fill((255, 255, 255, max(0, min(255, int(alpha)))), special_flags=pygame.BLEND_RGBA_MULT)
        return s

    def player_scale(self, e):
        """Estiramiento al elevarse / caer y compresion al aterrizar (sx, sy)."""
        if e.dash_t > 0:
            return 1.35, 0.86
        if e.land_t > 0:
            q = (e.land_t / LAND_T) * e.land_pow
            return 1.0 + 0.18 * q, 1.0 - 0.22 * q
        if not e.on_ground:
            if e.vy < 0:
                q = min(1.0, -e.vy / JUMP_V)
                return 1.0 - 0.10 * q, 1.0 + 0.14 * q
            q = min(1.0, e.vy / MAX_FALL)
            return 1.0 - 0.07 * q, 1.0 + 0.10 * q
        return 1.0, 1.0

    def player_sprite(self, e):
        """Devuelve (superficie, x, y) del caballero con estiramiento, inclinacion y
        retroceso de anticipacion aplicados. Los pies quedan siempre apoyados en e.y."""
        spr = self.knight_frame(e)
        idle = e.on_ground and abs(e.vx) <= 6
        bob = -1 if (idle and int(self.time * 1.6) % 2 == 1) else 0
        sx, sy = self.player_scale(e)
        sw0, sh0 = spr.get_size()
        w, h = max(1, int(round(sw0 * sx))), max(1, int(round(sh0 * sy)))
        if (w, h) != (sw0, sh0):
            spr = pygame.transform.scale(spr, (w, h))
        ox = 0
        if e.windup > 0:                                  # retroceso del cuerpo al armar el tajo
            ox = -int(round(e.face * 1.5 * (1.0 - e.windup / WINDUP_T)))
        bx, by = int(e.x) - w // 2 + ox, int(e.y) - h + bob
        if abs(e.tilt) > 0.8:
            spr = pygame.transform.rotate(spr, -e.tilt)
            r = spr.get_rect(midbottom=(bx + w // 2, by + h))
            bx, by = r.topleft
        return spr, bx, by

    # ------------------------------------------------------------ modo ANAKIN
    def draw_cape(self, v, p):
        """Capa animada: cuelga de los hombros, ondea sola, se estira al correr / dash
        y se levanta con furia mientras cargas la FUERZA. (Negra en Vader, parda en Anakin.)"""
        f = p.face
        vd = self.skin == "vader"
        ch = min(1.0, p.charge / SUPER_CHARGE_T) if p.charging else 0.0
        sp = 1.0 if p.dash_t > 0 else min(1.0, p.sf)
        sp = max(sp, 0.55 * ch)
        ax, ay = (p.x - f * 4.5, p.y - 12.5) if vd else (p.x - f * 3.5, p.y - 8.5)     # hombros
        cl = 13.0 if vd else 10.0
        c_body, c_edge, c_hem = (((14, 14, 20), (74, 74, 90), (40, 40, 52)) if vd
                                 else ((38, 26, 22), (112, 84, 62), (70, 50, 40)))
        if not p.on_ground:
            lift = max(-1.0, min(1.0, -p.vy / 140.0))        # al caer, la capa sube; al saltar, cae
        else:
            lift = 0.0
        lift = max(lift, 0.7 * ch)
        n = 9
        pts = []
        for i in range(n + 1):
            t = i / n
            wave = math.sin(self.time * (7 + 7 * sp + 6 * ch) - t * 5.2) * (0.5 + 2.8 * sp + 0.9 * abs(lift)) * t
            idle = math.sin(self.time * 2.0 - t * 2.2) * 0.6 * t
            back = -f * t * (2.2 + 14.0 * sp)
            cx = ax + back - idle * f
            cy = ay + t * (cl - 6.0 * sp) + wave - lift * 5.5 * t
            pts.append((cx, cy))
        left, right = [], []
        for i, (cx, cy) in enumerate(pts):
            t = i / n
            if i < n:
                dx, dy = pts[i + 1][0] - cx, pts[i + 1][1] - cy
            else:
                dx, dy = cx - pts[i - 1][0], cy - pts[i - 1][1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            w = (1.6 + 3.4 * t) if vd else (1.4 + 3.0 * t)
            left.append((cx + nx * w, cy + ny * w))
            right.append((cx - nx * w, cy - ny * w))
        poly = left + right[::-1]
        pygame.draw.polygon(v, c_body, poly)
        pygame.draw.lines(v, c_edge, False, right, 1)                 # brillo del borde
        pygame.draw.line(v, c_hem, left[-1], right[-1], 1)
        if ch > 0.2:                                                  # destellos al cargar (rojos / azules)
            q = int(150 * ch)
            pygame.draw.lines(v, self.tc((q + 60, 14, 14)), False, left, 1)

    def draw_force_charge(self, v, p):
        """Carga de la FUERZA: orbe que crece en la mano; al llenarse parpadea con halo y rayos."""
        tc = self.tc
        qq = min(1.0, p.charge / SUPER_CHARGE_T)
        full = qq >= 1.0
        hx, hy = self.hand_pos(p)
        cx, cy = int(hx), int(hy)
        rr = 1 + int(5 * qq) + (int(self.time * 16) % 2 if full else 0)
        flick = int(self.time * 12) % 2 == 0
        pygame.draw.circle(v, tc((130, 8, 10)), (cx, cy), rr + 1)
        pygame.draw.circle(v, tc((255, 50, 36)), (cx, cy), rr)
        pygame.draw.circle(v, tc((255, 235, 220)) if (full and flick) else tc((255, 170, 140)), (cx, cy), max(1, rr - 2))
        if qq > 0.35:                                                 # rayos que crepitan hacia la mano
            for i in range(2 + int(3 * qq)):
                a0 = self.time * 9 + i * 2.1
                r0 = rr + 3 + 4 * qq
                x0, y0 = cx + math.cos(a0) * r0, cy + math.sin(a0) * r0
                x1, y1 = cx + math.cos(a0 + 0.4) * (r0 + 3), cy + math.sin(a0 + 0.4) * (r0 + 3)
                pygame.draw.line(v, tc((255, 90, 60)), (x0, y0), (x1, y1), 1)
        if full:                                                      # SUPER CARGA: anillos
            pygame.draw.circle(v, tc((255, 120, 90)), (cx, cy), rr + 3, 1)
            pygame.draw.circle(v, tc((255, 60, 44)), (cx, cy), rr + 6 + int(self.time * 14) % 3, 1)

    def ak_blade(self, v, x0, y0, ang, ln, k=1.0):
        """Sable (rojo en Vader, azul fosforescente en Anakin): empunadura gris, nucleo casi blanco,
        cuerpo de color y halo exterior."""
        tc = self.tc
        ca, sa = math.cos(ang), math.sin(ang)
        hx, hy = x0 + ca * 3.0, y0 + sa * 3.0                      # fin de la empunadura
        pygame.draw.line(v, (30, 30, 36), (x0, y0), (hx, hy), 3)
        pygame.draw.line(v, (128, 128, 140), (x0, y0), (hx, hy), 1)
        ex, ey = x0 + ca * (ln + 3.0), y0 + sa * (ln + 3.0)
        pulse = 0.85 + 0.15 * math.sin(self.time * 14.0)
        pygame.draw.line(v, tc((int(120 * k * pulse), int(8 * k), int(8 * k))), (hx, hy), (ex, ey), 3)
        pygame.draw.line(v, tc((int(255 * k * pulse), int(46 * k), int(34 * k))), (hx, hy), (ex, ey), 2)
        pygame.draw.line(v, tc((255, int(225 * k), int(205 * k))), (hx, hy), (ex, ey), 1)
        return ex, ey

    def draw_ak_sword(self, v, p):
        """Sable emisivo (se dibuja sobre la oscuridad: brilla por si solo)."""
        tc = self.tc
        f = p.face
        hx, hy = self.sword_hand(p)                          # mano
        a_fwd = 0.0 if f > 0 else math.pi
        if self.ak_stab:                                     # espada CLAVADA en el suelo
            sx, gy, d, t, tm = self.ak_stab
            q = max(0.0, min(1.0, t / tm))
            tip = (sx, gy + 1.0)
            dx, dy = (hx - tip[0]), (hy - tip[1])
            dist = math.hypot(dx, dy) or 1.0
            vis = min(12.0, dist) * (0.35 + 0.65 * min(1.0, q * 2.0))   # se va hundiendo al final
            ux, uy = dx / dist, dy / dist
            ex, ey = tip[0] + ux * vis, tip[1] + uy * vis
            pygame.draw.line(v, tc((120, 8, 8)), tip, (ex, ey), 3)
            pygame.draw.line(v, tc((255, 46, 34)), tip, (ex, ey), 2)
            pygame.draw.line(v, tc((255, 215, 190)), tip, (ex, ey), 1)
            pygame.draw.line(v, (60, 56, 66), (ex - uy * 2, ey + ux * 2), (ex + uy * 2, ey - ux * 2), 1)  # guarda
            r = int(2 + (1.0 - q) * 9)                           # onda de choque en el suelo
            pygame.draw.ellipse(v, tc((255, 90, 50)), (int(sx) - r, int(gy) - 1, 2 * r, 3), 1)
            return
        if p.dash_t > 0:                                     # EMBESTIDA: espada al frente como lanza
            bob = math.sin(self.time * 60) * 0.6
            self.ak_blade(v, hx, hy + bob, a_fwd, 19.0)
            return
        if p.windup > 0 or p.attack_t > 0:                   # durante el tajo la hoja sigue el arco
            a0 = 0.0 if p.face > 0 else math.pi
            if p.air_atk:
                a0 += 0.75 * p.face
            if p.windup > 0:
                q = 1.0 - p.windup / WINDUP_T
                ang = a0 - 1.2 - 0.6 * q
            else:
                prog = 1 - p.attack_t / 0.16
                ang = a0 - 1.2 + 2.4 * prog
            self.ak_blade(v, p.x, p.y - 8, ang, 15.0)
            return
        sway = math.sin(self.time * 2.4) * 0.07
        # reposo: hoja hacia arriba y un poco al frente
        ang = (-1.2 + sway) if f > 0 else (-math.pi + 1.2 - sway)
        self.ak_blade(v, hx, hy, ang, 10.0)

    def draw_shield(self, v, p):
        sx = int(p.x + p.face * 6) - 2
        sy = int(p.y) - 13
        flash = self.block_flash > 0
        body = (150, 195, 255) if flash else (92, 108, 150)
        pygame.draw.rect(v, (20, 18, 30), (sx - 1, sy - 1, 6, 13))
        pygame.draw.rect(v, body, (sx, sy, 4, 11))
        pygame.draw.rect(v, (206, 214, 230), (sx, sy, 4, 11), 1)
        pygame.draw.rect(v, GOLD, (sx + 1, sy + 4, 2, 3))

    def render_world(self):
        v, lv, p = self.view, self.level, self.player
        T = self.tex
        self._pdraw = None
        self._mdraw = []
        self._pblink = False
        v.blit(lv.static, (0, 0))
        if lv.door:
            v.blit(T.door_open if lv.door_open else T.door_closed, (lv.door[0] * TILE, lv.door[1] * TILE))
        for cell in lv.ghost_cells:                      # puentes fantasma (solo el contorno si duermen)
            if lv.ghost_t.get(cell, 0.0) <= 0.0:
                v.blit(T.ghost_off, (cell[0] * TILE, cell[1] * TILE))
        for t in lv.torches:
            tx, ty = t
            pygame.draw.rect(v, (74, 52, 34), (tx * TILE + 7, ty * TILE + 8, 2, 5))
            pygame.draw.rect(v, (110, 110, 124), (tx * TILE + 6, ty * TILE + 7, 4, 2))
        if lv.chest:
            c = lv.chest
            v.blit(T.shadow, (c[0] - 6, c[1] - 3))
            v.blit(T.chest_open if self.chest_open else T.chest, (c[0] - 8, c[1] - 14))
        if lv.key and self.key_visible and not self.has_key:
            bob = int(math.sin(self.time * 3) * 1.5)
            v.blit(T.shadow, (lv.key[0] - 6, lv.key[1] + 4))
            v.blit(T.key, (lv.key[0] - 8, lv.key[1] - 8 + bob))
        ents = [(m.y, 0, m) for m in self.monsters] + [(p.y + 0.5, 1, p)]
        ents.sort(key=lambda e: e[0])
        for _, kind, e in ents:
            if kind == 0:
                if e.kind == "ghoul":
                    v.blit(T.shadow, (int(e.x) - 6, int(e.y) - 2))
                    moving = e.on_ground and abs(e.vx) > 4
                    if moving:
                        spr = T.ghoul_anim["walk"][int(self.time * 8 + e.phase) % 4]
                        bob = 0
                    else:
                        spr = T.ghoul_anim["idle"]
                        bob = int(math.sin(self.time * 5 + e.phase) * 1.0) if e.on_ground else 0
                    v.blit(spr, (int(e.x) - 8, int(e.y) - 15 + bob))
                    self._mdraw.append((spr, int(e.x) - 8, int(e.y) - 15 + bob, "ghoul", getattr(e, "alert", 0.0)))
                elif e.kind == "skel":
                    v.blit(T.shadow, (int(e.x) - 6, int(e.y) - 2))
                    A = T.skel_anim["right" if e.face > 0 else "left"]
                    if e.on_ground and abs(e.vx) > 4:
                        spr = A["walk"][int(self.time * 7 + e.phase) % 4]
                    else:
                        spr = A["idle"]
                    v.blit(spr, (int(e.x) - 8, int(e.y) - 15))
                    self._mdraw.append((spr, int(e.x) - 8, int(e.y) - 15, "skel", getattr(e, "alert", 0.0)))
                else:
                    fr = int(self.time * (11 if e.chase_t > 0 else 6) + e.phase) % len(T.bat)
                    v.blit(T.bat[fr], (int(e.x) - 8, int(e.y - e.h / 2) - 8))
                    self._mdraw.append((T.bat[fr], int(e.x) - 8, int(e.y - e.h / 2) - 8, "bat", getattr(e, "alert", 0.0)))
            else:
                if self.state == "dead":
                    continue
                blink = e.inv > 0 and int(self.time * 18) % 2 == 0
                spr, bx, by = self.player_sprite(e)
                if not blink:
                    v.blit(T.shadow, (int(e.x) - 6, int(e.y) - 2))
                    if self.anakin_mode:
                        self.draw_cape(v, e)
                    v.blit(spr, (bx, by))
                self._pdraw = (spr, bx, by)
                self._pblink = blink
                if e.shield:
                    self.draw_shield(v, e)
                if e.shoot_t > 0 and not self.anakin_mode:       # (con la skin ANAKIN no hay arco: es la FUERZA)
                    bx, by = int(e.x + e.face * 7), int(e.y) - 9
                    pygame.draw.lines(v, (176, 120, 60), False,
                                      [(bx, by - 5), (bx + e.face * 3, by), (bx, by + 5)], 2)
                    pygame.draw.line(v, (232, 220, 190), (bx, by - 5), (bx, by + 5))

        for a in self.arrows:
            if a.force:                                  # carga roja de la FUERZA (orbe)
                fl = 0.5 + 0.5 * math.sin(self.time * 30 + a.t * 9)
                rr = (5 if a.power else 2) + (1 if fl > 0.5 else 0)
                pygame.draw.circle(v, self.tc((150, 10, 12)), (int(a.x), int(a.y)), rr + 1)
                pygame.draw.circle(v, self.tc((255, 50, 36)), (int(a.x), int(a.y)), rr)
                pygame.draw.circle(v, self.tc((255, 225, 205)), (int(a.x), int(a.y)), max(1, rr - 2))
                continue
            ln = math.hypot(a.vx, a.vy) or 1.0
            seg = 16 if a.power else 6
            x2, y2 = a.x - a.vx / ln * seg, a.y - a.vy / ln * seg
            col = (240, 226, 190) if a.owner == "player" else (230, 110, 90)
            pygame.draw.line(v, col, (a.x, a.y), (x2, y2), 2 if a.power else 1)
            pygame.draw.circle(v, (255, 255, 255), (int(a.x), int(a.y)), 1)

        # ---- iluminacion
        L = self.light
        a = self.reveal
        L.fill((int(AMBIENT[0] + 110 * a), int(AMBIENT[1] + 100 * a), int(AMBIENT[2] + 120 * a)))
        if self.torch_fade > 0.01:               # antorchas: solo tras tomar la llave
            TL = self.tl
            TL.fill((0, 0, 0))
            for tl in lv.torch_lights:
                f = (math.sin(self.time * 9 + tl["phase"]) + math.sin(self.time * 13.7 + tl["phase"] * 2) + 2) / 4
                TL.blit(tl["surfs"][max(0, min(2, int(f * 3)))], (0, 0), special_flags=pygame.BLEND_RGB_MAX)
            if self.torch_fade < 0.99:
                q = int(255 * self.torch_fade)
                TL.fill((q, q, q), special_flags=pygame.BLEND_RGB_MULT)
            L.blit(TL, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
        for w in self.waves:
            self.draw_wave(w)
        L.blit(self.glow_player, (int(p.x) - GLOW_R, int(p.y - 8) - GLOW_R), special_flags=pygame.BLEND_RGB_MAX)
        G = self.glow_fxset.get(self.skin) or self.glow_fxset["vader"]
        gd = G["dash"] if self.anakin_mode else self.glow_dash
        if p.dash_t > 0:                         # el dash y su estela iluminan en cian (rojo en modo ANAKIN)
            L.blit(gd, (int(p.x) - 14, int(p.y - 8) - 14), special_flags=pygame.BLEND_RGB_MAX)
        for tr in self.trail[-5:]:
            L.blit(gd, (int(tr[1]) + 8 - 14, int(tr[2]) + 8 - 14), special_flags=pygame.BLEND_RGB_MAX)
        if self.anakin_mode and self.state in ("play", "paused") and not (p.charging or p.shoot_t > 0):     # la espada ilumina sola
            fl = 0.8 + 0.2 * math.sin(self.time * 11.0) + 0.1 * math.sin(self.time * 23.0)
            gs = G["sword"].copy()
            q = int(255 * max(0.3, min(1.0, fl)))
            gs.fill((q, q, q), special_flags=pygame.BLEND_RGB_MULT)
            if self.ak_stab:
                bx0, by0 = self.ak_stab[0], self.ak_stab[1] - 5
                qs = max(0.0, min(1.0, self.ak_stab[3] / self.ak_stab[4]))
                gb = G["stab"].copy()
                qq = int(255 * qs)
                gb.fill((qq, qq, qq), special_flags=pygame.BLEND_RGB_MULT)
                L.blit(gb, (int(bx0) - 30, int(by0) - 30), special_flags=pygame.BLEND_RGB_MAX)
                L.blit(gs, (int(bx0) - 17, int(by0) - 17), special_flags=pygame.BLEND_RGB_MAX)
            else:
                shx, shy = self.sword_hand(p)
                L.blit(gs, (int(shx) - 17, int(shy - 5.5) - 17), special_flags=pygame.BLEND_RGB_MAX)
        for m in self.monsters:                  # halo de los monstruos que te estan atacando (alerta)
            al = getattr(m, "alert", 0.0)
            if al < 0.03:
                continue
            gm = self.glow_mon[m.kind]
            if al < 0.97:
                gm = gm.copy()
                q = int(255 * al)
                gm.fill((q, q, q), special_flags=pygame.BLEND_RGB_MULT)
            r = gm.get_width() // 2
            L.blit(gm, (int(m.x) - r, int(m.y - m.h / 2) - r), special_flags=pygame.BLEND_RGB_MAX)
        if p.charging and (self.has_bow or self.anakin_mode) and p.charge > 0.08:      # el arco / la FUERZA cargada brilla
            qq = min(1.0, p.charge / SUPER_CHARGE_T)
            if self.anakin_mode:
                gb = G["big"] if qq >= 1.0 else G["force"]
                rr = gb.get_width() // 2
                fhx, fhy = self.hand_pos(p)
                L.blit(gb, (int(fhx) - rr, int(fhy) - rr), special_flags=pygame.BLEND_RGB_MAX)
            else:
                gb = self.glow_super if qq >= 1.0 else self.glow_arrow
                rr = gb.get_width() // 2
                L.blit(gb, (int(p.x + p.face * 7) - rr, int(p.y) - 9 - rr), special_flags=pygame.BLEND_RGB_MAX)
        if self.state in ("play", "paused"):     # haz frontal: mas intenso y largo al correr
            bm = self.beam.copy()
            q = int(70 + 185 * p.sf)
            bm.fill((q, q, q), special_flags=pygame.BLEND_RGB_MULT)
            L.blit(bm, (int(p.x + p.look) - BEAM_W // 2, int(p.y - 9) - BEAM_H // 2),
                   special_flags=pygame.BLEND_RGB_MAX)
        for ar in self.arrows:
            if ar.force:                         # la carga roja de la FUERZA ilumina su camino
                gf = G["big"] if ar.power else G["force"]
                rr = gf.get_width() // 2
                L.blit(gf, (int(ar.x) - rr, int(ar.y) - rr), special_flags=pygame.BLEND_RGB_MAX)
            elif ar.power:                       # el super disparo emite mucha mas luz
                L.blit(self.glow_super, (int(ar.x) - 30, int(ar.y) - 30), special_flags=pygame.BLEND_RGB_MAX)
            elif ar.owner == "player":
                L.blit(self.glow_arrow, (int(ar.x) - 9, int(ar.y) - 9), special_flags=pygame.BLEND_RGB_MAX)
            else:
                L.blit(self.glow_arrow_e, (int(ar.x) - 8, int(ar.y) - 8), special_flags=pygame.BLEND_RGB_MAX)
        if lv.key and self.key_visible and not self.has_key:
            dk = math.hypot(p.x - lv.key[0], p.y - lv.key[1])
            if dk < 70:
                idx = 2 if dk < 28 else (1 if dk < 48 else 0)
                L.blit(self.glow_key[idx], (lv.key[0] - 15, lv.key[1] - 15), special_flags=pygame.BLEND_RGB_MAX)
        if lv.chest and not self.chest_open:
            dk = math.hypot(p.x - lv.chest[0], p.y - lv.chest[1])
            if dk < 60:
                idx = 2 if dk < 24 else (1 if dk < 40 else 0)
                L.blit(self.glow_key[idx], (lv.chest[0] - 15, lv.chest[1] - 22), special_flags=pygame.BLEND_RGB_MAX)
        if lv.door and lv.door_open:
            dcx, dcy = lv.door[0] * TILE + 8, lv.door[1] * TILE + 8
            if math.hypot(p.x - dcx, p.y - dcy) < 90:
                L.blit(self.glow_door, (dcx - 20, dcy - 20), special_flags=pygame.BLEND_RGB_MAX)
        v.blit(L, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # ---- siluetas de los monstruos: contorno de color propio (fantasma, murcielago, esqueleto)
        rim_col = {"ghoul": (170, 130, 255), "bat": (255, 140, 200), "skel": (235, 235, 210)}
        for spr, mx, my, kd, al in self._mdraw:          # v9.5: SIN silueta fuera de tu luz; solo se ve si te atacan
            if al < 0.05:
                continue
            gain = al
            v.blit(self.rim_sprite(spr, rim_col[kd], 0.28, 0.5, gain), (mx - 1, my - 1),
                   special_flags=pygame.BLEND_RGB_MAX)

        # ---- silueta del caballero: nunca se pierde en la oscuridad
        if self._pdraw and self.state in ("play", "paused", "clear"):
            spr, sx, sy = self._pdraw
            v.blit(self.rim_sprite(spr, self.tc((255, 110, 90)) if self.anakin_mode else (170, 215, 255),
                                   0.40 + 0.25 * self.danger, 0.55,
                                   0.45 if self._pblink else 1.0), (sx - 1, sy - 1),
                   special_flags=pygame.BLEND_RGB_MAX)

        # ---- efectos emisivos (encima de la oscuridad)
        for cell in lv.ghost_cells:                      # puentes fantasma activos
            t = lv.ghost_t.get(cell, 0.0)
            if t > 0 and (t > 1.5 or int(self.time * 10) % 2 == 0):
                v.blit(T.ghost_on, (cell[0] * TILE, cell[1] * TILE))
        for vi, (x0, y0, x1, y1) in enumerate(lv.vents):   # particulas de las corrientes de aire
            hh = y1 - y0
            ww = max(1, int(x1 - x0 - 4))
            for i in range(7):
                px = x0 + 2 + ((i * 37 + vi * 11) % ww)
                py = y1 - ((self.time * 40.0 + i * (hh / 7.0)) % hh)
                pygame.draw.rect(v, (110, 190, 220), (int(px), int(py), 1, 2))
        for t in (lv.torches if self.torch_fade > 0.25 else []):
            tx, ty = t
            ph = int(self.time * 8 + tx * 3 + ty) % 3
            fx, fy = tx * TILE + 8, ty * TILE + 6
            pygame.draw.ellipse(v, (255, 138, 40), (fx - 2, fy - 4 - (ph == 1), 4, 7))
            pygame.draw.ellipse(v, (255, 226, 120), (fx - 1, fy - 2, 2, 4))
        for w in self.winds:                             # estela de viento de las flechas
            f = w[4] / w[5]
            col = (int(w[6][0] * f), int(w[6][1] * f), int(w[6][2] * f))
            pygame.draw.line(v, col, (w[0], w[1]), (w[2], w[3]), w[7] if f > 0.5 else 1)
            if w[8]:                                     # el super disparo arrastra tres cintas
                dim = (int(col[0] * 0.55), int(col[1] * 0.55), int(col[2] * 0.55))
                pygame.draw.line(v, dim, (w[0], w[1] - 3), (w[2], w[3] - 3), 1)
                pygame.draw.line(v, dim, (w[0], w[1] + 3), (w[2], w[3] + 3), 1)
        if p.charging and self.anakin_mode and p.charge > 0.08 and self.state == "play":
            self.draw_force_charge(v, p)
        elif p.charging and self.has_bow and p.charge > 0.08 and self.state == "play":
            qq = min(1.0, p.charge / SUPER_CHARGE_T)
            cbx, cby = int(p.x + p.face * 7), int(p.y) - 9
            full = qq >= 1.0
            rr = 2 + int(6 * qq) + (int(self.time * 16) % 2 if full else 0)
            ccol = (255, 255, 255) if (full and int(self.time * 12) % 2 == 0) else (255, 225, 150)
            pygame.draw.circle(v, ccol, (cbx, cby), rr, 1)
            if full:
                pygame.draw.circle(v, (255, 240, 190), (cbx, cby), rr + 3, 1)
        for tr in self.trail:                            # estela del dash (imagenes residuales)
            if tr[4] - tr[3] < 0.045:
                continue
            a = int(150 * (tr[3] / tr[4]) ** 1.2)
            if a > 4:
                v.blit(self.faded(tr[0], a), (tr[1], tr[2]))
        if p.dash_t > 0 and self.state == "play":        # lineas de velocidad
            d = p.dash_dir
            for i, (oy, ln) in enumerate(((-12, 24), (-8, 36), (-4, 30), (-1, 20))):
                ln *= 0.75 + 0.25 * math.sin(self.time * 55 + i * 1.7)
                x0, y0 = p.x - d * 7, p.y + oy
                xm = x0 - d * ln * 0.45
                c1, c2 = ((self.tc((255, 200, 170)), self.tc((230, 40, 30))) if self.anakin_mode
                      else ((225, 248, 255), (120, 200, 245)))
                pygame.draw.line(v, c1, (x0, y0), (xm, y0), 1)
                pygame.draw.line(v, c2, (xm, y0), (x0 - d * ln, y0), 1)
        for sp in self.sparks:                           # chispas
            f = sp[4] / sp[5]
            col = (int(sp[6][0] * f), int(sp[6][1] * f), int(sp[6][2] * f))
            sz = 2 if f > 0.5 else 1
            pygame.draw.rect(v, col, (int(sp[0]), int(sp[1]), sz, sz))
        if p.windup > 0 and self.state == "play":        # espada echada hacia atras (anticipacion)
            q = 1.0 - p.windup / WINDUP_T
            a0 = 0.0 if p.face > 0 else math.pi
            if p.air_atk:
                a0 += 0.75 * p.face
            ang = a0 - 1.2 - 0.6 * q
            ln = 10.0 + 5.0 * q
            cx0, cy0 = p.x - p.face * 1.5 * q, p.y - 8
            ex, ey = cx0 + math.cos(ang) * ln, cy0 + math.sin(ang) * ln
            pygame.draw.line(v, self.tc((255, 60, 44)) if self.anakin_mode else (236, 242, 255), (cx0, cy0), (ex, ey), 2)
            pygame.draw.line(v, self.tc((255, 170, 140)) if self.anakin_mode else (255, 214, 140), (cx0, cy0), (ex, ey), 1)
        if p.attack_t > 0 and self.state in ("play", "dead"):
            a0 = 0.0 if p.face > 0 else math.pi
            if p.air_atk:                                # tajo aereo: arco diagonal hacia abajo
                a0 += 0.75 * p.face
            prog = 1 - p.attack_t / 0.16
            cy0 = p.y - 8
            pts = [(p.x + math.cos(a0 - 1.2 + 2.4 * prog * (i / 8)) * 16,
                    cy0 + math.sin(a0 - 1.2 + 2.4 * prog * (i / 8)) * 16) for i in range(9)]
            pygame.draw.lines(v, self.tc((255, 60, 44)) if self.anakin_mode else (236, 242, 255), False, pts, 2)
            pygame.draw.lines(v, self.tc((255, 170, 140)) if self.anakin_mode else (255, 214, 140), False,
                              [(x + 0.5 * math.cos(a0), y) for x, y in pts], 1)
        if (self.anakin_mode and self.state in ("play", "paused") and not self._pblink
                and not (p.charging or p.shoot_t > 0)):
            self.draw_ak_sword(v, p)                       # espada roja emisiva (encima de la oscuridad)
        if self.block_flash > 0:
            r = 9 + int((0.15 - self.block_flash) * 40)
            pygame.draw.circle(v, (150, 200, 255), (int(p.x + p.face * 8), int(p.y - 8)), r, 1)

    def draw_hud(self):
        c, T = self.canvas, self.tex
        pygame.draw.rect(c, (30, 26, 40), (0, MAP_H, LW, HUD_H))
        pygame.draw.line(c, (160, 120, 52), (0, MAP_H), (LW, MAP_H))
        pygame.draw.line(c, (82, 60, 34), (0, MAP_H + 1), (LW, MAP_H + 1))
        if self.state == "menu":
            return
        p = self.player
        for i in range(MAX_HP):
            c.blit(T.heart_full if i < p.hp else T.heart_empty, (5 + i * 11, MAP_H + 5))
        c.blit(T.key if self.has_key else T.key_dim, (44, MAP_H + 1))
        if self.has_shield:                      # icono del escudo (solo si lo tienes)
            pygame.draw.rect(c, (20, 18, 30), (63, MAP_H + 3, 8, 11))
            pygame.draw.rect(c, (92, 108, 150), (64, MAP_H + 4, 6, 9))
            pygame.draw.rect(c, (206, 214, 230), (64, MAP_H + 4, 6, 9), 1)
            pygame.draw.rect(c, GOLD, (66, MAP_H + 7, 2, 3))
        ranged = self.has_bow or self.anakin_mode
        if self.anakin_mode:                     # icono de la FUERZA (orbe rojo)
            pygame.draw.circle(c, self.tc((110, 8, 10)), (80, MAP_H + 8), 5)
            pygame.draw.circle(c, self.tc((255, 60, 44)), (80, MAP_H + 8), 4)
            pygame.draw.circle(c, self.tc((255, 225, 205)), (80, MAP_H + 8), 2)
        elif self.has_bow:                       # icono del arco
            pygame.draw.lines(c, (176, 120, 60), False, [(78, MAP_H + 3), (82, MAP_H + 5), (83, MAP_H + 8),
                                                         (82, MAP_H + 11), (78, MAP_H + 13)], 2)
            pygame.draw.line(c, (232, 220, 190), (78, MAP_H + 3), (78, MAP_H + 13))
        if ranged and p.charging and p.charge > 0.05:           # barra de carga del super disparo
            qq = min(1.0, p.charge / SUPER_CHARGE_T)
            pygame.draw.rect(c, (12, 10, 18), (87, MAP_H + 5, 20, 6))
            pygame.draw.rect(c, (255, 255, 255) if (qq >= 1 and int(self.time * 10) % 2 == 0)
                             else (self.tc((255, 70, 50)) if self.anakin_mode else (255, 225, 150)),
                             (88, MAP_H + 6, int(18 * qq), 4))
        bx, by, bw = 112, MAP_H + 5, 36
        pygame.draw.rect(c, (12, 10, 18), (bx - 1, by - 1, bw + 2, 8))
        ready = 1.0 - p.pulse_cd / PULSE_COOLDOWN
        col = CYAN if ready >= 1 else (70, 110, 150)
        pygame.draw.rect(c, col, (bx, by, int(bw * ready), 6))
        if ready >= 1 and int(self.time * 3) % 2 == 0:
            pygame.draw.rect(c, (230, 250, 255), (bx, by, bw, 1))

    # ------------------------------------------------------------ texto
    def text_surf(self, s, size, color):
        key = (s, size, color, self.k)
        if key not in self.text_cache:
            base = self.font.render(s, False, color)
            f = self.k / 2.0 * size
            w, h = base.get_size()
            self.text_cache[key] = pygame.transform.scale(base, (max(1, int(w * f)), max(1, int(h * f))))
        return self.text_cache[key]

    def draw_text(self, s, x, y, size=1.0, color=PARCH, anchor="l", shadow=True, surf=None):
        surf = surf or self.screen
        t = self.text_surf(s, size, color)
        if anchor == "c":
            x -= t.get_width() // 2
        elif anchor == "r":
            x -= t.get_width()
        if shadow:
            surf.blit(self.text_surf(s, size, (10, 8, 14)), (x + self.k // 2 + 1, y + self.k // 2 + 1))
        surf.blit(t, (x, y))
        return t.get_height()

    def line_h(self, size=1.0):
        return int(self.font.get_height() * self.k / 2.0 * size)

    def wrap(self, s, size, max_w):
        f = self.k / 2.0 * size
        lines, cur = [], ""
        for w in s.split(" "):
            t = (cur + " " + w).strip()
            if self.font.size(t)[0] * f <= max_w:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    def draw_panel(self, rect, alpha=205):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        s.fill((14, 12, 22, alpha))
        self.screen.blit(s, rect.topleft)
        pygame.draw.rect(self.screen, (176, 132, 56), rect, self.k // 2 + 1)
        pygame.draw.rect(self.screen, (84, 60, 30), rect.inflate(-self.k * 3, -self.k * 3), 1)

    def draw_key(self, label, x, y):
        f = self.k / 2.0
        t = self.text_surf(label, 1.0, (240, 232, 210))
        w, h = t.get_width() + int(10 * f), t.get_height() + int(6 * f)
        r = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, (24, 20, 34), r.move(0, int(2 * f)))
        pygame.draw.rect(self.screen, (66, 58, 84), r)
        pygame.draw.rect(self.screen, (176, 150, 96), r, max(1, int(f // 2)))
        self.screen.blit(t, (x + int(5 * f), y + int(3 * f)))
        return w, h

    def draw_controls(self, x, y, w):
        f = self.k / 2.0
        lh = self.line_h()
        self.draw_text("CONTROLES", x + w // 2, y, 1.3, GOLD, anchor="c")
        y += int(lh * 1.7)
        keycol = int(w * 0.36)
        for keys, desc in CONTROLS:
            lines = desc.split("\n")
            kx, kh = x, 0
            for kk in keys:
                if kk == "|":
                    self.draw_text("o", kx, y + int(3 * f), 1.0, PARCH)
                    kx += int(12 * f)
                    continue
                kw, kh = self.draw_key(kk, kx, y)
                kx += kw + int(5 * f)
            for i, l in enumerate(lines):
                self.draw_text(l, x + keycol, y + i * lh + (0 if len(lines) > 1 else int(3 * f)), 1.0, PARCH)
            y += max(lh * len(lines), kh) + int(3 * f)
        y += int(3 * f)
        obj = "OBJETIVO: derrota a TODOS los monstruos, toma la LLAVE dorada y cruza la PUERTA de salida."
        for l in self.wrap(obj, 1.0, w):
            self.draw_text(l, x, y, 1.0, GOLD)
            y += lh

    # ------------------------------------------------------------ pantalla
    def draw(self):
        k, st = self.k, self.state
        self.render_world()
        self.canvas.blit(self.view, (0, 0))
        if st in ("play", "paused", "dead", "clear"):
            # v9.5: marco rojo de peligro ELIMINADO (causaba un cuadro negro sobre monstruo y jugador)
            pass
        self.draw_hud()
        pygame.transform.scale(self.canvas, (self.SW, self.SH), self.scaled)
        self.screen.blit(self.scaled, (0, 0))
        SW, SH = self.SW, self.SH
        lh = self.line_h()

        if st in ("play", "paused", "dead", "clear"):
            hy = MAP_H * k + (HUD_H * k - lh) // 2
            self.draw_text("ECO", 90 * k, hy, 1.0, CYAN)
            self.draw_text("MONSTRUOS: %d" % len(self.monsters), 152 * k, hy, 1.0,
                           GOLD if self.monsters else (120, 230, 150))
            self.draw_text("[H]", 198 * k, hy, 1.0, (170, 160, 140))
            self.draw_text("[F11] PANTALLA", 214 * k, hy, 1.0, (170, 160, 140))
            if self.anakin_mode:                         # indicador del modo ANAKIN (y recarga del dash)
                ready = self.player.dash_cd <= 0
                lab_sk = "DARTH VADER" if self.skin == "vader" else "SKIN ANAKIN"
                self.draw_text(lab_sk + " · R: DASH", 6 * k, (MAP_H - 13) * k, 1.0,
                               self.tc((255, 80, 60)) if ready else self.tc((140, 60, 56)))
            elif self.tun_mode:                          # indicador del modo TUN (y recarga del dash)
                ready = self.player.dash_cd <= 0
                self.draw_text("MODO TUN · R: DASH", 6 * k, (MAP_H - 13) * k, 1.0,
                               CYAN if ready else (90, 120, 150))
            lab = "TUTORIAL" if self.tutorial else "NIVEL %d · %s" % (self.level_idx + 1, self.level.name)
            self.draw_text(lab, SW - 4 * k, hy, 1.0, GOLD, anchor="r")
            if st == "play" and self.near_chest():
                self.draw_hint("Pulsa E para abrir el cofre")
            elif self.tutorial and st == "play":
                self.draw_hint(TUT_MSGS[min(self.tut, len(TUT_MSGS) - 1)])
            elif self.toast_t > 0:
                self.draw_hint(self.toast_text)
        if st == "menu":
            self.draw_menu()
        elif st == "paused":
            self.draw_center_title("PAUSA", GOLD, "ESC: continuar    P: reiniciar    H: ayuda    F11: pantalla completa")
        elif st == "dead":
            self.draw_center_title("HAS CAÍDO", RED, "ENTER / P: reintentar nivel    ESC: menú")
        elif st == "clear":
            self.draw_center_title("¡NIVEL SUPERADO!", GOLD, "")
        elif st == "victory":
            self.draw_victory()
        if self.help and st == "play":
            w = int(SW * 0.66)
            r = pygame.Rect((SW - w) // 2, int(SH * 0.03), w, int(SH * 0.94))
            self.draw_panel(r, 232)
            self.draw_controls(r.x + 4 * k, r.y + 4 * k, r.w - 8 * k)
            self.draw_text("[H] cerrar", r.centerx, r.bottom - lh * 1.5, 1.0, GOLD, anchor="c")

    def draw_hint(self, text):
        k = self.k
        lh = self.line_h()
        maxw = int(self.SW * 0.86)
        lines = self.wrap(text, 1.0, maxw - 12 * k)
        w = max(self.text_surf(l, 1.0, PARCH).get_width() for l in lines) + 12 * k
        h = lh * len(lines) + 8 * k
        r = pygame.Rect((self.SW - w) // 2, 3 * k, w, h)
        self.draw_panel(r, 190)
        for i, l in enumerate(lines):
            self.draw_text(l, r.centerx, r.y + 4 * k + i * lh, 1.0, PARCH, anchor="c")

    def draw_center_title(self, title, color, sub):
        k = self.k
        s = pygame.Surface((self.SW, int(34 * k)), pygame.SRCALPHA)
        s.fill((8, 6, 14, 190))
        y = self.SH // 2 - int(26 * k)
        self.screen.blit(s, (0, y))
        self.draw_text(title, self.SW // 2, y + 4 * k, 3.0, color, anchor="c")
        if sub:
            self.draw_text(sub, self.SW // 2, y + 25 * k, 1.0, PARCH, anchor="c")

    def draw_menu(self):
        k, SW, SH = self.k, self.SW, self.SH
        big = pygame.transform.scale(self.tex.knight["down"], (16 * k * 3, 16 * k * 3))
        self.screen.blit(big, (int(SW * 0.115), int(SH * 0.43)))
        self.draw_text("ECHO", int(SW * 0.205), int(SH * 0.07), 5.0, GOLD, anchor="c")
        self.draw_text("KNIGHT", int(SW * 0.205), int(SH * 0.07) + self.line_h(5.0), 5.0, GOLD, anchor="c")
        self.draw_text("Caballero del Eco", int(SW * 0.205), int(SH * 0.07) + self.line_h(5.0) * 2 + 4 * k,
                       1.3, CYAN, anchor="c")
        self.draw_text("Arenas medievales a oscuras", int(SW * 0.205), int(SH * 0.34), 1.0, PARCH, anchor="c")
        self.draw_fs_badge(int(SW * 0.205), int(SH * 0.76))
        if int(self.time * 2) % 2 == 0:
            self.draw_text("ENTER / TOCA - Comenzar", int(SW * 0.205), int(SH * 0.86), 1.5, GOLD, anchor="c")
        self.draw_text("N / toca aquí - Saltar tutorial", int(SW * 0.205), int(SH * 0.93), 1.0, PARCH, anchor="c")
        r = pygame.Rect(int(SW * 0.40), int(SH * 0.03), int(SW * 0.58), int(SH * 0.94))
        self.draw_panel(r, 225)
        self.draw_controls(r.x + 5 * k, r.y + 4 * k, r.w - 10 * k)

    def draw_fs_badge(self, cx, y):
        """Indicador del menu: icono de esquinas + tecla F11 + 'Pantalla completa'."""
        f = self.k / 2.0
        label = "Pantalla completa"
        tw = self.text_surf(label, 1.0, PARCH).get_width()
        kw = self.text_surf("F11", 1.0, PARCH).get_width() + int(10 * f)
        ic, gap = int(12 * f), int(6 * f)
        x = cx - (ic + gap + kw + gap + tw) // 2
        col = GOLD if int(self.time * 2) % 2 == 0 else PARCH
        s, lw = max(2, int(3.5 * f)), max(1, int(f))
        x0, y0 = x, y + int(3 * f)
        x1, y1 = x0 + ic, y0 + ic
        for px, py, ax, ay in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            pygame.draw.line(self.screen, col, (px, py), (px + ax * s, py), lw)
            pygame.draw.line(self.screen, col, (px, py), (px, py + ay * s), lw)
        w, _ = self.draw_key("F11", x + ic + gap, y)
        self.draw_text(label, x + ic + gap + w + gap, y + int(3 * f), 1.0, PARCH)

    def draw_victory(self):
        k, SW, SH = self.k, self.SW, self.SH
        r = pygame.Rect(int(SW * 0.2), int(SH * 0.2), int(SW * 0.6), int(SH * 0.55))
        self.draw_panel(r, 220)
        self.draw_text("¡VICTORIA!", SW // 2, r.y + 6 * k, 3.5, GOLD, anchor="c")
        m, s = divmod(int(self.total_time), 60)
        lines = ["Has escapado de las catacumbas.", "",
                 "Tiempo total: %02d:%02d" % (m, s), "Monstruos derrotados: %d" % self.kills, "",
                 "ENTER: volver al menú"]
        y = r.y + 40 * k
        for l in lines:
            self.draw_text(l, SW // 2, y, 1.2, PARCH, anchor="c")
            y += int(self.line_h(1.2) * 1.2)

    # ------------------------------------------------------------ bucle
    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.fit()
            self.draw()
            self.present()


def main():
    sound = "--sin-sonido" not in sys.argv
    Game(sound=sound).run()


if __name__ == "__main__":
    main()
