# Corte Viral AI — MVP

Aplicação web local para transformar vídeos autorizados em cortes verticais.

## O que funciona
- Interface web responsiva.
- Importação de vídeo por arquivo.
- Campo para link do YouTube: valida e registra o link, mas não baixa o vídeo.
- Processamento local com FFmpeg e transcrição com faster-whisper.
- Seleção automática de trechos por pausas, frases e palavras-chave de impacto.
- Exportação de MP4 vertical 9:16 com legendas SRT embutidas.

## Limitação importante do link do YouTube
O link sozinho não fornece legalmente/tecnicamente o arquivo para edição. Para gerar os MP4s, envie o arquivo original do vídeo, ou use um arquivo obtido por meios autorizados pelo titular e pelas regras da plataforma. O link fica associado ao projeto como referência.

## Requisitos
- Python 3.10+
- FFmpeg instalado e disponível no PATH
- Recomendada GPU para transcrição mais rápida; CPU também funciona.

## Instalação
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```
Abra http://127.0.0.1:8000

Na primeira execução, o faster-whisper baixa o modelo `base` (é necessário internet). Para mudar o modelo, defina `WHISPER_MODEL=small` ou `medium`.

## Como usar
1. Abra o site.
2. Informe opcionalmente o link de referência do YouTube.
3. Envie um vídeo que você tenha direito de editar.
4. Escolha quantos cortes deseja e a duração aproximada.
5. Clique em **Gerar cortes**.
6. Baixe os MP4s na lista de resultados.

## Observações
- Este MVP processa um vídeo por vez e guarda arquivos na pasta `data/`.
- A seleção automática é heurística: não promete viralização nem substitui revisão humana.
- Antes de publicar, revise o conteúdo, as legendas, o enquadramento e os direitos de uso.
- Monetização depende das regras atuais de cada plataforma, originalidade, autorização e políticas de conteúdo reutilizado.


## Publicação gratuita no Render (teste)
1. Crie uma conta no GitHub e um repositório novo.
2. Envie todos os arquivos desta pasta para o repositório.
3. Crie uma conta no Render e escolha **New → Blueprint**.
4. Conecte o repositório; o Render detectará `render.yaml`.
5. Confirme a criação do serviço gratuito. Após o deploy, use o endereço `https://...onrender.com`.

O plano gratuito é apenas para demonstração/testes: o serviço pode dormir após inatividade, o disco é temporário e o limite de RAM pode impedir o processamento de vídeos maiores. O modelo `tiny` foi escolhido para reduzir o consumo, mas não há garantia de que todo vídeo será processado no plano gratuito. Não envie conteúdo privado ou sensível.
