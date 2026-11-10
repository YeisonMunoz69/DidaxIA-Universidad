"""
El borde del sistema.

EL BORDE ES DONDE SE EJERCEN LAS GARANTIAS, no donde se confía en que el
cliente las respete.

Tres cosas ocurren aquí y en ningún otro sitio:

  1. La SEPARACION POR ROL de RP-17. Si el frontend fuera lo único que oculta
     el modelo del estudiante, bastaría abrir las herramientas del navegador.

  2. La TRADUCCION entre los tipos del borde y los del dominio. La regla N2 de
     las pruebas de arquitectura falla si un tipo del borde se cuela dentro.

  3. La EMISION POR PARTES de DD-11: primero las fases, al final el cuerpo.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

"""
