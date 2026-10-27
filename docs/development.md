# Desenvolvimento

## Ambiente completo

Use Python 3.13 e siga a instalação no [README](../README.md). Para instalar também as dependências de desenvolvimento:

```sh
python -m pip install -e '.[dev]'
```

A interface usa arquivos HTML/CSS/JS diretamente. Não há `npm install` nem etapa de build. Para executar o código sem instalar o entry point, com as dependências já disponíveis:

```sh
PYTHONPATH=src python -m spektrafilm_web.server
```

## Verificações leves

Na raiz do checkout:

```sh
PYTHONPATH=src python3.13 -m unittest discover -s tests/web -v
python3.13 -m compileall -q src/spektrafilm_web
node --check src/spektrafilm_web/static/app.js
```

Os testes web usam apenas a biblioteca padrão e precisam abrir uma porta temporária em loopback. Cobrem arquivos estáticos, perfis reais, recusa de render sem imagem, recusa de POST de outra origem, rotas privadas/inexistentes e faixas numéricas. Não cobrem decodificação de imagens, fidelidade da simulação, exportações reais ou comportamento visual.

O workflow `.github/workflows/web-checks.yml` executa essas verificações em pull requests e pushes. Ele não instala as dependências científicas e não representa uma validação completa do motor.

## Verificação manual ponta a ponta

Com as dependências completas instaladas:

1. Abra o servidor e importe um JPEG de teste.
2. Confirme nome, dimensões, miniatura, zoom e seleção entre duas imagens.
3. Gere uma prévia com Kodak Portra 400 e Kodak Portra Endura.
4. Confira comparação, controle divisor e resultado no tamanho reduzido.
5. Mude a exposição e gere outra prévia; confira a alteração visual.
6. Renderize em resolução completa com grão e exporte PNG, JPEG e TIFF.
7. Reabra os arquivos em um visualizador que permita conferir dimensões e profundidade do TIFF.
8. Teste um RAW e um TIFF/EXR conhecido, confirmando a configuração de entrada em **Avançado**.
9. Confira o layout em janela estreita e a navegação por teclado.
10. Encerre o servidor e confirme que não há promessa de restauração da sessão.

Registre sistema, versão do Python, arquivo de teste e resultado ao relatar falhas. Não envie fotografias particulares ou metadados pessoais em issues públicas.

## Testes herdados

Os testes do motor, GUI desktop e criador de LUTs ficam em `tests/` e exigem as dependências correspondentes. Para a suíte completa:

```sh
python -m pytest
```

Consulte os READMEs dos respectivos pacotes para detalhes. Os testes web usam `unittest discover` para não carregar o `conftest.py` geral e suas dependências científicas.

## Problemas comuns

| Sintoma | Verificação |
| --- | --- |
| `spektrafilm-web` não encontrado | Ative `.venv` e instale com `python -m pip install -e .` |
| `ModuleNotFoundError` durante upload ou render | Confirme Python 3.13 e a instalação completa no ambiente ativo |
| Porta já ocupada | Use `spektrafilm-web --port 8766` e abra a mesma porta no navegador |
| Primeira simulação demorada | Aguarde a compilação inicial e comece com uma imagem menor |
| Cor inesperada em TIFF/EXR | Confira espaço e decodificação da entrada; a interface não lê ICC automaticamente |
| Resultado não muda ao ajustar controles | Clique novamente em Prévia ou Renderizar |
| Grão não aparece | Use Renderizar; o modo de prévia desativa grão |
| Sessão perdida após fechar o servidor | Comportamento atual: imagens e jobs são temporários |

## Publicação do repositório

A raiz deste checkout deve ser a raiz do novo repositório. Preserve `LICENSE`, `SPEKTRAFILM_LICENSE.txt`, atribuições dos ativos e `CITATION.cff`. O destino escolhido é `emnovais/spektrafilme-web` no GitHub. O comando da aplicação continua sendo `spektrafilm-web`.

O README principal descreve a camada web; `README.upstream.md` preserva o conteúdo recebido do projeto original. Este checkout não veio com histórico Git: uma inicialização local cria uma nova linha de histórico e não equivale a um fork criado no GitHub. Caso seja necessário preservar a relação de fork e o histórico upstream, use um clone/fork do repositório original como base antes de importar as alterações web.

Configurações pessoais, ambientes virtuais, caches, credenciais e imagens privadas não devem fazer parte dos commits. O `.gitignore` inclui os padrões locais mais comuns; revise os arquivos preparados antes da publicação.
