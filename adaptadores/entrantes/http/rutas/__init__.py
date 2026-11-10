"""
rutas/ — Las rutas HTTP, una familia por archivo (`PM-B27`)
===================================================================

`aplicacion.py` declaraba las **33 rutas** del sistema en un solo
`crear_aplicacion()` de 823 líneas. Creció así porque partirlo «no era el
encargo» de ninguna de las sesiones que le fueron añadiendo rutas encima —
`PM-B14`, `PM-B19`, `PM-B21`, `PM-B15`, `DD-26`—, que es exactamente cómo una
deuda de estructura se vuelve invisible: nunca es el problema de nadie.

Qué hay aquí y qué sigue en `aplicacion.py`
--------------------------------------------------
Cada módulo expone **`crear_router(...)`**, que recibe por parámetro lo que
esa familia necesita y devuelve un `APIRouter` con sus rutas ya declaradas.
`aplicacion.py` se queda con lo único que no es de ninguna familia: construir
el estado compartido —los almacenes, la composición del dominio— y registrar
los routers.

**Las dependencias entran por parámetro, no por `Depends` ni por estado
global.** Es la misma disciplina que el dominio ya aplica en todas partes: un
filtro recibe su puerto, `AdaptadorTurno` recibe su orquestador. Que una ruta
declare qué necesita es lo que permite construirla en una prueba sin levantar
la aplicación entera.

⚠️ Los nombres se repiten a propósito, y la carpeta es la que distingue
------------------------------------------------------------------------------
`rutas/clases.py` son **las rutas** de clases; `http/clases.py` es **el
almacén**. Lo mismo con `supervision`, `datos_personales` y `turno`. No es un
descuido: son las dos mitades de la misma familia y llamarlas distinto
—`rutas_de_clases.py`— habría hecho más ruido que el que evita. Un import
absoluto en la cabecera de cada archivo deja claro cuál es cuál.


"""
