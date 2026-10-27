# Spektrafilm Web

Interface web local, em português, para explorar simulações de fotografia analógica com o motor Python do [spektrafilm](https://github.com/andreavolpato/spektrafilm), de Andrea Volpato.

Escolha filme e papel, ajuste exposição e cor, compare o resultado com o original e exporte a imagem pelo navegador. O processamento acontece no seu computador.

**Estado:** implementação inicial. Os testes do servidor HTTP e a sintaxe do JavaScript foram verificados. A simulação completa e a interface no navegador ainda precisam de validação ponta a ponta.

## Recursos

- Biblioteca pesquisável com os perfis de filmes e papéis incluídos no motor.
- Importação de JPEG, PNG, TIFF, EXR e formatos RAW compatíveis com rawpy/LibRaw.
- Lista de imagens da sessão, zoom e comparação antes/depois.
- Exposição, filtros amarelo/magenta, grão, halation e dispersão.
- Prévia reduzida e renderização em resolução completa.
- Exportação PNG e JPEG de 8 bits e TIFF de 16 bits em sRGB.

## Instalação

É necessário **Python 3.13**. O projeto inclui dependências científicas e bibliotecas nativas de imagem; a instalação pode variar conforme sistema e arquitetura. Node.js é opcional e usado apenas para verificar a sintaxe do frontend.

Na pasta do projeto:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
spektrafilm-web
```

No Windows, crie o ambiente com `py -3.13 -m venv .venv` e ative no PowerShell com `.venv\Scripts\Activate.ps1`. Os dois últimos comandos são os mesmos.

Abra **http://127.0.0.1:8765**. Para escolher outra porta:

```sh
spektrafilm-web --port 8766
```

Encerre com `Ctrl+C` no terminal. A instalação também preserva os comandos `spektrafilm` (desktop Qt/napari) e `spektrafilm-lut` (criação de LUTs). O nome do pacote Python continua sendo `spektrafilm`.

## Como usar

1. Abra uma imagem ou arraste arquivos para a área central.
2. Escolha filme e papel na biblioteca.
3. Ajuste exposição, cor e textura.
4. Clique em **Prévia** para uma simulação com até 1000 pixels no maior lado.
5. Use **Renderizar** para incluir grão e efeitos completos em resolução original.
6. Compare com o original e clique em **Exportar**.

A primeira simulação pode demorar por causa das compilações do Numba. Alterações nos ajustes exigem uma nova prévia ou renderização; o resultado anterior permanece disponível até ser substituído.

### Cor e formatos

| Entrada | Interpretação inicial |
| --- | --- |
| JPEG / PNG | sRGB com curva codificada |
| TIFF / EXR | ProPhoto RGB linear |
| RAW | Demosaico com balanço da câmera e saída sRGB linear |

Confira **Avançado** para ajustar espaço e decodificação da entrada. Perfis ICC embutidos não são interpretados automaticamente nesta interface. Todas as exportações usam sRGB; metadados EXIF da origem não são copiados.

## Sessão local e limites

O servidor escuta em `127.0.0.1` e foi feito para uma sessão local de navegador. Não há envio das imagens para serviços externos, contas de usuário ou persistência de projetos.

- Limite de 256 MiB por upload e uma simulação por vez.
- Imagens decodificadas ficam em memória; originais de upload são removidos após a leitura.
- Prévias e resultados ficam em uma pasta temporária da sessão.
- Ao encerrar normalmente o servidor, os arquivos temporários são removidos. Um encerramento forçado pode deixar arquivos para limpeza manual.
- A prévia desativa grão e alguns efeitos dispendiosos do motor. Sua exportação é PNG reduzido.
- Renderizações completas e várias imagens grandes podem consumir muita memória e disco.
- Não há progresso percentual, cancelamento, processamento em lote automático ou recuperação de sessão.

## Documentação

- [Guia da interface](src/spektrafilm_web/README.md)
- [Arquitetura](docs/architecture.md)
- [API HTTP local](docs/api.md)
- [Desenvolvimento e verificações](docs/development.md)
- [Contribuições](CONTRIBUTING.md)
- [Histórico das alterações web](CHANGELOG.md)
- [Documentação original do Spektrafilm](README.upstream.md)

## Verificação rápida

Estes testes não exigem instalar as dependências científicas:

```sh
PYTHONPATH=src python3.13 -m unittest discover -s tests/web -v
node --check src/spektrafilm_web/static/app.js
```

No PowerShell, configure `$env:PYTHONPATH = 'src'` e execute `python -m unittest discover -s tests/web -v`.

## Origem e licenças

**Film modeling powered by spektrafilm**, de Andrea Volpato. Esta cópia contém o motor, a GUI desktop e o criador de LUTs do projeto original, além da interface web local adicionada neste trabalho. Não é uma interface oficial do autor original.

O código mantém a [licença GPLv3](LICENSE). Os perfis e seus derivados têm condições próprias descritas em [SPEKTRAFILM_LICENSE.txt](SPEKTRAFILM_LICENSE.txt); ativos de terceiros preservam suas atribuições. Consulte [CITATION.cff](CITATION.cff) para citar o motor original. As alterações web estão registradas separadamente no [changelog](CHANGELOG.md).
