[Pagina 93 a 99 del libro]

# REVISIÓN DEL CAPÍTULO 1: FUNCIONES, LÍMITES Y CONTINUIDAD

---

## EJERCICIOS DE EVALUACIÓN Y LÍMITES

En los ejercicios 21 y 22, haga lo siguiente:
* **(a)** Trace la gráfica de $g$ en un rectángulo de inspección conveniente. ¿A qué se parece el comportamiento de $g(t)$ conforme $t$ se aproxima a $0$ mediante valores mayores que $0$? *(Para apreciar la gráfica correspondiente, consulte la página 93 del libro).*
* **(b)** Confirme la respuesta del inciso (a) calculando el $\lim_{t \to 0^{+}} g(t)$.

**21.** 
$$g(t) = \frac{\sin t}{t^{2}}$$

**22.** 
$$g(t) = \frac{\sin 4t}{\cos 3t - 1}$$

---

En los ejercicios 23 y 24, haga lo siguiente:
* **(a)** Trace la gráfica de $h$ en un rectángulo de inspección conveniente. ¿A qué valor parece que se aproxima $h(t)$ conforme $t$ tiende o se acerca a $\frac{\pi}{2}$? *(Para apreciar la gráfica correspondiente, consulte la página 93 del libro).*
* **(b)** Confirme la respuesta del inciso (a) calculando el $\lim_{t \to \pi/2} h(t)$. *(Sugerencia: considere $x = \frac{\pi}{2} - t$).*

**23.** 
$$h(t) = \frac{1 - \sin t}{\frac{\pi}{2} - t}$$

**24.** 
$$h(t) = \frac{\frac{\pi}{2} - t}{\cos t}$$

---

En los ejercicios 25 y 26, haga lo siguiente:
* **(a)** Trace la gráfica de $f$ en un rectángulo de inspección conveniente. ¿A qué valor parece que se aproxima $f(x)$ conforme $x$ tiende o se acerca a $\pi$ mediante valores mayores que $\pi$? *(Para apreciar la gráfica correspondiente, consulte la página 93 del libro).*
* **(b)** Confirme analíticamente la respuesta del inciso (a) calculando $\lim_{x \to \pi^{+}} f(x)$. *(Sugerencia: considere $t = x - \pi$).*

**25.** 
$$f(x) = \frac{\sin x}{x - \pi}$$

**26.** 
$$f(x) = \frac{\tan x}{x - \pi}$$

---

**27.** Si $R(\theta)$ pies es el alcance de un proyectil, entonces:
$$R(\theta) = \frac{v_{0}^{2} \sin 2\theta}{g}, \quad 0 \le \theta \le \frac{\pi}{2}$$
donde $v_{0}\text{ pie/s}$ es la velocidad inicial, $g\text{ pie/s}^{2}$ es la constante de aceleración debida a la gravedad, y $\theta$ es la medida en radianes del ángulo que el cañón forma con la horizontal. Demuestre que $R$ es continua en su dominio.

**28.** Si un cuerpo cuyo peso es de $W$ libras es arrastrado a lo largo de un piso horizontal a una velocidad constante por una fuerza de magnitud $F$ libras y dirigida en un ángulo de $\theta$ radianes con respecto al piso, entonces:
$$F(\theta) = \frac{k W}{k \sin \theta + \cos \theta}$$
donde $k$ es una constante llamada coeficiente de fricción y $0 < k < 1$. Demuestre que $F$ es continua en $\left[0, \frac{\pi}{2}\right]$.

---

En los ejercicios 29 a 32, utilice el teorema de estricción para determinar el límite. En los ejercicios 29 y 30, apoye su respuesta gráficamente.

**29.** 
$$\lim_{x \to 0} \left(x \cos \frac{1}{x}\right)$$

**30.** 
$$\lim_{x \to 0} \left(x^{2} \sin \frac{1}{\sqrt[3]{x}}\right)$$

**31.** 
$$\lim_{x \to 3} g(x) \quad \text{si } |g(x) + 4| < 2(3 - x)^{4} \text{ para toda } x$$

**32.** 
$$\lim_{x \to -2} g(x) \quad \text{si } |g(x) - 3| < 5(x + 2)^{2} \text{ para toda } x$$

---

En los ejercicios 33 y 34, determine el límite si existe y apoye su respuesta gráficamente.

**33.** 
$$\lim_{x \to 0} \frac{\sin(\sin x)}{x}$$

**34.** 
$$\lim_{x \to 0} \left(\sin x \sin \frac{1}{x}\right)$$

---

**35.** Dado que $1 - \cos^{2} x \le f(x) \le x^{2}$ para toda $x$ en el intervalo abierto $\left(-\frac{\pi}{2}, \frac{\pi}{2}\right)$, determine $\lim_{x \to 0} f(x)$.

**36.** Dado que $-\sin x \le f(x) \le 2 + \sin x$ para toda $x$ en el intervalo abierto $(-\pi, 0)$, determine $\lim_{x \to -\pi/2} f(x)$.

---

En los ejercicios 37 a 40, demuestre que la función es continua en su dominio.

**37.** La función tangente.
**38.** La función cotangente.
**39.** La función secante.
**40.** La función cosecante.

---

**41.** Si $|f(x)| \le M$ para toda $x$, donde $M$ es una constante, utilice el teorema de estricción para demostrar que $\lim_{x \to 0} x^{2}f(x) = 0$.

**42.** Considere que $|f(x)| \le M$ para toda $x$, donde $M$ es una constante. Además suponga que $\lim_{x \to a} |g(x)| = 0$. Utilice el teorema de estricción para demostrar que $\lim_{x \to a} f(x)g(x) = 0$.

**43.** Si $|f(x)| \le k|x - a|$ para toda $x \neq a$, donde $k$ es una constante, demuestre que $\lim_{x \to a} f(x) = 0$.

---

**44.** Dada $f(x) = \sin(1/x)$, trace la gráfica de $f$ en cada uno de los siguientes rectángulos de inspección:
* **(a)** $[-2, 2] \times [-2, 2]$
* **(b)** $[-1, 1] \times [-2, 2]$
* **(c)** $[-0.5, 0.5] \times [-2, 2]$
* **(d)** $[-0.25, 0.25] \times [-2, 2]$
* **(e)** $[-0.1, 0.1] \times [-2, 2]$
* **(f)** $[-0.01, 0.01] \times [-2, 2]$
* **(g)** ¿Sospecha que el $\lim_{x \to 0} f(x)$ existe? Si es así, ¿qué número sospecha que es y por qué? O, ¿sospecha que el $\lim_{x \to 0} f(x)$ no existe? Si es así, ¿por qué?

**45.** Haga el ejercicio 44 considerando ahora que $f(x) = \cos \frac{1}{x}$.

**46.** Haga el ejercicio 44 considerando ahora que $f(x) = \tan \frac{1}{x}$.

---

## SUGERENCIAS PARA LA REVISIÓN DEL CAPÍTULO 1

**1.** Defina función y en su definición incluya los conceptos de dominio y contradominio.

**2.** Invente un ejemplo de una función que tenga la propiedad indicada:
* **(a)** El dominio es el conjunto de todos los números reales.
* **(b)** El dominio es el conjunto de todos los números no negativos.
* **(c)** El dominio es el conjunto de todos los números negativos.
* **(d)** El dominio es el conjunto de todos los números reales excepto $0$.
* **(e)** El contradominio es el conjunto de todos los números enteros.

**3.** ¿Qué se entiende por gráfica de una función?

**4.** Invente un ejemplo de una función que tenga la propiedad indicada:
* **(a)** La gráfica de $f$ tiene un "agujero" en $x = 4$, cuando $f(4)$ no está definido.
* **(b)** La gráfica de $f$ tiene un "agujero" en $x = 4$, cuando $f(4)$ está definido.
* **(c)** La función $f$ está definida a trozos para $x < 2$ y $2 \le x$, donde la gráfica de $f$ se rompe en $x = 2$.
* **(d)** La función $f$ está definida a trozos para $x < 2$ y $2 \le x$, donde la gráfica de $f$ no se rompe en $x = 2$.

**5.** Defina la suma, diferencia, producto y cociente de dos funciones $f$ y $g$, y establezca cómo se relaciona el dominio de la función resultante con los dominios de las funciones $f$ y $g$.

**6.** Invente un ejemplo de dos funciones $f$ y $g$, tales que al menos una no sea una función polinomial, y defina $(f+g)(x)$, $(f-g)(x)$, $(f \cdot g)(x)$ y $(f/g)(x)$. Determine los dominios de $f$ y $g$ y los dominios de las funciones resultantes.

**7.** Defina la función compuesta de dos funciones $f$ y $g$, y establezca cómo se relaciona el dominio de la función compuesta con los dominios de las funciones $f$ y $g$.

**8.** Invente un ejemplo de dos funciones $f$ y $g$, tales que al menos una no sea una función polinomial, y defina $(f \circ g)(x)$ y $(g \circ f)(x)$. Determine los dominios de $f$ y $g$, así como los dominios de $f \circ g$ y $g \circ f$.

**9.** ¿Qué se entiende por: **(a)** función par, **(b)** función impar? Describa la simetría de las gráficas de cada uno de estos tipos de funciones.

**10.** Invente un ejemplo de una función, diferente de una polinomial, que sea **(a)** par, **(b)** impar y **(c)** ni par ni impar.

**11.** Defina con precisión, empleando la notación $\epsilon\text{-}\delta$, lo que se entiende por: el límite de $f(x)$ conforme $x$ se aproxima a $a$ es igual a $L$. Ahora establezca en palabras lo que significa sin utilizar la notación $\epsilon\text{-}\delta$ y sin usar las palabras límite y tiende o se aproxima.

**12.** ¿Cómo se utiliza la definición del límite de una función para demostrar que $\lim_{x \to a} f(x) = L$?

**13.** Describa en términos geométricos la relación entre $\epsilon$ y $\delta$ de la definición del límite de una función.

**14.** Invente un ejemplo de una función para la cual:
* **(a)** $f(a)$ no existe, pero $\lim_{x \to a} f(x)$ existe;
* **(b)** $f(a)$ existe, pero $\lim_{x \to a} f(x)$ no existe;
* **(c)** tanto $f(a)$ como $\lim_{x \to a} f(x)$ existen, pero no son iguales.

**15.** ¿Qué se entiende cuando se dice que el límite de una función, cuando existe es único? Establezca el teorema que garantiza este hecho.

**16.** ¿Cómo se utilizan los teoremas de límites para calcular el límite de una función?

**17.** Establezca los teoremas que tratan sobre los límites de la suma, diferencia, producto y cociente de dos funciones.

**18.** ¿Por qué no es preciso el siguiente enunciado: *"El límite de la suma de dos funciones es la suma de sus límites"*? Invente un ejemplo de dos funciones para las cuales el enunciado es incorrecto.

**19.** Invente un ejemplo de dos funciones $f$ y $g$ tales que al menos una no sea una función polinomial, y muestre cómo se aplican los teoremas de la sugerencia 17.

**20.** Defina con precisión, utilizando la notación $\epsilon\text{-}\delta$, cada uno de los siguientes límites laterales: 
* **(a)** $\lim_{x \to a^{+}} f(x) = L$
* **(b)** $\lim_{x \to a^{-}} f(x) = L$

Ahora establezca en palabras lo que significa cada una de estas definiciones sin utilizar la notación $\epsilon\text{-}\delta$ ni usar las palabras límite y tiende o se aproxima.

**21.** ¿Cómo están relacionados los límites laterales y los límites bilaterales?

**22.** ¿Cuándo es necesario emplear los límites laterales para calcular un límite bilateral? Invente un ejemplo para ilustrar su respuesta.

**23.** ¿Cuándo pueden emplearse los límites laterales para demostrar que un límite bilateral no existe? Invente un ejemplo para ilustrar su respuesta.

**24.** Defina con precisión, empleando la notación $\epsilon\text{-}N$, cada una de las siguientes expresiones:
* **(a)** conforme $x$ se aproxima a $a$, $f(x)$ crece sin límite;
* **(b)** conforme $x$ se aproxima a $a$, $f(x)$ decrece sin límite.

Ahora establezca en palabras lo que significa cada una de estas definiciones sin utilizar la notación $\epsilon\text{-}N$ y sin usar las palabras límite, tiende a o se aproxima a, infinito, crece sin límite o decrece sin límite.

**25.** ¿Cómo se evalúa el límite de una función racional para la cual el límite del denominador es cero y el límite del numerador es una constante diferente de cero?

**26.** ¿Qué es la asíntota vertical de la gráfica de una función?

**27.** ¿Cómo puede determinarse cualquier asíntota vertical para la gráfica de una función?

**28.** Invente ejemplos de dos funciones racionales tales que la gráfica de una tenga un agujero en el punto donde $x = 3$ y la otra tenga a la recta $x = 3$ como una asíntota vertical.

**29.** Defina: la función $f$ es continua en el número $a$.

**30.** Invente un ejemplo de una función discontinua en el número $1$, debido a las condiciones indicadas:
* **(a)** $f(1)$ no existe, pero $\lim_{x \to 1} f(x)$ existe;
* **(b)** $f(1)$ existe pero $\lim_{x \to 1} f(x)$ no existe;
* **(c)** tanto $f(1)$ como $\lim_{x \to 1} f(x)$ existen, pero no son iguales.

**31.** ¿Cuál es la diferencia entre discontinuidad esencial y discontinuidad removible?

**32.** Invente un ejemplo de una función que tenga una discontinuidad esencial en $x = 2$. Después invente un ejemplo de una función que tenga una discontinuidad removible en $x = 2$ y muestre cómo puede removerse o eliminarse esta discontinuidad.

**33.** Establezca los teoremas concernientes a la continuidad de funciones polinomiales y racionales. ¿Cómo se aplican estos teoremas para calcular los límites de estas funciones?

**34.** ¿Qué condiciones de continuidad de las funciones $f$ y $g$ son necesarias para que la función compuesta $f \circ g$ sea continua en el número $a$?

**35.** Invente un ejemplo de dos funciones $f$ y $g$ tales que la función compuesta $f \circ g$ sea continua en cada número del intervalo abierto $(-3, 3)$. Muestre que las funciones $f$ y $g$ de su ejemplo cumplen las condiciones de la respuesta de la sugerencia 34.

**36.** Invente un ejemplo de una función que sea discontinua en el número $c$ y que sea continua por la derecha de $c$. Muestre que su función satisface los requerimientos.

**37.** Defina: la función $f$ es continua en el intervalo cerrado $[a, b]$.

**38.** Establezca el teorema del valor intermedio.

**39.** Invente un ejemplo de una función que ilustre el teorema del valor intermedio. Muestre que la hipótesis y la conclusión del teorema son satisfechas por su función.

**40.** Establezca el teorema de estricción. Invente un ejemplo de tres funciones $f$, $g$ y $h$ que satisfagan las hipótesis de este teorema y muestre que se cumple la conclusión.

**41.** Invente un ejemplo de tres funciones $f$, $g$ y $h$ que ilustren cómo se aplica el teorema de estricción para calcular el límite de $g(x)$ cuando los límites de $f(x)$ y $h(x)$ se conocen.

**42.** ¿A qué es igual el $\lim_{t \to 0} \frac{\sin t}{t}$ y cómo se utiliza su valor para demostrar que la función seno es continua en $0$?

**43.** ¿Cómo se emplea la continuidad de la función seno en $0$ para demostrar que la función coseno es continua en $0$?

**44.** ¿Cómo se usa el hecho de que las funciones seno y coseno son continuas en $0$ para demostrar que dichas funciones son continuas en cada número real?

**45.** ¿Cómo se demuestra la continuidad de las otras cuatro funciones trigonométricas a partir de la continuidad de las funciones seno y coseno?

---

## EJERCICIOS DE REPASO PARA EL CAPÍTULO 1

**1.** Dada $f(x) = 4 - x^{2}$, determine:
* **(a)** $f(1)$
* **(b)** $f(-2)$
* **(c)** $f(3)$
* **(d)** $f(x-1)$
* **(e)** $f(x^{2})$
* **(f)** $\frac{f(x+h) - f(x)}{h}, \quad h \neq 0$

**2.** Dada $g(x) = \sqrt{1 - x}$, determine:
* **(a)** $g(1)$
* **(b)** $g(-3)$
* **(c)** $g(x+1)$
* **(d)** $g(1 - x^{2})$
* **(e)** $\frac{g(x+h) - g(x)}{h}, \quad h \neq 0$

---

En los ejercicios 3 a 6, defina las siguientes funciones y determine los dominios de las funciones resultantes: **(a)** $f+g$; **(b)** $f-g$; **(c)** $f \cdot g$; **(d)** $f/g$; **(e)** $g/f$; **(f)** $f \circ g$; **(g)** $g \circ f$.

**3.** 
$$f(x) = \sqrt{x+2}, \quad g(x) = x^{2} - 4$$

**4.** 
$$f(x) = x^{2} - 9, \quad g(x) = \sqrt{x+5}$$

**5.** 
$$f(x) = \frac{1}{x^{2}}, \quad g(x) = \sqrt{x}$$

**6.** 
$$f(x) = \frac{x}{x-1}, \quad g(x) = \frac{1}{x+2}$$

---

En los ejercicios 7 y 8, trace la gráfica de la función y a partir de la gráfica conjeture si la función es par, impar o de ninguno de estos tipos. Después confirme su conjetura analíticamente. *(Para apreciar la gráfica correspondiente, consulte la página 95 del libro).*

**7.** 
* **(a)** $f(x) = 2x^{3} - 3x$
* **(b)** $g(x) = 5x^{4} + 2x^{2} - 1$
* **(c)** $h(x) = 3x^{5} - 2x^{3} + x^{2} - x$
* **(d)** $F(x) = \frac{x^{2}+1}{x^{3}-x}$

**8.** 
* **(a)** $f(x) = \frac{x^{3}-2x}{x^{2}-1}$
* **(b)** $g(x) = \frac{x}{|x|}$
* **(c)** $h(x) = \frac{\sqrt[3]{x}}{x}$
* **(d)** $F(x) = x^{2}\lfloor x \rfloor$

---

En los ejercicios 9 y 10, trace la gráfica de la función y determine su dominio y su contradominio. *(Para apreciar la gráfica correspondiente, consulte la página 95 del libro).*

**9.** 
* **(a)** $f(x) = 4 - 2x$
* **(b)** $g(x) = x^{2} - 4$
* **(c)** $h(x) = \sqrt{x^{2} - 16}$
* **(d)** $F(x) = \sqrt{16 - x^{2}}$
* **(e)** $f(x) = |5 - x|$
* **(f)** $g(x) = 5 - |x|$

**10.** 
* **(a)** $g(x) = 3x + 2$
* **(b)** $f(x) = 9 - x^{2}$
* **(c)** $H(x) = \sqrt{1 - x^{2}}$
* **(d)** $G(x) = \sqrt{x^{2} - 1}$
* **(e)** $g(x) = |x + 4|$
* **(f)** $f(x) = |x| + 4$

---

En los ejercicios 11 a 14, dibuje la gráfica de la función y determine su dominio y su contradominio. *(Para apreciar la gráfica correspondiente, consulte las páginas 95 y 96 del libro).*

**11.** 
* **(a)** $g(x) = \frac{x^{2} - 16}{x + 4}$
* **(b)** 
$$G(x) = \begin{cases} x - 4 & \text{si } x \neq -4 \\ 3 & \text{si } x = -4 \end{cases}$$

**12.** 
* **(a)** $f(x) = \frac{x^{2} + x - 6}{x - 2}$
* **(b)** 
$$F(x) = \begin{cases} x + 3 & \text{si } x \neq 2 \\ 1 & \text{si } x = 2 \end{cases}$$

**13.** 
* **(a)** 
$$F(x) = \begin{cases} 3 - x & \text{si } x < 0 \\ 3 + 2x & \text{si } 0 \le x \end{cases}$$
* **(b)** 
$$h(x) = \begin{cases} x^{2} - 1 & \text{si } x \le 0 \\ x - 1 & \text{si } 0 < x \end{cases}$$

**14.** 
* **(a)** 
$$G(x) = \begin{cases} 3x + 2 & \text{si } x \le 0 \\ 4 - 2x & \text{si } 0 < x \end{cases}$$
* **(b)** 
$$H(x) = \begin{cases} x^{2} & \text{si } x < -1 \\ (x + 2)^{2} & \text{si } -1 \le x \end{cases}$$

---

En los ejercicios 15 a 20, se han dado $f(x)$, $a$, $L$ y $\epsilon$.
* **(a)** Utilice una figura y un argumento semejante a los de los ejemplos de la sección 1.4 para determinar una $\delta > 0$ tal que si $0 < |x - a| < \delta$ entonces $|f(x) - L| < \epsilon$.
* **(b)** Apoye la elección de $\delta$ del inciso (a) con la graficadora.
* **(c)** Confirme analíticamente, empleando las propiedades de las desigualdades, la elección de $\delta$ del inciso (a).

**15.** $f(x) = 2x - 5$; $a = 3$; $L = 1$; $\epsilon = 0.05$
**16.** $f(x) = 3x - 2$; $a = 1$; $L = 1$; $\epsilon = 0.2$
**17.** $f(x) = \frac{x^{2} - 25}{x - 5}$; $a = 5$; $L = 10$; $\epsilon = 0.1$
**18.** $f(x) = \frac{2x^{2} + 9x + 10}{x + 2}$; $a = -2$; $L = 1$; $\epsilon = 0.03$
**19.** $f(x) = x^{2} + 4$; $a = 2$; $L = 8$; $\epsilon = 0.3$
**20.** $f(x) = x^{2} - 3x$; $a = 3$; $L = 0$; $\epsilon = 0.08$

---

En los ejercicios 21 a 26, demuestre que el límite es el número indicado aplicando la definición formal de límite; esto es, para cualquier $\epsilon > 0$, determine una $\delta > 0$ tal que si $0 < |x - a| < \delta$ entonces $|f(x) - L| < \epsilon$.

**21.** 
$$\lim_{x \to 3} (2x - 5) = 1$$

**22.** 
$$\lim_{x \to -2} (8 - 3x) = 14$$

**23.** 
$$\lim_{x \to -1} (3x + 8) = 5$$

**24.** 
$$\lim_{x \to 5} (4x - 11) = 9$$

**25.** 
$$\lim_{x \to -3/4} \frac{16x^{2} - 9}{4x + 3} = -6$$

**26.** 
$$\lim_{x \to 1/3} \frac{1 - 9x^{2}}{1 - 3x} = 2$$

---

En los ejercicios 27 a 34, calcule el límite y, cuando sea apropiado, indique los teoremas de límites empleados.

**27.** 
$$\lim_{x \to 2} (3x^{2} - 4x + 5)$$

**28.** 
$$\lim_{x \to -2} \frac{x^{2} - x - 6}{x^{2} - 5x - 14}$$

**29.** 
$$\lim_{z \to -3} \frac{z^{2} - 9}{z + 3}$$

**30.** 
$$\lim_{h \to 1} \frac{h^{2} - 4}{3h^{3} + 6}$$

**31.** 
$$\lim_{x \to 1/2} \sqrt[3]{\frac{4x^{2} + 4x - 3}{4x^{2} - 1}}$$

**32.** 
$$\lim_{t \to 0} \frac{1 - \sqrt{1 + t}}{t}$$

**33.** 
$$\lim_{t \to 0} \frac{\sqrt{9 - t} - 3}{t}$$

**34.** 
$$\lim_{y \to -4} \sqrt{\frac{5y + 4}{y - 5}}$$

---

En los ejercicios 35 a 42, calcule el límite si existe, y apoye su respuesta trazando la gráfica de la función en un rectángulo de inspección adecuado. *(Para apreciar la gráfica correspondiente, consulte la página 96 del libro).*

**35.** 
$$\lim_{x \to -1} \frac{2x^{2} - x - 3}{3x^{2} + 8x + 5}$$

**36.** 
$$\lim_{y \to 3} \sqrt{\frac{y - 3}{y^{3} - 27}}$$

**37.** 
$$\lim_{x \to 9} \frac{2\sqrt{x} - 6}{x - 9}$$

**38.** 
$$\lim_{y \to 5^{-}} \sqrt{\frac{25 - y^{2}}{y - 5}}$$

**39.** 
$$\lim_{s \to 7} \frac{5 - \sqrt{4 + 3s}}{7 - s}$$

**40.** 
$$\lim_{x \to 0^{-}} \frac{x^{2} - 5}{2x^{3} - 3x^{2}}$$

**41.** 
$$\lim_{x \to 2^{+}} \frac{\lfloor x \rfloor - 1}{\lfloor x \rfloor - x}$$

**42.** 
$$\lim_{x \to 5} \frac{\sqrt{x - 1} - 2}{x - 5}$$

---

En los ejercicios 43 a 48, dibuje la gráfica de la función y calcule el límite indicado si existe; si el límite no existe, establezca la razón. *(Para apreciar la gráfica correspondiente, consulte la página 96 del libro).*

**43.** 
$$f(x) = \begin{cases} x^{2} - 1 & \text{si } x < 3 \\ x + 5 & \text{si } 3 \le x \end{cases}$$
* **(a)** $\lim_{x \to 3^{-}} f(x)$
* **(b)** $\lim_{x \to 3^{+}} f(x)$
* **(c)** $\lim_{x \to 3} f(x)$

**44.** 
$$g(x) = \begin{cases} x - 2 & \text{si } x \le 0 \\ x^{2} - 1 & \text{si } 0 < x \end{cases}$$
* **(a)** $\lim_{x \to 0^{-}} g(x)$
* **(b)** $\lim_{x \to 0^{+}} g(x)$
* **(c)** $\lim_{x \to 0} g(x)$

**45.** 
$$h(t) = \frac{|t - 1|}{t - 1}$$
* **(a)** $\lim_{t \to 1^{-}} h(t)$
* **(b)** $\lim_{t \to 1^{+}} h(t)$
* **(c)** $\lim_{t \to 1} h(t)$

**46.** 
$$f(r) = \begin{cases} |r - 2| & \text{si } r \neq 2 \\ 3 & \text{si } r = 2 \end{cases}$$
* **(a)** $\lim_{r \to 2^{-}} f(r)$
* **(b)** $\lim_{r \to 2^{+}} f(r)$
* **(c)** $\lim_{r \to 2} f(r)$

**47.** 
$$g(x) = \begin{cases} x - 4 & \text{si } x < -4 \\ \sqrt{16 - x^{2}} & \text{si } -4 \le x \le 4 \\ 4 - x & \text{si } 4 < x \end{cases}$$
* **(a)** $\lim_{x \to -4^{-}} g(x)$
* **(b)** $\lim_{x \to -4^{+}} g(x)$
* **(c)** $\lim_{x \to -4} g(x)$
* **(d)** $\lim_{x \to 4^{-}} g(x)$
* **(e)** $\lim_{x \to 4^{+}} g(x)$
* **(f)** $\lim_{x \to 4} g(x)$

**48.** 
$$h(x) = \begin{cases} x^{2} - 4 & \text{si } x \le 2 \\ 2 - x & \text{si } 2 < x \le 4 \\ x - 2 & \text{si } 4 < x \end{cases}$$
* **(a)** $\lim_{x \to 2^{-}} h(x)$
* **(b)** $\lim_{x \to 2^{+}} h(x)$
* **(c)** $\lim_{x \to 2} h(x)$
* **(d)** $\lim_{x \to 4^{-}} h(x)$
* **(e)** $\lim_{x \to 4^{+}} h(x)$
* **(f)** $\lim_{x \to 4} h(x)$

---

En los ejercicios 49 a 54, calcule el límite y apoye su respuesta gráficamente.

**49.** **(a)** $\lim_{x \to -4^{-}} \frac{2x}{16 - x^{2}}$ \quad **(b)** $\lim_{x \to -4^{+}} \frac{2x}{16 - x^{2}}$

**50.** **(a)** $\lim_{x \to -2^{-}} \frac{x - 1}{x^{2} - 4}$ \quad **(b)** $\lim_{x \to -2^{+}} \frac{x - 1}{x^{2} - 4}$

**51.** **(a)** $\lim_{x \to 4^{-}} \frac{2x}{16 - x^{2}}$ \quad **(b)** $\lim_{x \to 4^{+}} \frac{2x}{16 - x^{2}}$

**52.** **(a)** $\lim_{x \to 2^{-}} \frac{x - 1}{x^{2} - 4}$ \quad **(b)** $\lim_{x \to 2^{+}} \frac{x - 1}{x^{2} - 4}$

**53.** **(a)** $\lim_{t \to 5^{-}} \frac{\sqrt{t - 4}}{(t - 5)^{2}}$ \quad **(b)** $\lim_{t \to 5^{+}} \frac{4 - t}{\sqrt{t - 5}}$

**54.** **(a)** $\lim_{x \to -2^{-}} \frac{\sqrt{3 - x}}{(x + 2)^{2}}$ \quad **(b)** $\lim_{x \to -2^{+}} \frac{x - 3}{\sqrt{x + 2}}$

---

En los ejercicios 55 a 62, haga lo siguiente:
* **(a)** Trace la gráfica de $f$ en un rectángulo de inspección adecuado. ¿A qué número parece que se aproxima $f(x)$ conforme $x$ tiende o se acerca a $0$? *(Para apreciar la gráfica correspondiente, consulte la página 96 del libro).*
* **(b)** Confirme la respuesta del inciso (a) analíticamente, calculando el límite $\lim_{x \to 0} f(x)$.

**55.** 
$$f(x) = \frac{x}{\sin 3x}$$

**56.** 
$$f(x) = \frac{x^{2}}{1 - \cos x}$$

**57.** 
$$f(x) = \frac{\sin 5x}{\sin 2x}$$

**58.** 
$$f(x) = \frac{1 - \cos 3x}{\sin 3x}$$

**59.** 
$$f(x) = \frac{1 - \cos^{2} x}{x}$$

**60.** 
$$f(x) = \frac{4x}{\tan x}$$

**61.** 
$$f(x) = \frac{\csc 3x}{\cot x}$$

**62.** 
$$f(x) = \frac{2x^{2} - 3x}{2 \sin x}$$

---

En los ejercicios 63 a 68, determine las asíntotas verticales de la gráfica de la función y utilícelas para dibujar la gráfica. *(Para apreciar la gráfica correspondiente, consulte las páginas 96 y 97 del libro).*

**63.** 
$$f(x) = \frac{x + 8}{x - 4}$$

**64.** 
$$f(x) = \frac{3x - 2}{x - 2}$$

**65.** 
$$g(x) = 1 - \frac{1}{x^{2}}$$

**66.** 
$$f(x) = \frac{-2}{x^{2} - x - 6}$$

**67.** 
$$f(x) = \frac{5x^{2}}{x^{2} - 4}$$

**68.** 
$$h(x) = \frac{2x^{2}}{x^{2} - 1}$$

---

En los ejercicios 69 a 74, dibuje la gráfica de la función; después observe dónde se rompe la gráfica, determine los valores de $x$ en los que la función es discontinua y muestre por qué la definición de continuidad no se satisface en cada discontinuidad. *(Para apreciar la gráfica correspondiente, consulte la página 97 del libro).*

**69.** 
$$f(x) = \frac{x + 2}{x^{2} + x - 2}$$

**70.** 
$$g(x) = \frac{x^{4} - 1}{x^{2} - 1}$$

**71.** 
$$g(x) = \begin{cases} 2x + 1 & \text{si } x \le -2 \\ x - 2 & \text{si } -2 < x \le 2 \\ 2 - x & \text{si } 2 < x \end{cases}$$

**72.** 
$$F(x) = \begin{cases} |4 - x| & \text{si } x \neq 4 \\ 3 & \text{si } x = 4 \end{cases}$$

**73.** 
$$h(x) = \begin{cases} \frac{1}{x} & \text{si } x \le 1 \\ x^{2} - 1 & \text{si } 1 < x \end{cases}$$

**74.** 
$$f(x) = \begin{cases} x^{2} - 9 & \text{si } x < 3 \\ 5 & \text{si } x = 3 \\ 9 - x^{2} & \text{si } 3 < x \end{cases}$$

---

En los ejercicios 75 a 78, demuestre que la función es discontinua en el número $a$. Después determine si la discontinuidad es esencial o removible. Si la discontinuidad es removible, redefina $f(a)$ de modo que la discontinuidad sea eliminada.

**75.** 
$$f(x) = \frac{x^{2} + 2x - 8}{x^{2} + 3x - 4}; \quad a = -4$$

**76.** 
$$f(x) = \begin{cases} 4 - x^{2} & \text{si } x < 1 \\ 2x + 3 & \text{si } 1 \le x \end{cases}; \quad a = 1$$

**77.** 
$$f(x) = \begin{cases} \frac{1}{x-2} & \text{si } x \neq 2 \\ 3 & \text{si } x = 2 \end{cases}; \quad a = 2$$

**78.** 
$$f(x) = \frac{|2x - 6|}{2x - 6}; \quad a = 3$$

---

En los ejercicios 79 a 82, la función es discontinua en el número $a$.
* **(a)** Trace la gráfica de $f$, la cual se rompe en el punto donde $x = a$. ¿Es esencial o removible la discontinuidad? Si parece que es removible, especule acerca de cómo debe redefinirse $f(a)$ de modo que la discontinuidad sea eliminada. *(Para apreciar la gráfica correspondiente, consulte la página 97 del libro).*
* **(b)** Confirme la respuesta del inciso (a) analíticamente.

**79.** 
$$f(x) = \frac{|4 - x| - 3}{x - 1}; \quad a = 1$$

**80.** 
$$f(x) = \frac{2 - \sqrt{x + 4}}{x}; \quad a = 0$$

**81.** 
$$f(x) = \frac{x}{\sqrt{x + 9} - 3}; \quad a = 0$$

**82.** 
$$f(x) = \frac{x - 1}{\sqrt[3]{x} - 1}; \quad a = 1$$

---

En los ejercicios 83 y 84, **(a)** defina $f \circ g$ y **(b)** determine los números en los que $f \circ g$ es continua y establezca la razón.

**83.** 
* **(a)** $f(x) = \sqrt{x}$ y $g(x) = 25 - x^{2}$
* **(b)** $f(x) = \frac{\sqrt{x^{2} - 4}}{\sqrt{3 - x}}$ y $g(x) = |x|$
* **(c)** $f(x) = \text{sgn}(x)$ y $g(x) = x^{2} - 1$

**84.** 
* **(a)** $f(x) = \sqrt{x}$ y $g(x) = x^{2} - 25$
* **(b)** $f(x) = \sqrt{x + 1}$ y $g(x) = \frac{1}{x - 3}$
* **(c)** $f(x) = \text{sgn}(x)$ y $g(x) = x^{2} - x$

---

En los ejercicios 85 y 86, determine los valores de las constantes $a$ y $b$ que hagan a la función continua en todo número y dibuje la gráfica de la función resultante. *(Para apreciar la gráfica correspondiente, consulte la página 97 del libro).*

**85.** 
$$f(x) = \begin{cases} 2x + 1 & \text{si } x \le 3 \\ ax + b & \text{si } 3 < x < 5 \\ x^{2} + 2 & \text{si } 5 \le x \end{cases}$$

**86.** 
$$f(x) = \begin{cases} 3x + 6a & \text{si } x < -3 \\ 3ax - 7b & \text{si } -3 \le x \le 3 \\ x - 12b & \text{si } 3 < x \end{cases}$$

---

**87.** Sea $f$ la función definida por:
$$f(x) = \begin{cases} 1 & \text{si } x \text{ es un número entero} \\ 0 & \text{si } x \text{ no es un número entero} \end{cases}$$
* **(a)** Dibuje la gráfica de $f$. *(Para apreciar la gráfica correspondiente, consulte la página 97 del libro).*
* **(b)** ¿Para qué valores de $a$ existe el límite $\lim_{x \to a} f(x)$?
* **(c)** ¿En qué números reales es continua $f$?

**88.** Proporcione un ejemplo de una función $f$ para la cual $\lim_{x \to 0} |f(x)|$ exista pero que $\lim_{x \to 0} f(x)$ no exista.

---

En los ejercicios 89 a 92, determine el intervalo más grande (o unión de intervalos), donde la función es continua. Apoye la respuesta con la graficadora.

**89.** 
* **(a)** $f(x) = \sqrt{25 - x^{2}}$
* **(b)** $g(x) = \sqrt{x^{2} - 25}$

**90.** 
* **(a)** $f(x) = \frac{|x| + 1}{|x| - 1}$
* **(b)** $g(x) = \frac{\sqrt{9 - x^{2}}}{x - 2}$

**91.** 
* **(a)** $f(x) = \frac{|x - 2|}{x - 2}$
* **(b)** $g(x) = \frac{x}{x^{2} - 4}$

**92.** 
$$F(x) = \begin{cases} x + 4 & \text{si } x < -4 \\ \sqrt{16 - x^{2}} & \text{si } -4 \le x \le 4 \\ 2 - x & \text{si } 4 < x \end{cases}$$

---

En los ejercicios 93 a 96, haga lo siguiente:
* **(a)** Verifique que se cumpla el teorema del valor intermedio para la función $f$, el intervalo cerrado $[a, b]$ y el valor dado de $k$;
* **(b)** Trace la gráfica de $f$ y la recta $y = k$ en la graficadora y estime, con cuatro cifras decimales, el número $c$ de $(a, b)$ tal que $f(c) = k$;
* **(c)** Confirme analíticamente la estimación del inciso (b);
* **(d)** Dibuje la gráfica de $f$ en el intervalo $[a, b]$ y muestre el punto $(c, k)$. *(Para apreciar la gráfica correspondiente, consulte la página 98 del libro).*

**93.** $f(x) = x^{2} - 4x + 1$; $[a, b] = [-10, 0]$; $k = 10$
**94.** $f(x) = x^{2} - 4x + 1$; $[a, b] = [0, 10]$; $k = 10$
**95.** $f(x) = x - \sqrt{16 - x^{2}}$; $[a, b] = [0, 4]$; $k = -2$
**96.** $f(x) = x - \sqrt{16 - x^{2}}$; $[a, b] = [-4, 0]$; $k = -2$

---

En los ejercicios 97 y 98, responda las preguntas a partir de la gráfica adjunta de la función $f$. *(Para consultar la figura de la gráfica original, remítase a la página 97 y 98 del libro).*

**97.** ¿Cuál es el valor de cada uno de los límites siguientes:
* **(a)** $\lim_{x \to -3^{-}} f(x)$
* **(b)** $\lim_{x \to -3^{+}} f(x)$
* **(c)** $\lim_{x \to 0} f(x)$
* **(d)** $\lim_{x \to 2^{-}} f(x)$
* **(e)** $\lim_{x \to 2^{+}} f(x)$
* **(f)** $\lim_{x \to 3^{-}} f(x)$
* **(g)** $\lim_{x \to 3^{+}} f(x)$
* **(h)** ¿En qué números es discontinua $f$?
* **(i)** ¿Cuáles de las discontinuidades del inciso (h) son esenciales?
* **(j)** ¿Cuáles de las discontinuidades del inciso (h) son removibles? ¿Cómo redefiniría la función para eliminar las discontinuidades?

**98.** ¿Cuál es el valor de cada uno de los límites siguientes:
* **(a)** $\lim_{x \to -2^{-}} f(x)$
* **(b)** $\lim_{x \to 2^{+}} f(x)$
* **(c)** $\lim_{x \to -1} f(x)$
* **(d)** $\lim_{x \to 0} f(x)$
* **(e)** $\lim_{x \to 1^{-}} f(x)$
* **(f)** $\lim_{x \to 1^{+}} f(x)$
* **(g)** $\lim_{x \to 2} f(x)$
* **(h)** ¿En qué números es discontinua $f$?
* **(i)** ¿Cuáles de las discontinuidades del inciso (h) son esenciales?
* **(j)** ¿Cuáles de las discontinuidades del inciso (h) son removibles? ¿Cómo redefiniría la función para eliminar las discontinuidades?

---

En los ejercicios 99 a 102, dibuje la gráfica de una función $f$ que satisfaga las condiciones dadas. *(Para apreciar la representación gráfica resultante, consulte la página 98 del libro).*

**99.** $-5, -3, -2, -1, 0,$ y $2$ son los únicos ceros de $f$; $\lim_{x \to -3} f(x) = 4$; $\lim_{x \to -1^{-}} f(x) = -\infty$; $\lim_{x \to -1^{+}} f(x) = 0$; $\lim_{x \to 0} f(x) = +\infty$; $f$ es continua en todos los números de los intervalos abiertos $(-\infty, -3)$, $(-3, -1)$, $(-1, 0)$, $(0, +\infty)$.

**100.** $f$ es continua en $(-\infty, -2)$, $[-2, 1)$, $[1, 3]$, y $(3, +\infty)$; $\lim_{x \to -4} f(x) = 0$; $\lim_{x \to -2^{-}} f(x) = 3$; $\lim_{x \to -2^{+}} f(x) = 0$; $\lim_{x \to 0} f(x) = -3$; $\lim_{x \to 1^{-}} f(x) = -\infty$; $\lim_{x \to 1^{+}} f(x) = 2$; $\lim_{x \to 3^{-}} f(x) = 4$; $\lim_{x \to 3^{+}} f(x) = -1$; $\lim_{x \to 5} f(x) = 0$.

**101.** El dominio de $f$ es $(-\infty, +\infty)$; $f(-4) = 2$; $-2, 0, 2, 4$ y $6$ son los únicos ceros de $f$; $\lim_{x \to -4} f(x) = 0$; $\lim_{x \to -2^{-}} f(x) = -\infty$; $\lim_{x \to -2^{+}} f(x) = +\infty$; $\lim_{x \to 0^{-}} f(x) = 0$; $\lim_{x \to 0^{+}} f(x) = -3$; $\lim_{x \to 4} f(x) = 5$; $f$ es continua en todos los números excepto $-4, -2, 0,$ y $4$.

**102.** $f$ es continua en $(-\infty, -4]$, $(-4, 4)$ y $[4, +\infty)$; $\lim_{x \to -6} f(x) = 0$; $\lim_{x \to -4^{-}} f(x) = 2$; $\lim_{x \to -4^{+}} f(x) = +\infty$; $\lim_{x \to -2} f(x) = 0$; $\lim_{x \to 0} f(x) = -3$; $\lim_{x \to 2} f(x) = 0$; $\lim_{x \to 4^{-}} f(x) = 1$; $\lim_{x \to 4^{+}} f(x) = -2$; $\lim_{x \to 5} f(x) = 0$.

---

## MODELOS MATEMÁTICOS Y APLICACIONES

En los ejercicios 103 a 106, obtenga un modelo matemático de la situación particular. Defina la variable independiente y los valores de función como números, e indique las unidades de medición. Asegúrese de completar el ejercicio escribiendo una conclusión.

**103.** Se construye una cacerola abierta cortando cuadrados del mismo tamaño en las esquinas de un trozo rectangular de lámina de $14$ por $18\text{ pulg}$ y doblando los lados hacia arriba.
* **(a)** Encuentre un modelo matemático que exprese el volumen de la cacerola como una función de la longitud del lado de los cuadrados que se cortarán.
* **(b)** ¿Cuál es el dominio de la función del inciso (a)?
* **(c)** Demuestre que la función es continua en su dominio.
* **(d)** En la graficadora, estime con aproximación de centésimos de pulgada la longitud del lado de los cuadrados que deben cortarse de modo que el volumen de la cacerola sea un máximo.

**104.** Una caja abierta tiene base cuadrada y un volumen de $4000\text{ pulg}^{3}$.
* **(a)** Encuentre un modelo matemático que exprese el área de la superficie total de la caja, como una función de la longitud del lado de la base cuadrada.
* **(b)** ¿Cuál es el dominio de la función del inciso (a)?
* **(c)** Demuestre que la función es continua en su dominio.
* **(d)** En la graficadora, determine, con aproximación de pulgadas, las dimensiones de la caja que pueda construirse con la mínima cantidad de material.

**105.** Se requiere que un anuncio, que contiene $50\text{ m}^{2}$ de material impreso, tenga márgenes de $4\text{ m}$ en las partes superior e inferior y $2\text{ m}$ en los otros dos lados. *(Para apreciar la ilustración del anuncio, consulte la página 98 del libro).*
* **(a)** Encuentre un modelo matemático que exprese el área total del anuncio como una función de la dimensión horizontal de la región cubierta por el material impreso.
* **(b)** ¿Cuál es el dominio de la función del inciso (a)?
* **(c)** Demuestre que la función es continua en su dominio.
* **(d)** En la graficadora, estime, con aproximación de metros, las dimensiones del anuncio más pequeño que cumpla con estas especificaciones.

**106.** Un estanque puede mantener a $10\,000$ peces. La tasa de crecimiento de la población de peces es conjuntamente proporcional al número de peces presentes y a la diferencia entre $10\,000$ y el número de peces presentes. La tasa de crecimiento es de $90$ peces semanales cuando se encuentran presentes $1000$ peces.
* **(a)** Encuentre un modelo matemático que exprese la tasa de crecimiento de la población, como una función de la cantidad de peces presentes.
* **(b)** ¿Cuál es el dominio de la función del inciso (a)?
* **(c)** Demuestre que la función es continua en su dominio.
* **(d)** En la graficadora, determine el tamaño de la población de peces, de modo que la tasa de crecimiento sea un máximo.

---

**107.** $U$ y $\text{sgn}$ son las funciones salto unitario y signo definidas previamente. Encuentre fórmulas para la función $F$ definida por:
$$F(x) = \text{sgn}(x) \cdot U(x+1)$$
y dibuje su gráfica *(consulte la página 99 del libro)*. ¿En qué números es $F$ discontinua y por qué?

---

En los ejercicios 108 y 109, utilice el teorema de estricción para calcular los límites.

**108.** 
$$\lim_{x \to 4} g(x) \quad \text{si } |g(x) + 5| \le 3(4 - x)^{2} \text{ para toda } x$$

**109.** 
$$\lim_{x \to 1} \left[(x - 1)^{2} \sin \frac{1}{\sqrt[3]{x - 1}}\right]$$

---

**110.** Dibuje la gráfica de $f$ si $f(x) = \lfloor 1 - x^{2} \rfloor$ y $-2 \le x \le 2$. *(Para apreciar la gráfica correspondiente, consulte la página 99 del libro).*
* **(a)** ¿Existe $\lim_{x \to 0} f(x)$?
* **(b)** ¿Es $f$ continua en $0$?

**111.** Dibuje la gráfica de $g$ si $g(x) = (x - 1)\lfloor x \rfloor$ y $0 \le x \le 2$. *(Para apreciar la gráfica correspondiente, consulte la página 99 del libro).*
* **(a)** ¿Existe $\lim_{x \to 1} g(x)$?
* **(b)** ¿Es $g$ continua en $1$?

---

**112.** 
* **(a)** Demuestre que si $f(x) = g(x)$ para todos los valores de $x$ excepto $a$, entonces $\lim_{x \to a} f(x) = \lim_{x \to a} g(x)$ si los límites existen.
* **(b)** Demuestre que si $f(x) = g(x)$ para todos los valores de $x$ excepto $a$, entonces si $\lim_{x \to a} g(x)$ no existe, $\lim_{x \to a} f(x)$ no existe. *(Sugerencia: muestre que la suposición de que $\lim_{x \to a} f(x)$ existe conduce a una contradicción).*

**113.** 
* **(a)** Demuestre que si $\lim_{h \to 0} f(x+h) = f(x)$, entonces $\lim_{h \to 0} f(x+h) = \lim_{h \to 0} f(x-h)$.
* **(b)** Demuestre que el inverso del teorema del inciso (a) es falso proporcionando un ejemplo de una función para la cual $\lim_{h \to 0} f(x+h) = \lim_{h \to 0} f(x-h)$, pero $\lim_{h \to 0} f(x+h) \neq f(x)$.

**114.** Si el dominio de $f$ es el conjunto de todos los números reales y $f$ es continua en $0$, demuestre que si:
$$f(a+b) = f(a) + f(b)$$
para todo $a$ y $b$, entonces $f$ es continua en todo número real.

**115.** Si el dominio de $f$ es el conjunto de todos los números reales y $f$ es continua en $0$, demuestre que si:
$$f(a+b) = f(a) \cdot f(b)$$
para todo $a$ y $b$, entonces $f$ es continua en todo número real.

**116.** Suponga que la función $f$ está definida en el intervalo abierto $(0, 1)$ y que:
$$f(x) = \frac{\sin \pi x}{x(x - 1)}$$
Defina $f$ en $0$ y $1$ de modo que $f$ sea continua en el intervalo cerrado $[0, 1]$.
