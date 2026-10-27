# Arquitetura

A camada web reutiliza o motor incluído no repositório. Ela cuida de arquivos, parâmetros, sessão e apresentação; os modelos físicos permanecem em `spektrafilm`.

```mermaid
flowchart LR
    UI[HTML / CSS / JavaScript] -->|HTTP em 127.0.0.1| Server[Servidor Python]
    Server --> Profiles[Perfis JSON]
    Server --> Images[Imagens em memória]
    Server --> Worker[Thread de simulação]
    Worker --> Runtime[Motor spektrafilm]
    Runtime --> Output[Resultados temporários]
    Output --> UI
```

## Componentes

| Caminho | Responsabilidade |
| --- | --- |
| `src/spektrafilm_web/server.py` | HTTP, upload, sessão, jobs, mapeamento de parâmetros e exportações |
| `src/spektrafilm_web/static/index.html` | Estrutura e controles da interface |
| `src/spektrafilm_web/static/style.css` | Tema escuro e adaptação do layout |
| `src/spektrafilm_web/static/app.js` | Seleção de perfis, uploads, comparação, polling e downloads |
| `src/spektrafilm` | Motor físico, perfis e utilitários de imagem |
| `src/spektrafilm_gui` | Aplicativo desktop existente |
| `src/spektrafilm_lut_creator` | Ferramentas de LUT existentes |
| `tests/web` | Contratos HTTP e validação dos parâmetros numéricos |

O frontend não exige bundler, framework ou instalação de pacotes JavaScript. O servidor usa `ThreadingHTTPServer` da biblioteca padrão.

## Ciclo de uma imagem

1. O navegador envia os bytes para `POST /api/upload`.
2. O servidor lê a imagem em RGB, atribui um ID e cria uma prévia do original com até 1600 pixels no maior lado.
3. A matriz decodificada fica em `server.images`; o arquivo de upload é removido.
4. O navegador envia o ID e os ajustes para `POST /api/render`.
5. Uma thread chama `init_params` e depois `simulate_preview` ou `simulate`.
6. O navegador consulta `GET /api/jobs/{id}` a cada segundo.
7. Os resultados são disponibilizados em `/media/` para exibição e download.

## Concorrência e estado

Um lock protege a admissão de novas simulações: se houver um job em execução, outro render recebe HTTP 409. Os estados do job são `running`, `done` e `error`.

Imagens e jobs pertencem ao processo do servidor. Abas compartilham o mesmo estado no backend, embora cada aba mantenha suas próprias seleções no frontend. Não há isolamento de usuários nem expiração por imagem. Reiniciar o processo descarta os registros em memória.

## Parâmetros

O servidor aplica uma lista explícita de ajustes aos parâmetros do runtime: filme, papel, espaço de entrada, decodificação, exposição, filtros do ampliador, grão, halation e dispersão. A prévia define `settings.preview_mode = True` e `preview_max_size = 1000`. O motor decide quais efeitos esse modo desativa.

## Limites da implementação

O servidor é destinado ao computador local. Não inclui autenticação, HTTPS, persistência ou infraestrutura para publicação na internet. Dependências científicas são importadas quando necessárias: a página e a biblioteca de perfis podem ser servidas sem instalar o motor completo, mas uploads e simulações exigem essas dependências.

O desenho e os endpoints ainda podem mudar durante a validação inicial.
