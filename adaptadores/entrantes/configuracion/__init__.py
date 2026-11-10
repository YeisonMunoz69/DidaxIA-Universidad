"""
Umbrales externos · RF-ADM-06 · RI-13.

Los valores que el OE4 tiene que calibrar viven fuera del código.

POR QUE IMPORTA: ADR-006 adoptó el umbral de similitud 0,70 y su regla U5 exige
calibrarlo con datos propios. DD-06 fijó la ventana en 3 episodios y declaró el
valor provisional. Si estuvieran incrustados, cada calibración exigiría un
despliegue en mitad del piloto.

LO QUE NO ES CONFIGURABLE: la UNIDAD de las cosas. La ventana se mide en
episodios y no en turnos, y eso es el constructo, no un parámetro. DD-06 lo
dice: cambiar de episodios a turnos sería cambiar lo que se mide.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

"""
