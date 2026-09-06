# Projeto-Integrador-IFBA-campus-Jequié
Apenas os codigos usados para criar o projeto que consiste em uma webcam policial com reconhecimento facial do suspeito
Projeto ainda nao 100%, feito por mim e mais 3 alunos do IFBA-jequié da turma TI432 em 2026

===============================================================================
📄 BODYCAM AI - DOCUMENTAÇÃO OFICIAL DO PROJETO
Projeto Integrador (PII) — Instituto Federal da Bahia (IFBA)
===============================================================================

1. VISÃO GERAL E OBJETIVO
-------------------------------------------------------------------------------
O Bodycam AI é um sistema computacional tático de visão computacional projetado 
para simular o uso de câmeras corporais (Bodycams) integradas a algoritmos de 
Inteligência Artificial para segurança pública. O objetivo principal é fornecer 
às forças de segurança um mecanismo de identificação biométrica em tempo real 
capaz de reconhecer alvos procurados ou indivíduos autorizados durante abordagens 
perimetrais, registrando automaticamente históricos de auditoria (Caixa Preta).

O projeto adota uma arquitetura descentralizada dividida em dois eixos operacionais:
- Frontend / Central de Comando (Web): Painel administrativo para gestão de 
  banco de dados biométrico, consulta de evidências e logs de turno.
- Edge / Módulo Operacional (HUD Native): Script de captura e inferência que 
  roda diretamente no hardware em campo com HUD (Heads-Up Display) tático 
  renderizado sobre a imagem.


2. ARQUITETURA E TECNOLOGIAS UTILIZADAS
-------------------------------------------------------------------------------
A seleção do stack tecnológico priorizou desempenho de processamento em tempo 
real (manutenção de FPS elevado), robustez matemática e total compatibilidade 
com distribuições Linux de alto desempenho.

- dlib & face_recognition (Motor Biométrico C++): Utilizados para extração dos 
  vetores biométricos. Escolhidos pela superioridade em precisão (99.38% no 
  benchmark Labeled Faces in the Wild) e por rodar nativamente em C++ compilado.
- OpenCV (cv2) (Processamento de Imagem): Gerencia a captura da câmera, 
  manipulação de matrizes de pixels, aplicação de filtros gráficos (modo visão 
  noturna), overlays de HUD tático e gravação de quadros.
- Streamlit (Dashboard de Gerenciamento): Framework reativo utilizado na criação 
  da Central de Comando para visualização de estatísticas, gestão da base de 
  dados e download das evidências.
- Pandas & JSON (Persistência e Registros): Estrutura leve para armazenamento 
  no-SQL de perfis (banco_fichas.json) e registros temporais imutáveis de 
  detecções (logs_turno.csv).
- Threading (Processamento Assíncrono): Execução da inteligência artificial em 
  uma Thread paralela ao loop de renderização de vídeo. Isso impede que a taxa de 
  quadros (FPS) da câmera caia enquanto a IA calcula os vetores faciais.


3. METODOLOGIA COMPUTACIONAL E ENGENHARIA DE IA
-------------------------------------------------------------------------------
A identificação biométrica no Bodycam AI segue um pipeline rigoroso dividido em 
três estágios matemáticos:

A. Detecção Facial (HOG vs CNN)
O sistema aplica o algoritmo HOG (Histogram of Oriented Gradients). O frame 
capturado é convertido para escala de cinza e dividido em pequenas células onde 
os gradientes de intensidade de luz são calculados. Isso permite detectar a forma 
estrutural do rosto humano independentemente de variações severas de iluminação.

B. Extração de Embeddings (128 Pontos Nodais)
Uma vez localizado o rosto, uma Rede Neural Convolucional Profunda (Deep Metric 
Learning) analisa a região e extrai 128 medidas quantitativas (distância entre 
os olhos, largura do nariz, profundidade da mandíbula, formato dos lábios). Esse 
conjunto de 128 números ponto flutuante forma o Face Encoding único do indivíduo.

C. Classificação por Distância Euclidiana
Para identificar um indivíduo, o sistema calcula a Distância Euclidiana entre o 
vetor capturado em tempo real (V_cam) e os vetores armazenados no banco de 
dados (V_db):

    D(V_cam, V_db) = sqrt( sum_{i=1}^{128} (V_cam[i] - V_db[i])^2 )

- Tolerância D < 0.5: Caracteriza um Match positivo (Alta similaridade).
- Tolerância D >= 0.5: Indivíduo classificado como Desconhecido.

Análise Técnica sobre Reconhecimento de Perfil (Ângulos Extremos):
Sistemas de biometria 2D baseados em 128 pontos nodais requerem a visibilidade 
de ambos os olhos e do centro do nariz. Quando o indivíduo gira o rosto em um 
ângulo superior a 45º (perfil parcial ou total), a oclusão anatômica oculta metade 
dos pontos de extração. Para mitigar isso, orienta-se o cadastro de fotos em 
posições levemente anguladas ou o uso futuro de redes de alinhamento facial 3D (3DFA).


4. ESTRUTURA DE MÓDULOS DO SISTEMA
-------------------------------------------------------------------------------
- main.py: Loop principal de visão computacional. Gerencia a leitura da câmera, 
  inicializa a thread de IA, aplica filtros de visão noturna e intercepta atalhos 
  de teclado.
- app.py: Aplicação Web Streamlit que provê o CRUD completo de suspeitos, 
  visualização dos logs da Caixa Preta, galeria de evidências e esta documentação.
- banco_fichas.json: Mapeamento estruturado contendo o ID, Nome Completo, Ficha 
  Criminal e Status (Procurado/Liberado).
- logs_turno.csv: Registro cronológico de auditoria contendo Data/Hora, ID, Nome, 
  Status e Precisão do Match.
- /evidencias: Diretório físico onde são salvas as fotos de capturas de campo 
  acionadas pelo policial.


5. FUNCIONALIDADES DO HUD TÁTICO E ATALHOS
-------------------------------------------------------------------------------
O módulo operacional emite uma janela nativa com os seguintes recursos:
- Tecla N (Visão Noturna / Infravermelho Simulado): Zera os canais de cor 
  Vermelho e Azul da matriz RGB e amplifica o canal Verde, simulando a resposta 
  espectral de fósforo verde usada em equipamentos de visão noturna militar.
- Tecla S (Snapshot / Evidência): Captura o frame exato da câmera sem os 
  elementos do HUD e salva no servidor com timestamp no nome do arquivo.
- Tecla Q (Encerrar Operação): Finaliza as threads de processamento e libera o 
  recurso da câmera com segurança.


6. ENGENHARIA DE SOFTWARE E RESOLUÇÃO DE PROBLEMAS (ESTUDO DE CASO LINUX)
-------------------------------------------------------------------------------
Durante o desenvolvimento do projeto no sistema operacional CachyOS (Arch Linux), 
foram enfrentadas e superadas barreiras de infraestrutura de software:

- Isolamento do VS Code em Flatpak: Como o ambiente de desenvolvimento rodava 
  dentro do contêiner isolado do Flatpak, o acesso direto aos dispositivos do 
  sistema (/dev/video0) e bibliotecas do host estava bloqueado. A comunicação foi 
  estabelecida via execução interativa do bash do container:

    flatpak run --command=bash com.visualstudio.code

- Incompatibilidade com Python 3.14 (Bleeding-Edge): A versão bleeding-edge do 
  Python no Arch Linux não possuía rodas (wheels) pré-compiladas para o dlib e 
  dependências C++. Foi aplicado um isolamento de ambiente virtual (venv) 
  apontando estrategicamente para o Python 3.11:

    python3.11 -m venv venv
    source venv/bin/activate

- Depreciação do pkg_resources: Devido a mudanças recentes no empacotamento do 
  Python, o módulo setuptools precisou ser explicitamente atualizado dentro do 
  ambiente virtual para permitir que o repositório de modelos biométricos 
  compilasse corretamente:

    pip install --upgrade pip setuptools
    pip install face_recognition opencv-python pandas streamlit

  fim.
