# Contribuindo

Este projeto adiciona uma interface web local ao Spektrafilm. A implementação web ainda está em validação inicial.

## Propor uma alteração

1. Descreva o problema ou comportamento desejado em uma issue.
2. Crie uma branch e mantenha o escopo da mudança claro.
3. Execute as verificações relevantes em [Desenvolvimento](docs/development.md).
4. Atualize a documentação e o [changelog](CHANGELOG.md) quando mudar comportamento público.
5. Abra um pull request com o problema, a mudança, as verificações feitas e as limitações restantes.

Para bugs de imagem, informe sistema, Python, formato, espaço de cor, filme, papel, ajustes e mensagem de erro. Use imagens compartilháveis. Para alterações visuais, inclua capturas quando possível, indicando o tamanho da janela.

## Organização

- Interface, uploads e endpoints web: `src/spektrafilm_web`.
- Modelos físicos e processamento: `src/spektrafilm`.
- GUI desktop e LUTs preservam seus próprios módulos.

Mantenha a ciência no runtime e o comportamento de interação na camada web. Evite adicionar dependências de frontend sem uma necessidade concreta. Testes HTTP leves devem continuar executáveis sem as dependências científicas.

## Atribuição

Preserve a autoria e as licenças do Spektrafilm original e dos ativos de terceiros. Não atribua à interface web recursos ou validações que ainda não foram implementados. Ao alterar perfis ou LUTs, siga os requisitos do arquivo `SPEKTRAFILM_LICENSE.txt` e registre as modificações separadamente.
