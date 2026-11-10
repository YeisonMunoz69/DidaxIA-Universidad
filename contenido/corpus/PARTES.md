# Partes de obra y correspondencia de páginas

> ⚠️ **Antes de modificar nada, lea [`../../ANTES-DE-MODIFICAR.md`](../../ANTES-DE-MODIFICAR.md).**

| | |
|---|---|
| **Qué es** | La tabla que lleva una **página impresa** a la parte de la obra que la contiene y a la **página interna** del archivo |
| **Decisión que lo exige** | `EQ-013` · Fase 5 · el lector debe abrir la página correcta, no suponerla |
| **Quién lo lee** | `adaptadores/salientes/biblioteca/catalogo.py` |
| **Estado** | 🟢 **99 partes Markdown catalogadas, 69 PDF divididos y 4 PDF completos** |
| **Fecha** | 2026-09-05 |

---

## Alcance institucional

La decisión del equipo del 2026-09-05 autoriza estas copias para el piloto y la
presentación del trabajo de grado dentro de DidaxIA. Las rutas HTTP que las
sirven exigen una sesión institucional autenticada; este catálogo no convierte
los archivos en recursos públicos ni permite que el cliente elija una ruta del
servidor.

Los nombres de este archivo corresponden exclusivamente a copias normalizadas.
Los originales de trabajo, revisiones y archivos auxiliares continúan fuera del
catálogo.

---

## Desfase de paginación por obra

`página interna del PDF completo = página impresa + desfase`

| Clave | Desfase | Evidencia |
|---|:---:|---|
| `LOP` | 0 | La hoja 146 del archivo muestra la página impresa 146 |
| `PUR` | +19 | Las hojas 146 y 250 muestran las páginas impresas 127 y 231 |
| `SPI` | +7 | En el rango usado por el corpus, la hoja 234 muestra la página impresa 227 |
| `PIS` | sin medir | No hay PDF completo catalogado; sus PDF divididos se localizan directamente |
| `LEI` | +22 | Las hojas 24, 253 y 309 muestran las páginas impresas 2, 231 y 287 |

`SWO` permanece fuera del corpus y no tiene rutas servibles.

---

## Archivo del PDF completo por obra

| Clave | Archivo |
|---|---|
| `LOP` | lop.pdf |
| `PUR` | pur.pdf |
| `LEI` | lei.pdf |
| `SPI` | spi.pdf |
| `PIS` | — |

`PIS` dispone de las 30 partes PDF catalogadas, pero en el lote recibido no
existe un ejemplar completo independiente. El sistema lo informa como recurso
no catalogado en vez de inventar un nombre.

---

## Partes por obra

El identificador es `CLAVE:nombre`. Los archivos son nombres simples dentro
del directorio catalogado de cada obra; nunca son rutas aportadas por el
navegador.

| Identificador | Obra | Título | Impresa inicial | Impresa final | Markdown | PDF |
|---|---|---|---:|---:|---|---|
| LEI:1-1 | LEI | Sección 1.1 | 2 | 12 | 1_1.md | — |
| LEI:1-2 | LEI | Sección 1.2 | 12 | 20 | 1_2.md | — |
| LEI:1-3 | LEI | Sección 1.3 | 20 | 28 | 1_3.md | — |
| LEI:1-4 | LEI | Sección 1.4 | 28 | 38 | 1_4.md | — |
| LEI:1-5 | LEI | Sección 1.5 | 38 | 48 | 1_5.md | — |
| LEI:1-6 | LEI | Sección 1.6 | 49 | 54 | 1_6.md | — |
| LEI:1-7 | LEI | Sección 1.7 | 55 | 66 | 1_7.md | — |
| LEI:1-8 | LEI | Sección 1.8 | 67 | 76 | 1_8.md | — |
| LEI:1-9 | LEI | Sección 1.9 | 76 | 84 | 1_9.md | — |
| LEI:1-10 | LEI | Sección 1.10 | 85 | 93 | 1_10.md | — |
| LEI:2-1 | LEI | Sección 2.1 | 101 | 109 | 2_1.md | — |
| LEI:2-2 | LEI | Sección 2.2 | 109 | 118 | 2_2.md | — |
| LEI:2-3 | LEI | Sección 2.3 | 118 | 122 | 2_3.md | — |
| LEI:2-4 | LEI | Sección 2.4 | 123 | 132 | 2_4.md | — |
| LEI:2-5 | LEI | Sección 2.5 | 132 | 145 | 2_5.md | — |
| LEI:2-6 | LEI | Sección 2.6 | 145 | 152 | 2_6.md | — |
| LEI:2-7 | LEI | Sección 2.7 | 152 | 162 | 2_7.md | — |
| LEI:2-8 | LEI | Sección 2.8 | 162 | 172 | 2_8.md | — |
| LEI:2-9 | LEI | Sección 2.9 | 172 | 182 | 2_9.md | — |
| LEI:2-10 | LEI | Sección 2.10 | 182 | 190 | 2_10.md | — |
| LEI:3-1 | LEI | Sección 3.1 | 198 | 206 | 3_1.md | — |
| LEI:3-2 | LEI | Sección 3.2 | 207 | 214 | 3_2.md | — |
| LEI:3-3 | LEI | Sección 3.3 | 215 | 222 | 3_3.md | — |
| LEI:3-4 | LEI | Sección 3.4 | 223 | 230 | 3_4.md | — |
| LEI:3-5 | LEI | Sección 3.5 | 231 | 242 | 3_5.md | — |
| LEI:3-6 | LEI | Sección 3.6 | 242 | 248 | 3_6.md | — |
| LEI:3-7 | LEI | Sección 3.7 | 249 | 260 | 3_7.md | — |
| LEI:3-8 | LEI | Sección 3.8 | 260 | 266 | 3_8.md | — |
| LEI:3-9 | LEI | Sección 3.9 | 266 | 274 | 3_9.md | — |
| LEI:3-10 | LEI | Sección 3.10 | 275 | 287 | 3_10.md | — |
| PIS:1 | PIS | Parte 1 | 7 | 15 | 1.md | 1.pdf |
| PIS:2 | PIS | Parte 2 | 16 | 27 | 2.md | 2.pdf |
| PIS:3 | PIS | Parte 3 | 28 | 38 | 3.md | 3.pdf |
| PIS:4 | PIS | Parte 4 | 39 | 50 | 4.md | 4.pdf |
| PIS:5 | PIS | Parte 5 | 51 | 67 | 5.md | 5.pdf |
| PIS:6 | PIS | Parte 6 | 69 | 77 | 6.md | 6.pdf |
| PIS:7 | PIS | Parte 7 | 78 | 87 | 7.md | 7.pdf |
| PIS:8 | PIS | Parte 8 | 88 | 99 | 8.md | 8.pdf |
| PIS:9 | PIS | Parte 9 | 100 | 110 | 9.md | 9.pdf |
| PIS:10 | PIS | Parte 10 | 111 | 121 | 10.md | 10.pdf |
| PIS:11 | PIS | Parte 11 | 122 | 131 | 11.md | 11.pdf |
| PIS:12 | PIS | Parte 12 | 132 | 140 | 12.md | 12.pdf |
| PIS:13 | PIS | Parte 13 | 141 | 157 | 13.md | 13.pdf |
| PIS:14 | PIS | Parte 14 | 158 | 165 | 14.md | 14.pdf |
| PIS:15 | PIS | Parte 15 | 167 | 175 | 15.md | 15.pdf |
| PIS:16 | PIS | Parte 16 | 176 | 187 | 16.md | 16.pdf |
| PIS:17 | PIS | Parte 17 | 188 | 200 | 17.md | 17.pdf |
| PIS:18 | PIS | Parte 18 | 201 | 213 | 18.md | 18.pdf |
| PIS:19 | PIS | Parte 19 | 214 | 222 | 19.md | 19.pdf |
| PIS:20 | PIS | Parte 20 | 223 | 232 | 20.md | 20.pdf |
| PIS:21 | PIS | Parte 21 | 233 | 240 | 21.md | 21.pdf |
| PIS:22 | PIS | Parte 22 | 242 | 254 | 22.md | 22.pdf |
| PIS:23 | PIS | Parte 23 | 255 | 267 | 23.md | 23.pdf |
| PIS:24 | PIS | Parte 24 | 269 | 278 | 24.md | 24.pdf |
| PIS:25 | PIS | Parte 25 | 279 | 289 | 25.md | 25.pdf |
| PIS:26 | PIS | Parte 26 | 290 | 299 | 26.md | 26.pdf |
| PIS:27 | PIS | Parte 27 | 300 | 308 | 27.md | 27.pdf |
| PIS:28 | PIS | Parte 28 | 309 | 323 | 28.md | 28.pdf |
| PIS:29 | PIS | Parte 29 | 324 | 336 | 29.md | 29.pdf |
| PIS:30 | PIS | Parte 30 | 337 | 371 | 30.md | 30.pdf |
| PUR:0-1-0-3 | PUR | Secciones 0-1-0-3 | 1 | 24 | 0-1_0-3.md | 0-1_0-3.pdf |
| PUR:0-4-0-6 | PUR | Secciones 0-4-0-6 | 24 | 40 | 0-4_0-6.md | 0-4_0-6.pdf |
| PUR:0-7-0-8 | PUR | Secciones 0-7-0-8 | 41 | 54 | 0-7_0-8.md | 0-7_0-8.pdf |
| PUR:1-1-1-4 | PUR | Secciones 1-1-1-4 | 55 | 76 | 1-1_1-4.md | 1-1_1-4.pdf |
| PUR:1-5-2-1 | PUR | Secciones 1-5-2-1 | 77 | 99 | 1-5_2-1.md | 1-5_2-1.pdf |
| PUR:2-2-2-5 | PUR | Secciones 2-2-2-5 | 100 | 124 | 2-2_2-5.md | 2-2_2-5.pdf |
| PUR:2-6-2-10 | PUR | Secciones 2-6-2-10 | 125 | 150 | 2-6_2-10.md | 2-6_2-10.pdf |
| SPI:1 | SPI | Parte 1 | 3 | 26 | 1.md | 1.pdf |
| SPI:2 | SPI | Parte 2 | 27 | 45 | 2.md | 2.pdf |
| SPI:3 | SPI | Parte 3 | 49 | 70 | 3.md | 3.pdf |
| SPI:4 | SPI | Parte 4 | 71 | 81 | 4.md | 4.pdf |
| SPI:5 | SPI | Parte 5 | 82 | 97 | 5.md | 5.pdf |
| SPI:6 | SPI | Parte 6 | 98 | 105 | 6.md | 6.pdf |
| SPI:7 | SPI | Parte 7 | 107 | 125 | 7.md | 7.pdf |
| SPI:8 | SPI | Parte 8 | 126 | 140 | 8.md | 8.pdf |
| SPI:9 | SPI | Parte 9 | 141 | 150 | 9.md | 9.pdf |
| SPI:10 | SPI | Parte 10 | 151 | 170 | 10.md | 10.pdf |
| SPI:11 | SPI | Parte 11 | 171 | 192 | 11.md | 11.pdf |
| SPI:12 | SPI | Parte 12 | 197 | 208 | 12.md | 12.pdf |
| SPI:13 | SPI | Parte 13 | 209 | 226 | 13.md | 13.pdf |
| SPI:14 | SPI | Parte 14 | 227 | 234 | 14.md | 14.pdf |
| SPI:15 | SPI | Parte 15 | 235 | 245 | 15.md | 15.pdf |
| SPI:16 | SPI | Parte 16 | 246 | 253 | 16.md | 16.pdf |
| SPI:17 | SPI | Parte 17 | 255 | 274 | 17.md | 17.pdf |
| SPI:18 | SPI | Parte 18 | 275 | 286 | 18.md | 18.pdf |
| SPI:19 | SPI | Parte 19 | 287 | 301 | 19.md | 19.pdf |
| SPI:20 | SPI | Parte 20 | 302 | 316 | 20.md | 20.pdf |
| SPI:21 | SPI | Parte 21 | 317 | 343 | 21.md | 21.pdf |
| SPI:22 | SPI | Parte 22 | 345 | 354 | 22.md | 22.pdf |
| LOP:1 | LOP | Parte 1 | 13 | 42 | 1.md | 1.pdf |
| LOP:2 | LOP | Parte 2 | 42 | 61 | 2.md | 2.pdf |
| LOP:3 | LOP | Parte 3 | 62 | 83 | 3.md | 3.pdf |
| LOP:4 | LOP | Parte 4 | 84 | 93 | 4.md | 4.pdf |
| LOP:5 | LOP | Parte 5 | 94 | 120 | 5.md | 5.pdf |
| LOP:6 | LOP | Parte 6 | 121 | 145 | 6.md | 6.pdf |
| LOP:7 | LOP | Parte 7 | 146 | 173 | 7.md | 7.pdf |
| LOP:8 | LOP | Parte 8 | 174 | 194 | 8.md | 8.pdf |
| LOP:9 | LOP | Parte 9 | 195 | 222 | 9.md | 9.pdf |
| LOP:10 | LOP | Parte 10 | 223 | 227 | 10.md | 10.pdf |

---

## Reglas operativas

- Cada fragmento abre la parte que cubre su rango impreso.
- Los PDF divididos empiezan en su propia hoja 1; el catálogo calcula esa hoja
  sin aplicar el desfase del ejemplar completo.
- El salto al PDF completo sólo se ofrece cuando existe un nombre catalogado y
  un desfase medido.
- Retirar una autorización en `FUENTES.md` vuelve a cerrar el canal sin borrar
  la trazabilidad histórica.

---

*Corpus · `EQ-013` · Fase 5 · IU Colegio Mayor del Cauca*
