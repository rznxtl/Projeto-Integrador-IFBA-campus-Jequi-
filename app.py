import streamlit as st
import json
import os
import pandas as pd
from PIL import Image
import subprocess

# ==========================================
# CONFIGURAÇÕES DA PÁGINA
# ==========================================
st.set_page_config(page_title="Central de Comando - IFBA", page_icon="🚓", layout="wide")
DB_FILE = "banco_fichas.json"
LOG_FILE = "logs_turno.csv"
EVIDENCIAS_DIR = "evidencias"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)
if not os.path.exists(EVIDENCIAS_DIR):
    os.makedirs(EVIDENCIAS_DIR)

def carregar_banco():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_banco(dados):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4)

banco = carregar_banco()

# ==========================================
# MENU LATERAL
# ==========================================
st.sidebar.title("🚓 MENU TÁTICO")
menu = st.sidebar.radio("Navegação", [
    "Dashboard & Monitoramento", 
    "Caixa Preta (Logs)",
    "Gestão de Suspeitos", 
    "Galeria de Evidências",
    "Documentação do Projeto"
])

# ==========================================
# ABA 1: DASHBOARD E WEBCAM
# ==========================================
if menu == "Dashboard & Monitoramento":
    st.title("📊 Centro de Operações")
    st.markdown("Monitoramento em tempo real das bodycams em campo.")
    
    st.write("Clique abaixo para iniciar a transmissão tática (Janela do OpenCV).")
    if st.button("🔴 INICIAR BODYCAM (MAIN.PY)", use_container_width=True):
        try:
            subprocess.Popen(["python", "main.py"])
            st.success("Transmissão iniciada! Verifique a janela da câmera.")
        except Exception as e:
            st.error(f"Erro ao iniciar câmera: {e}")
            
    col1, col2, col3 = st.columns(3)
    col1.metric("Suspeitos Cadastrados", len(banco))
    col2.metric("Evidências Coletadas", len(os.listdir(EVIDENCIAS_DIR)))
    
    alvos_procurados = 0
    for info in banco.values():
        if info.get("status") == "procurado":
            alvos_procurados += 1
    col3.metric("Alvos Procurados", alvos_procurados)

# ==========================================
# ABA 2: CAIXA PRETA (LOGS)
# ==========================================
elif menu == "Caixa Preta (Logs)":
    st.title("🗃️ Auditoria e Caixa Preta")
    st.markdown("Registro imutável de todas as detecções realizadas pelas bodycams em campo.")
    
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE)
            st.dataframe(df.iloc[::-1], use_container_width=True, height=500)
            
            # Opção para exportar ou limpar logs
            if st.button("⚠️ Limpar Registros de Turno"):
                os.remove(LOG_FILE)
                st.rerun()
        except Exception as e:
            st.warning("Aguardando registros da bodycam...")
    else:
        st.info("Nenhuma ocorrência registrada neste turno.")

# ==========================================
# ABA 3: CADASTRO E GESTÃO (CRUD)
# ==========================================
elif menu == "Gestão de Suspeitos":
    st.title("📂 Base de Dados Biométrica")
    
    aba_cad, aba_list = st.tabs(["Cadastrar Novo", "Listar/Excluir"])
    
    with aba_cad:
        col1, col2 = st.columns(2)
        
        with col1:
            proximo_id = max([int(k) for k in banco.keys()] + [0]) + 1
            st.text_input("ID Único (Gerado Automaticamente)", value=str(proximo_id), disabled=True)
            novo_nome = st.text_input("Nome Completo")
            nova_ficha = st.text_area("Ocorrências / Observações")
            novo_status = st.selectbox("Status", ["liberado", "procurado"])
            
        with col2:
            st.write("Foto do Indivíduo")
            metodo_foto = st.radio("Como deseja enviar a foto?", ["Upload de Arquivo", "Tirar Foto com a Webcam"])
            
            foto_bytes = None
            if metodo_foto == "Upload de Arquivo":
                foto_upload = st.file_uploader("Envie a foto frontal", type=["jpg", "png", "jpeg"])
                if foto_upload:
                    foto_bytes = foto_upload.read()
            else:
                foto_cam = st.camera_input("Tirar foto pelo painel")
                if foto_cam:
                    foto_bytes = foto_cam.read()

        if st.button("SALVAR REGISTRO", type="primary"):
            if not foto_bytes:
                st.error("É obrigatório enviar uma foto para extração biométrica.")
            elif not novo_nome.strip():
                st.error("O nome não pode ficar em branco.")
            else:
                caminho_img = f"suspeito_{proximo_id}.jpg"
                with open(caminho_img, "wb") as f:
                    f.write(foto_bytes)
                
                banco[str(proximo_id)] = {
                    "nome": novo_nome,
                    "ficha": nova_ficha,
                    "status": novo_status
                }
                salvar_banco(banco)
                st.success(f"Indivíduo {novo_nome} cadastrado com sucesso sob o ID {proximo_id}!")
                st.rerun()

    with aba_list:
        if len(banco) == 0:
            st.write("Nenhum registro encontrado.")
        else:
            for id_str, info in banco.items():
                with st.expander(f"ID: {id_str} - {info['nome']} ({info['status'].upper()})"):
                    col_img, col_info, col_del = st.columns([1, 3, 1])
                    with col_img:
                        caminho_img = f"suspeito_{id_str}.jpg"
                        if os.path.exists(caminho_img):
                            st.image(Image.open(caminho_img), width=100)
                    with col_info:
                        st.write(f"**Ficha:** {info['ficha']}")
                    with col_del:
                        if st.button("🗑️ Excluir", key=f"del_{id_str}"):
                            del banco[id_str]
                            salvar_banco(banco)
                            if os.path.exists(caminho_img):
                                os.remove(caminho_img)
                            st.rerun()

# ==========================================
# ABA 4: GALERIA DE EVIDÊNCIAS
# ==========================================
elif menu == "Galeria de Evidências":
    st.title("📸 Sistema de Evidências em Campo")
    st.markdown("Fotos capturadas pelo policial durante a abordagem (Tecla `S` no HUD).")
    
    evidencias = [f for f in os.listdir(EVIDENCIAS_DIR) if f.endswith(('.jpg', '.png'))]
    evidencias.sort(reverse=True)
    
    if not evidencias:
        st.info("Nenhuma evidência capturada ainda.")
    else:
        cols = st.columns(3)
        for index, img_name in enumerate(evidencias):
            with cols[index % 3]:
                img_path = os.path.join(EVIDENCIAS_DIR, img_name)
                st.image(Image.open(img_path), caption=img_name, use_container_width=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    with open(img_path, "rb") as file:
                        st.download_button(label="⬇️ Baixar", data=file, file_name=img_name, mime="image/jpeg", key=f"dl_{img_name}", use_container_width=True)
                with c2:
                    if st.button("🗑️ Excluir", key=f"del_ev_{img_name}", use_container_width=True):
                        os.remove(img_path)
                        st.rerun()

# ==========================================
# ABA 5: DOCUMENTAÇÃO ACADÊMICA
# ==========================================
elif menu == "Documentação do Projeto":
    st.title("📄 Bodycam AI - Documentação Oficial do Projeto")
    st.markdown("**Projeto Integrador (PII) - Instituto Federal da Bahia (IFBA)**")
    
    st.markdown("""
    ---
    
    ### 👨‍💻 Equipe Desenvolvedora (Turma: TI432)
    * **Renato Santana Santos Alcantara de Oliveira**
    * **Nicolas Leite Ferreira da Silva**
    * **Pietro Brandão Santana**
    * **André Mauro Miranda Batista**

    ---

    ## 1. Visão Geral e Objetivo
    O **Bodycam AI** é um sistema computacional tático de visão computacional projetado para simular o uso de câmeras corporais integradas a algoritmos de Inteligência Artificial para segurança pública. O objetivo principal é fornecer às forças de segurança um mecanismo de identificação biométrica em tempo real, capaz de reconhecer alvos procurados ou indivíduos autorizados durante abordagens perimetrais, registrando automaticamente históricos de auditoria (*Caixa Preta*).

    O projeto adota uma arquitetura descentralizada dividida em dois eixos operacionais:
    1. **Frontend / Central de Comando (Web):** Painel administrativo para gestão de banco de dados biométrico, consulta de evidências e auditoria de logs operacionais.
    2. **Edge / Módulo Operacional (HUD Native):** Script de captura e inferência que roda diretamente no hardware em campo com HUD (Heads-Up Display) tático renderizado sobre a imagem, otimizado para não depender de conexões constantes com a internet.

    ---

    ## 2. Arquitetura e Tecnologias Utilizadas
    A seleção do stack tecnológico priorizou desempenho de processamento em tempo real, robustez matemática e total compatibilidade com distribuições Linux de alto desempenho.

    * **`dlib` & `face_recognition` (Motor Biométrico C++):** Utilizados para extração dos vetores biométricos. Escolhidos pela superioridade em precisão (99.38% no benchmark *Labeled Faces in the Wild*) e por rodar nativamente em C++ compilado.
    * **`OpenCV (cv2)` (Processamento de Imagem):** Gerencia a captura da câmera, manipulação de matrizes de pixels, aplicação de filtros gráficos (modo visão noturna), overlays de HUD tático e gravação de quadros.
    * **`Streamlit` (Dashboard de Gerenciamento):** Framework reativo utilizado na criação da Central de Comando para visualização de estatísticas, gestão da base de dados e download das evidências. A escolha do Python se deu pela agilidade na prototipagem e integração fluida com modelos de IA.
    * **`Threading` (Processamento Assíncrono):** Execução da inteligência artificial em uma *Thread* paralela ao loop de renderização de vídeo. Isso impede que a taxa de quadros (FPS) da câmera caia enquanto a IA calcula os vetores faciais matemáticos.

    ---

    ## 3. Metodologia Computacional e Engenharia de IA
    A identificação biométrica no **Bodycam AI** segue um pipeline rigoroso dividido em três estágios matemáticos:

    ### A. Detecção Facial (HOG vs CNN)
    O sistema aplica o algoritmo **HOG (Histogram of Oriented Gradients)**. O frame capturado é convertido para escala de cinza e dividido em pequenas células onde os gradientes de intensidade de luz são calculados. Isso permite detectar a forma estrutural do rosto humano independentemente de variações severas de iluminação.

    ### B. Extração de Embeddings (128 Pontos Nodais)
    Uma vez localizado o rosto, uma Rede Neural Convolucional Profunda analisa a região e extrai **128 medidas quantitativas** (distância entre os olhos, largura do nariz, profundidade da mandíbula, formato dos lábios). Esse conjunto forma o *Face Encoding* único do indivíduo.

    ### C. Classificação por Distância Euclidiana
    O sistema calcula a Distância Euclidiana entre o vetor capturado em tempo real e os vetores armazenados no banco de dados. Uma distância menor que `0.5` caracteriza um *Match* positivo, enquanto valores superiores classificam o alvo como *Desconhecido*.

    > **Fatores Limitantes Físicos e Ambientais:** Sistemas biométricos 2D sofrem degradação de precisão em duas situações críticas: (1) **Oclusão e Ângulo de Perfil**, onde o rosto gira mais de 45º e oculta os pontos nodais essenciais; e (2) **Intempéries Ambientais**, como chuva forte ou ausência total de fótons (escuridão absoluta sem emissor infravermelho físico), que injetam "ruído" na matriz da imagem lida pelo OpenCV.

    ---

    ## 4. Funcionalidades do HUD Tático e Atalhos
    O módulo operacional emite uma janela nativa com os seguintes recursos:
    * **Tecla `N` (Visão Noturna / Infravermelho Simulado):** Zera os canais de cor Vermelho e Azul da matriz RGB e amplifica o canal Verde, simulando a resposta espectral de fósforo verde usada em equipamentos de visão noturna militar.
    * **Tecla `S` (Snapshot / Evidência):** Captura o frame exato da câmera sem os elementos do HUD e salva no servidor com *timestamp* no nome do arquivo.
    * **Auditoria Automática:** Salva passivamente ocorrências positivas no arquivo `logs_turno.csv`, garantindo a lisura da operação policial.

    ---

    ## 5. Comandos Operacionais e Configuração de Ambiente
    Para garantir a integridade dos módulos de visão computacional, o sistema exige configuração via terminal. Abaixo constam os processos executados para erguer a infraestrutura do projeto:

    **A. Criação e Ativação de Ambiente Virtual (VENV)**
    Para isolar o ecossistema do projeto das bibliotecas globais do sistema operacional (prevenindo quebras de dependências), cria-se um ambiente virtual protegido:
    ```bash
    # Geração da estrutura da interface virtual
    python -m venv venv
    
    # Ativação do ambiente para direcionar as instalações
    source venv/bin/activate
    ```

    **B. Importação e Instalação de Dependências**
    Com o venv ativo, utiliza-se o gerenciador de pacotes para importar os motores essenciais do projeto (IA, manipulação de matrizes e web):
    ```bash
    pip install --upgrade pip setuptools
    pip install cmake dlib face_recognition opencv-python pandas streamlit
    ```

    **C. Bypass de Sandbox em Contêineres (Flatpak Bash)**
    Sistemas Linux modernos frequentemente isolam aplicações em contêineres Flatpak (como o editor de código nativo do desenvolvedor). Essa *sandbox* bloqueia o barramento de hardware, impedindo que a IA enxergue o dispositivo físico da câmera (`/dev/video0`). O comando a seguir resolve isso interceptando o bash raiz do contêiner e fornecendo permissão manual de acesso:
    ```bash
    flatpak run --command=bash com.visualstudio.code
    ```

    **D. Execução dos Scripts**
    ```bash
    # 1. Start no Frontend (Levanta o servidor local na porta 8501)
    streamlit run app.py
    
    # 2. Start no Edge / Bodycam (Gatilho da janela do OpenCV)
    python main.py
    ```

    ---

    ## 6. Considerações Éticas e Segurança de Dados (LGPD)
    O desenvolvimento de tecnologias de vigilância exige responsabilidade cívica. O **Bodycam AI** foi arquitetado tendo em vista os princípios da **Lei Geral de Proteção de Dados (LGPD)**:
    * **Processamento Local (Edge Computing):** Os dados biométricos não são enviados para servidores em nuvem de terceiros. Todo o processamento ocorre no hardware local (arquivos locais JSON e CSV), minimizando riscos de vazamento.
    * **Não-Retenção de Desconhecidos:** O algoritmo extrai os 128 pontos faciais de pessoas não cadastradas apenas em memória RAM volátil. Se a pessoa não é identificada como alvo, os dados matemáticos são descartados no frame seguinte (em frações de segundo), garantindo a privacidade dos cidadãos comuns.
    """)