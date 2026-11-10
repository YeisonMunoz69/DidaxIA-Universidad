"""
El adaptador HTTP · ADR-009.

Recibe el turno, lo traduce al dominio, lo pasa al orquestador y emite la
respuesta por partes.

LO QUE ESTE MODULO NO HACE, y es lo que lo mantiene delgado: no decide el nivel
de ayuda, no juzga si algo está verificado, no interpreta matemática. Todo eso
pertenece al dominio. Aquí solo se traduce y se transporta.

El contrato de lo que cruza está en 08-Contrato-del-Turno.md, y se escribió
ANTES que este adaptador. En hexagonal el puerto lo define el dominio y el
adaptador se conforma; derivar el contrato de lo que este archivo devolviera
sería invertirlo.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

"""
