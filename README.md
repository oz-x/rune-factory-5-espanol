# Rune Factory 5 en español (castellano)

Traducción no oficial al español de España de **Rune Factory 5** (PC/Steam).

## ⚠️ Aviso: traducción hecha con inteligencia artificial

Este parche está hecho **por fans y para fans** de la saga que llevamos años esperando
una traducción al español que nunca llegó. Rune Factory 5 salió en inglés, francés,
alemán, japonés, coreano y chino… pero no en español.

**La traducción se ha generado con inteligencia artificial**, usando el texto oficial en
inglés y, como apoyo, la localización oficial francesa (para el tú/usted, el género y
los matices). Se ha revisado por muestreo y se ha probado en el juego, pero **no** se han
revisado a mano las más de 70.000 líneas. Puede haber errores, frases poco naturales o
alguna concordancia de género incorrecta. Si encuentras alguno, abre un *issue* con la
frase original y la traducida.

No está afiliado ni respaldado por Marvelous, XSEED ni ninguna otra empresa. Necesitas
tu propia copia legal del juego en Steam; este repositorio no incluye ningún archivo del
juego.

## Qué está traducido

- Todo el guion: historia, conversaciones diarias, eventos, citas, bodas, hijos y
  festivales (unas 71.000 líneas).
- Menús, opciones, objetos y sus descripciones, monstruos, lugares, habilidades,
  recetas, encargos, consejos de las pantallas de carga, subtítulos de voces y de
  vídeos, apodos y el comentario de los actores de voz.
- Concordancia con el sexo del protagonista (Ares/Alice) y de los hijos donde el
  español la necesita.

**Sigue en inglés:** el texto dibujado dentro de imágenes (opciones del menú de título,
«PRESS ANY BUTTON», «Loading», algunos rótulos y tutoriales con imagen), el lanzador del
juego y los logros de Steam (los sirve Steam).

## Instalación (fácil)

1. Cierra el juego.
2. Descarga **`RF5-Espanol-Instalador.exe`** de la página de
   [Releases](https://github.com/oz-x/rune-factory-5-espanol/releases/latest).
3. Ábrelo. Busca solo el juego en tus bibliotecas de Steam (si no lo encuentra, pulsa
   **Buscar…** y elige la carpeta `Rune Factory 5`).
4. Pulsa **Instalar traducción**.
5. La traducción ocupa el lugar del inglés: en el lanzador del juego, el idioma del
   sistema (*System Language*) debe ser **English**, que es el que viene por defecto.

Para volver al inglés, abre el instalador y pulsa **Desinstalar**: deja los archivos del
juego exactamente como estaban. Si Steam actualiza o verifica el juego, la traducción se
pierde: vuelve a instalarla.

Windows puede avisar de que el programa no está firmado («Windows protegió su PC»):
pulsa **Más información → Ejecutar de todas formas**.

## Instalación con Python (alternativa)

Con [Python 3](https://www.python.org/downloads/) y `pip install UnityPy`, desde la
carpeta del repositorio:

```
python instalar.py              # busca el juego en Steam
python instalar.py "C:\ruta\al\juego"
python desinstalar.py
```

Para generar el `.exe`: `pip install pyinstaller UnityPy` y ejecutar
`construir_instalador.bat`.

## Cómo funciona

Los textos del juego están en *bundles* de Unity (Addressables) por idioma. El
instalador lee los del inglés de tu copia del juego, sustituye cada texto por su
traducción (solo si el texto inglés coincide con el traducido, comprobado con un
*hash*) y los vuelve a escribir. Guarda los originales en la carpeta `es_backup` del
juego para poder deshacerlo byte a byte.

- `mod/texto/` — textos traducidos (solo español; cada línea lleva el *hash* del
  inglés al que corresponde).
- `tools/` — lectura y escritura de los guiones (`pack.bytes`), las tablas de texto y
  los *bundles*; `tools/build_texts.py` regenera `mod/texto` desde la memoria de
  traducción.

La descripción de los comandos de guion (`tools/adv_commands.json`) procede de
[Grimoire](https://github.com/RF5-Research/Grimoire) (RF5-Research, licencia MIT; ver
`tools/adv_commands.LICENSE`).

## Licencia

El código y los textos de este repositorio se publican bajo licencia [MIT](LICENSE).
Rune Factory 5 y sus textos originales pertenecen a Marvelous Inc.
