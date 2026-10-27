# API HTTP local

Base padrão: `http://127.0.0.1:8765`. Esta API é interna à interface web, sem compromisso de estabilidade entre versões.

Respostas estruturadas usam JSON. Erros retornam `{"error": "mensagem"}`. Arquivos são retornados como imagens. As rotas POST rejeitam `Origin` diferente de `http://127.0.0.1:<porta>` ou `http://localhost:<porta>`; clientes sem esse cabeçalho também são aceitos. Não há suporte a clientes web de outra origem.

## Rotas

| Método | Rota | Função |
| --- | --- | --- |
| GET | `/api/profiles` | Lista informações dos perfis incluídos |
| POST | `/api/upload` | Importa uma imagem |
| POST | `/api/render` | Agenda uma simulação |
| GET | `/api/jobs/{id}` | Consulta o estado de um job |
| GET | `/media/{arquivo}` | Obtém uma imagem gerada na sessão |

### Perfis

`GET /api/profiles` retorna um array com os campos de `info` de cada perfil e um `id` derivado do nome do JSON. Use `support: "film"` para filmes e `support: "paper"` para papéis. Exemplos de IDs: `kodak_portra_400` e `kodak_portra_endura`.

### Upload

Envie o corpo como bytes do arquivo, sem multipart, com o cabeçalho `X-Filename`. O frontend aplica `encodeURIComponent` ao nome; atualmente o backend usa o valor desse cabeçalho sem decodificá-lo. A extensão deve estar presente.

```sh
curl --data-binary @foto.jpg \
  -H 'X-Filename: foto.jpg' \
  http://127.0.0.1:8765/api/upload
```

Resposta HTTP 200, com IDs e dimensões dependentes do arquivo:

```json
{
  "id": "<image-id>",
  "name": "foto.jpg",
  "width": 6000,
  "height": 4000,
  "url": "/media/<image-id>-original.png",
  "space": "sRGB",
  "encoded": true
}
```

Extensões aceitas: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.exr`, `.nef`, `.cr2`, `.cr3`, `.arw`, `.dng`, `.raf`, `.rw2`, `.orf`. A leitura RAW depende do suporte da biblioteca para o arquivo específico. Limite: 268435456 bytes por requisição.

### Simulação

`POST /api/render` recebe `Content-Type: application/json`. `image`, `film` e `paper` devem corresponder à sessão e aos perfis existentes.

```json
{
  "image": "<image-id>",
  "film": "kodak_portra_400",
  "paper": "kodak_portra_endura",
  "mode": "preview",
  "space": "sRGB",
  "encoded": true,
  "exposure": 0,
  "yellow": 0,
  "magenta": 0,
  "grain": true,
  "grain_size": 0.2,
  "grain_blur": 0.65,
  "halation": 1,
  "scatter": 1
}
```

HTTP 202 retorna `{"job": "<job-id>"}`. HTTP 409 indica que já existe uma simulação em andamento. A aceitação não garante sucesso: validações do filme, papel e parâmetros ocorrem na thread, e suas falhas aparecem no estado do job.

| Campo opcional | Padrão | Valores |
| --- | --- | --- |
| `mode` | prévia | `"full"` ativa resolução completa; os demais valores usam prévia |
| `space` | Detectado no upload | `sRGB`, `ProPhoto RGB`, `Adobe RGB (1998)`, `Display P3`, `ACES2065-1` |
| `encoded` | Detectado no upload | Booleano |
| `exposure` | 0 | −3 a 3 EV |
| `yellow`, `magenta` | 0 | −50 a 50 |
| `grain` | true | Booleano |
| `grain_size` | 0.2 | 0.01 a 2 µm² |
| `grain_blur` | 0.65 | 0 a 2 |
| `halation`, `scatter` | 1 | 0 a 3 |

Use booleanos JSON reais nos campos booleanos. O servidor rejeita valores numéricos não finitos e fora das faixas. A saída é sRGB codificada.

### Consulta do job

Durante o processamento: `{"status": "running"}`.

Quando concluído, HTTP 200:

```json
{
  "status": "done",
  "url": "/media/<job-id>.png",
  "exports": {
    "png": "/media/<job-id>.png",
    "jpg": "/media/<job-id>.jpg",
    "tif": "/media/<job-id>.tif"
  },
  "preview": false
}
```

Prévias retornam `preview: true` e somente `exports.png`. Falhas retornam HTTP 200 com `{"status": "error", "error": "mensagem"}`. Um job inexistente retorna HTTP 404.

### Códigos de erro

| HTTP | Significado |
| --- | --- |
| 400 | Corpo inválido, imagem não aberta, formato inválido ou falha na leitura |
| 403 | Origem de POST rejeitada |
| 404 | Recurso ou job inexistente |
| 409 | Outra simulação em execução |
| 413 | Corpo vazio, tamanho não informado ou maior que o limite |
| 503 | Dependência ausente durante uma requisição, por exemplo no upload |

Dependências ausentes durante a thread de renderização aparecem como `status: "error"`, em vez de HTTP 503.
