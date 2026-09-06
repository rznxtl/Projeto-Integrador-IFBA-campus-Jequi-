import cv2
import numpy as np
import os
import json
import time
from datetime import datetime
import face_recognition
import threading
import csv

# ==========================================
# 1. BANCO DE DADOS E AUDITORIA (CAIXA PRETA)
# ==========================================
DB_FILE = "banco_fichas.json"
LOG_FILE = "logs_turno.csv"
banco_fichas = {}

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        banco_fichas = {int(k): v for k, v in json.load(f).items()}

# Cria o arquivo de log se não existir
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Data_Hora", "ID", "Nome", "Status", "Precisao"])

tempos_log = {} # Evita flood de logs da mesma pessoa

def auditar_ocorrencia(id_suspeito, nome, status, precisao):
    agora = time.time()
    # Registra no banco apenas uma vez a cada 15 segundos por indivíduo
    if agora - tempos_log.get(id_suspeito, 0) > 15:
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%d/%m/%Y %H:%M:%S"), id_suspeito, nome, status, f"{precisao}%"])
        tempos_log[id_suspeito] = agora
        print(f"📄 LOG REGISTRADO: {nome} ({status})")

# ==========================================
# 2. MOTOR BIOMÉTRICO
# ==========================================
print("Extraindo biometrias (dlib)...")
encodings_conhecidos, ids_conhecidos = [], []

for user_id in banco_fichas.keys():
    caminho_img = f"suspeito_{user_id}.jpg"
    if os.path.exists(caminho_img):
        img = face_recognition.load_image_file(caminho_img)
        encodings = face_recognition.face_encodings(img)
        if encodings:
            encodings_conhecidos.append(encodings[0])
            ids_conhecidos.append(user_id)

# ==========================================
# 3. PROCESSAMENTO ASSÍNCRONO (MULTITHREADING)
# ==========================================
frame_atual = None
resultados_ia = []
sistema_ativo = True

def scanner_biometrico():
    global resultados_ia
    while sistema_ativo:
        if frame_atual is not None:
            # Pega uma cópia do frame para não travar o vídeo
            small_frame = cv2.resize(frame_atual, (0, 0), fx=0.25, fy=0.25)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            locs = face_recognition.face_locations(rgb_small, model="cnn") # Mais preciso, mas mais lento. alternativa: "hog" para CPU
            encs = face_recognition.face_encodings(rgb_small, locs)
            
            novos_resultados = []
            for (top, right, bottom, left), face_encoding in zip(locs, encs):
                match_id = None
                precisao = 0
                if encodings_conhecidos:
                    distancias = face_recognition.face_distance(encodings_conhecidos, face_encoding)
                    melhor_idx = np.argmin(distancias)
                    if distancias[melhor_idx] < 0.5:
                        match_id = ids_conhecidos[melhor_idx]
                        precisao = round((1 - distancias[melhor_idx]) * 100)
                
                # Retorna coordenadas ao tamanho original
                novos_resultados.append(((top*4, right*4, bottom*4, left*4), match_id, precisao))
            
            resultados_ia = novos_resultados
        time.sleep(0.05) # Roda a ~20 FPS no background

# Inicia o cérebro da IA em paralelo
ia_thread = threading.Thread(target=scanner_biometrico)
ia_thread.start()

# ==========================================
# 4. CÂMERA E HUD TÁTICO
# ==========================================
cap = cv2.VideoCapture(0) # 0 para webcam padrão, ou caminho do vídeo
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

prev_frame_time = 0
frame_count = 0
modo_noturno = False

os.makedirs("evidencias", exist_ok=True)

while True:
    ret, frame = cap.read()
    if not ret: break
    
    frame_atual = frame.copy() # Alimenta a IA
    frame_count += 1
    
    # ------------------------------------------
    # Filtro Visão Noturna
    # ------------------------------------------
    if modo_noturno:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        zeros = np.zeros_like(gray)
        frame = cv2.merge([zeros, gray, zeros]) # Zera canais R e B, deixa só Verde
    
    # ------------------------------------------
    # Cálculo FPS
    # ------------------------------------------
    new_frame_time = time.time()
    fps = int(1 / (new_frame_time - prev_frame_time)) if (new_frame_time - prev_frame_time) > 0 else 0
    prev_frame_time = new_frame_time

    # ------------------------------------------
    # Design do HUD Overlay
    # ------------------------------------------
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 80), (10, 10, 10), -1)
    cv2.rectangle(overlay, (0, frame.shape[0] - 40), (frame.shape[1], frame.shape[0]), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    modo_txt = "NVG: ON" if modo_noturno else "NVG: OFF"
    cv2.putText(frame, "IFBA - DLIB TACTICAL HUD", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"FPS: {fps} | MODE: {modo_txt}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(frame, agora, (frame.shape[1] - 250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    if int(time.time() * 2) % 2 == 0:
        cv2.circle(frame, (frame.shape[1] - 270, 25), 6, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (frame.shape[1] - 250, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Scanline Effect (Linha de varredura descendo a tela)
    scan_y = (frame_count * 10) % frame.shape[0]
    cv2.line(frame, (0, scan_y), (frame.shape[1], scan_y), (0, 255, 0, 100), 1)

    # ------------------------------------------
    # Renderização dos Alvos (Dados vindos da IA)
    # ------------------------------------------
    for (t, r, b, l), match_id, precisao in resultados_ia:
        nome = "DESCONHECIDO"
        ficha = "Sem registros"
        status_txt = "ANALISANDO..."
        cor = (255, 255, 255)

        if match_id is not None:
            info = banco_fichas[match_id]
            nome = info["nome"]
            ficha = info["ficha"]
            if info["status"] == "procurado":
                cor = (0, 0, 255)
                status_txt = f"PROCURADO [{precisao}%]"
                auditar_ocorrencia(match_id, nome, "PROCURADO", precisao)
            else:
                cor = (0, 255, 0)
                status_txt = f"LIBERADO [{precisao}%]"
                auditar_ocorrencia(match_id, nome, "LIBERADO", precisao)

        # Miras
        w, h = r - l, b - t
        cv2.rectangle(frame, (l, t), (r, b), cor, 1)
        m = 20
        cv2.line(frame, (l, t), (l + m, t), cor, 2)
        cv2.line(frame, (l, t), (l, t + m), cor, 2)
        cv2.line(frame, (r, t), (r - m, t), cor, 2)
        cv2.line(frame, (r, t), (r, t + m), cor, 2)
        cv2.line(frame, (l, b), (l + m, b), cor, 2)
        cv2.line(frame, (l, b), (l, b - m), cor, 2)
        cv2.line(frame, (r, b), (r - m, b), cor, 2)
        cv2.line(frame, (r, b), (r, b - m), cor, 2)

        cv2.rectangle(frame, (l, t - 35), (r, t), (0, 0, 0), -1)
        cv2.putText(frame, nome, (l + 5, t - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)
        cv2.putText(frame, status_txt, (l + 5, t - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
        cv2.putText(frame, ficha, (l, b + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)

    cv2.imshow("Sistema Integrado Bodycam - IFBA", frame)

    # ------------------------------------------
    # Controles Táticos (Teclado)
    # ------------------------------------------
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        sistema_ativo = False
        break
    elif key == ord('n'): # Alterna Visão Noturna
        modo_noturno = not modo_noturno
    elif key == ord('s'): # Salva Snapshot como evidência
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_evidencia = f"evidencias/snap_{ts}.jpg"
        cv2.imwrite(caminho_evidencia, frame_atual)
        print(f"📸 Evidência salva: {caminho_evidencia}")
        
        # Pisca a tela em branco para feedback visual
        cv2.imshow("Sistema Integrado Bodycam - IFBA", np.ones_like(frame) * 255)
        cv2.waitKey(50)

cap.release()
cv2.destroyAllWindows()