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

A barra abaixo da imagem acompanha a importação (arquivo atual/total, recebimento, leitura, cores e miniatura) e a prévia/renderização (filme, papel, digitalização e gravação). O percentual reflete etapas concluídas, sem estimar tempo restante. Etapas longas, como compilações iniciais, podem manter o mesmo percentual enquanto o processamento continua. A barra só chega a 100% quando o resultado também está carregado para exibição; falhas preservam o percentual atingido e liberam os controles para nova tentativa.

JPEG/PNG são tratados como sRGB codificado. RAW usa rawpy com balanço da câmera e saída sRGB linear. TIFF/EXR assumem ProPhoto RGB linear: confira **Avançado** e ajuste o espaço de entrada e a decodificação conforme o arquivo. Esta versão não interpreta automaticamente perfis ICC embutidos nem copia EXIF para a exportação.

O servidor escuta exclusivamente em `127.0.0.1`. Arquivos e resultados são temporários, e não são enviados para serviços externos. Ao encerrar o servidor, a sessão é descartada. A biblioteca de imagens e os resultados usam memória/disco durante a sessão; imagens grandes e renderizações completas podem exigir bastante memória. Há uma simulação por vez e limite de 256 MB por upload. Esta versão é para uso local em uma única sessão de navegador.

## Tempo de renderização

A barra mostra **tempo decorrido** e, quando houver uma base comparável, **tempo restante aproximado**. A estimativa usa os tempos medidos por etapa em renderizações bem-sucedidas desta sessão. São comparados modo (prévia/renderização), dimensões da imagem, filme, papel, espaço de entrada e ajustes de grão/halation/dispersão; mudanças de exposição e filtros de cor podem reutilizar a base.

Na primeira combinação sem histórico aparece **Calculando estimativa…**. Depois de concluir uma renderização, a próxima com configuração comparável poderá usar essa medição. O histórico é limitado, fica em memória e é descartado ao reiniciar o servidor. Não se extrapola o tempo de uma imagem pequena para uma imagem grande.

A estimativa é atualizada nas consultas de progresso, sem fazer novas requisições adicionais. Ela soma as durações esperadas das etapas restantes e desconta o tempo já gasto na etapa atual. Se uma etapa exceder muito o esperado, aparece **Recalculando estimativa…**. Compilações iniciais do Numba, carga do computador e conteúdo da imagem podem alterar os tempos; a estimativa não é uma garantia. Falhas não alimentam o histórico.

## Logs e diagnóstico

Ao iniciar `spektrafilm-web`, os logs são gravados no terminal e em `logs/spektrafilm-web.log`, relativo à pasta onde o comando foi executado. O caminho absoluto é mostrado na inicialização. O arquivo registra início da sessão, etapas e tempo decorrido dos jobs, erros completos do Python e erros da interface recebidos pelo servidor. A rotação mantém o arquivo atual e até três cópias anteriores de até 5 MiB cada.

```sh
# Acompanhar o log em outro terminal, na mesma pasta de execução:
tail -f logs/spektrafilm-web.log

# Incluir também cada consulta de progresso:
spektrafilm-web --debug

# Escolher outro destino:
spektrafilm-web --log-file /tmp/spektrafilm-web.log
```

Consultas repetidas de progresso ficam fora do log padrão; `--debug` as habilita. Falhas do navegador também aparecem no console de desenvolvimento. Se o servidor estiver inacessível, essas falhas não poderão ser persistidas no backend.

Após alterar o código Python, encerre o servidor com `Ctrl+C`, execute `spektrafilm-web` novamente e atualize a página. Reabra as imagens, pois a sessão é temporária. A interface verifica a compatibilidade do backend antes de importar/renderizar. Um backend antigo pode servir os arquivos novos da interface sem conhecer os endpoints de progresso: nesse caso aparece uma instrução de reinício. Consultas de importação que retornam 404 repetidamente são interrompidas após três tentativas.

## Verificar

```sh
PYTHONPATH=src python3.13 -m unittest discover -s tests/web -v
node --check src/spektrafilm_web/static/app.js
node --test tests/web_js/progress.test.cjs
```

Os testes HTTP e de progresso não exigem as dependências científicas. Os testes JavaScript usam um substituto mínimo do DOM e não validam a aparência no navegador. Para validar a simulação ponta a ponta, instale o projeto e processe uma imagem pelo navegador.

Film modeling powered by [spektrafilm](https://github.com/andreavolpato/spektrafilm), de Andrea Volpato. Código sob a licença do projeto; perfis preservam suas respectivas atribuições e licenças.
