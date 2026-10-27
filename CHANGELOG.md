# Histórico de alterações web

Este arquivo registra as mudanças locais sobre a cópia do Spektrafilm 0.3.3. A versão do motor e do pacote Python continua sendo 0.3.3; ainda não há uma versão web independente publicada.

## Não lançado

### Limpeza integral do histórico

- Histórico sanitizado desde o primeiro commit, mantendo a topologia de commits e merges.
- Caminhos locais do exemplo e dos metadados TIFF removidos também das versões antigas.
- Identidade dos commits do responsável pela interface normalizada para usuário público e e-mail GitHub `noreply`.
- Conteúdo funcional atual preservado durante a reescrita.

### Limpeza para publicação

- Remoção de arquivos de metadados do macOS do checkout e novas exclusões no `.gitignore`.
- Exemplo de simulação com caminho relativo ao projeto, sem diretórios pessoais fixos.
- Remoção de caminho local nos metadados da imagem de teste TIFF, preservando os pixels e seu formato.
- Exclusão de estados pessoais da GUI, configurações locais, credenciais, logs e ambientes gerados do versionamento.

### Estimativa de tempo

- Tempo decorrido e estimativa restante nas prévias e renderizações.
- Histórico limitado da sessão com mediana de tempos por etapa e configuração comparável.
- Estados de aprendizado e recálculo quando faltam dados ou uma etapa excede o previsto.
- Falhas excluídas do aprendizado; nenhuma extrapolação de tempo a partir do percentual da barra.
- Testes de relógio controlado, histórico e apresentação dos tempos na interface.

### Correções e diagnóstico do progresso

- Verificação de compatibilidade frontend/backend antes de importar e renderizar.
- Detecção de sessão reiniciada e instruções para reabrir imagens.
- Limite de três falhas consecutivas nas consultas de importação, evitando polling indefinido de jobs ausentes.
- Intervalo de consultas ajustado para um segundo.
- Log rotativo em arquivo e terminal, com etapas, tempo decorrido, tracebacks e erros do navegador.
- Opções `--log-file` e `--debug`; consultas de progresso omitidas no log padrão.
- Testes de regressão para backend antigo, incompatibilidade, jobs ausentes e reinício do servidor.

### Progresso de importação e renderização

- Barra com percentual por etapas, arquivo atual/total, conclusão e falhas.
- Progresso de recebimento, leitura, conversão de cor e miniatura via polling do upload.
- Callback opcional de progresso do runtime, com etapas de filme, impressão e digitalização.
- Status de gravação de PNG/JPEG/TIFF e conclusão visual após carregar o resultado.
- Testes de polling concorrente, falhas e estados assíncronos da interface.
- Upload, prévia e renderização HTTP verificados com imagem sintética RGB de 32 × 32; exportações verificadas, incluindo TIFF de 16 bits.

### Interface web inicial

- Novo pacote `spektrafilm_web` e comando `spektrafilm-web`.
- Servidor HTTP em loopback com uploads, catálogo de perfis, jobs e arquivos temporários.
- Interface em português com biblioteca de filmes/papéis, imagens da sessão, comparação e zoom.
- Ajustes de exposição, filtros do ampliador, grão, halation e dispersão.
- Integração com `init_params`, `simulate_preview` e `simulate` do runtime.
- Exportação de prévia PNG e resultado completo PNG/JPEG/TIFF.
- Cinco testes leves de contratos HTTP e parâmetros.

### Preparação do repositório

- README próprio da aplicação web e preservação do README recebido em `README.upstream.md`.
- Documentação de arquitetura, API, desenvolvimento e contribuição.
- Workflow de verificações web sem dependências científicas.
- Exclusões locais adicionais no `.gitignore`.

### Validação pendente

- Validação com fotografias e arquivos RAW/TIFF/EXR de diferentes origens.
- Inspeção visual e teste de interação no navegador.
- Compatibilidade de leitura de arquivos reais e conferência das exportações.

Não foram feitas alterações locais nos perfis JSON ou nos modelos físicos para implementar a interface web.
