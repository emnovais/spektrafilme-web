# Spektrafilm Web

Interface local em português para o motor Python do Spektrafilm. A GUI desktop continua disponível pelo comando `spektrafilm`.

## Executar

Na raiz deste projeto, com Python 3.13:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
spektrafilm-web
```

Abra http://127.0.0.1:8765 no navegador. Para trocar a porta: `spektrafilm-web --port 8766`.
Sem instalar o pacote, dentro de um ambiente com suas dependências, use `PYTHONPATH=src python -m spektrafilm_web.server`.

## Fluxo

1. Abra uma ou mais imagens ou arraste arquivos para a área central.
2. Selecione filme e papel da biblioteca real de perfis do projeto.
3. Ajuste exposição, filtros do ampliador, partículas e suavização de grão, halation e dispersão.
4. Gere uma **Prévia**, com até 1000 pixels no maior lado. O modo rápido do motor desativa grão e outros efeitos espaciais dispendiosos.
5. Use **Renderizar** para resolução completa e efeitos completos. A primeira execução pode levar mais tempo por causa das compilações do Numba.
6. Compare com o original usando o controle na base da imagem e exporte PNG/JPEG ou TIFF de 16 bits em sRGB. A exportação de prévia é identificada como reduzida e permite apenas PNG.

JPEG/PNG são tratados como sRGB codificado. RAW usa rawpy com balanço da câmera e saída sRGB linear. TIFF/EXR assumem ProPhoto RGB linear: confira **Avançado** e ajuste o espaço de entrada e a decodificação conforme o arquivo. Esta versão não interpreta automaticamente perfis ICC embutidos nem copia EXIF para a exportação.

O servidor escuta exclusivamente em `127.0.0.1`. Arquivos e resultados são temporários, e não são enviados para serviços externos. Ao encerrar o servidor, a sessão é descartada. A biblioteca de imagens e os resultados usam memória/disco durante a sessão; imagens grandes e renderizações completas podem exigir bastante memória. Há uma simulação por vez e limite de 256 MB por upload. Esta versão é para uso local em uma única sessão de navegador.

## Verificar

```sh
PYTHONPATH=src python3.13 -m unittest discover -s tests/web -v
node --check src/spektrafilm_web/static/app.js
```

Os testes HTTP não exigem as dependências científicas. Para validar a simulação ponta a ponta, instale o projeto e processe uma imagem pelo navegador.

Film modeling powered by [spektrafilm](https://github.com/andreavolpato/spektrafilm), de Andrea Volpato. Código sob a licença do projeto; perfis preservam suas respectivas atribuições e licenças.
