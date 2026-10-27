# Histórico de alterações web

Este arquivo registra as mudanças locais sobre a cópia do Spektrafilm 0.3.3. A versão do motor e do pacote Python continua sendo 0.3.3; ainda não há uma versão web independente publicada.

## Não lançado

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

- Simulação ponta a ponta com dependências completas.
- Inspeção visual e teste de interação no navegador.
- Compatibilidade de leitura de arquivos reais e conferência das exportações.

Não foram feitas alterações locais nos perfis JSON ou nos modelos físicos para implementar a interface web.
