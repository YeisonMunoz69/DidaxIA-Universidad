[Pagina 1 a 1345 del libro (Ãndice de contenido completo)]

# CONTENIDO

## PRÓLOGO (pág. XV)

---

## 1. Funciones, límites y continuidad (pág. 1)

* **1.1 Funciones y sus gráficas** (pág. 2)
  * *(Para apreciar la representación gráfica de las funciones y sus transformaciones, véase la pág. 2)*
* **1.2 Operaciones con funciones y tipos de funciones** (pág. 12)
  * Operaciones fundamentales:
    * Suma: $(f + g)(x) = f(x) + g(x)$
    * Resta: $(f - g)(x) = f(x) - g(x)$
    * Producto: $(f \cdot g)(x) = f(x) \cdot g(x)$
    * Cociente: $\left(\frac{f}{g}\right)(x) = \frac{f(x)}{g(x)}, \quad g(x) \neq 0$
    * Composición: $(f \circ g)(x) = f(g(x))$
  * *(Para analizar las gráficas de funciones polinomiales, racionales y algebraicas, véase la pág. 12)*
* **1.3 Funciones como modelos matemáticos** (pág. 20)
  * *(Para revisar la construcción de modelos gráficos a partir de problemas aplicados, véase la pág. 20)*
* **1.4 Introducción gráfica a los límites de funciones** (pág. 28)
  * *(Para apreciar la aproximación visual al comportamiento de una función cerca de un punto, véase la pág. 28)*
* **1.5 Definición de límite de una función y teoremas de límites** (pág. 38)
  * Definición formal $(\varepsilon-\delta)$:
    $$\lim_{x \to a} f(x) = L \iff \forall \varepsilon > 0, \, \exists \delta > 0 \text{ tal que } 0 < |x - a| < \delta \implies |f(x) - L| < \varepsilon$$
* **1.6 Límites laterales** (pág. 49)
  * Límite por la derecha: $\lim_{x \to a^+} f(x) = L_1$
  * Límite por la izquierda: $\lim_{x \to a^-} f(x) = L_2$
  * Criterio de existencia: $\lim_{x \to a} f(x) = L \iff \lim_{x \to a^+} f(x) = \lim_{x \to a^-} f(x) = L$
  * *(Para observar las gráficas de dislocación y saltos finitos, véase la pág. 49)*
* **1.7 Límites infinitos** (pág. 55)
  * Definicón: $\lim_{x \to a} f(x) = \pm\infty$
  * Asíntotas verticales: la recta $x = a$ es una asíntota vertical si $\lim_{x \to a^\pm} f(x) = \pm\infty$
  * *(Para apreciar las asíntotas verticales en la gráfica de la función, véase la pág. 55)*
* **1.8 Continuidad de una función en un número** (pág. 67)
  * $f$ es continua en $x = a$ si cumple:
    1. $f(a)$ existe.
    2. $\lim_{x \to a} f(x)$ existe.
    3. $\lim_{x \to a} f(x) = f(a)$
  * *(Para visualizar los tipos de discontinuidad removible y de salto en la gráfica, véase la pág. 67)*
* **1.9 Continuidad de una función compuesta y continuidad en un intervalo** (pág. 76)
  * Continuidad de la composición: Si $g$ es continua en $a$ y $f$ es continua en $g(a)$, entonces $(f \circ g)(x)$ es continua en $a$.
* **1.10 Continuidad de las funciones trigonométricas y teorema de estricción** (pág. 85)
  * Teorema de estricción (o del sándwich): Si $g(x) \le f(x) \le h(x)$ en un entorno de $a$ y $\lim_{x \to a} g(x) = \lim_{x \to a} h(x) = L$, entonces:
    $$\lim_{x \to a} f(x) = L$$
  * Límites trigonométricos fundamentales:
    $$\lim_{x \to 0} \frac{\sin x}{x} = 1, \quad \lim_{x \to 0} \frac{1 - \cos x}{x} = 0$$
* **Revisión del capítulo 1** (pág. 93)

---

## 2. Derivada y diferenciación (pág. 100)

* **2.1 Recta tangente y derivada** (pág. 101)
  * Pendiente de la recta tangente y definición de derivada:
    $$f'(x) = \lim_{\Delta x \to 0} \frac{f(x + \Delta x) - f(x)}{\Delta x} = \lim_{t \to x} \frac{f(t) - f(x)}{t - x}$$
  * *(Para interpretar geométrica y gráficamente la recta tangente y secante, véase la pág. 101)*
* **2.2 Diferenciabilidad y continuidad** (pág. 109)
  * Teorema: Si $f$ es diferenciable en $a$, entonces $f$ es continua en $a$.
  * *(Para analizar las gráficas con picos, cúspides o tangentes verticales donde no hay diferenciabilidad, véase la pág. 109)*
* **2.3 Derivada numérica** (pág. 118)
  * Aproximación por diferencias finitas centrales:
    $$f'(x) \approx \frac{f(x + h) - f(x - h)}{2h}$$
* **2.4 Teoremas sobre diferenciación de funciones algebraicas y derivadas de orden superior** (pág. 123)
  * Regla de la constante: $\frac{d}{dx}(c) = 0$
  * Regla de la potencia: $\frac{d}{dx}(x^n) = n x^{n-1}$
  * Regla de la suma/resta: $\frac{d}{dx}[f(x) \pm g(x)] = f'(x) \pm g'(x)$
  * Regla del producto: $\frac{d}{dx}[f(x) g(x)] = f'(x)g(x) + f(x)g'(x)$
  * Regla del cociente:
    $$\frac{d}{dx}\left[\frac{f(x)}{g(x)}\right] = \frac{f'(x)g(x) - f(x)g'(x)}{[g(x)]^2}$$
  * Derivadas de orden superior: $f''(x) = \frac{d^2 y}{dx^2}$, $f'''(x) = \frac{d^3 y}{dx^3}$, $\dots$, $f^{(n)}(x) = \frac{d^n y}{dx^n}$
* **2.5 Movimiento rectilíneo** (pág. 132)
  * Posición: $s(t)$
  * Velocidad instantánea: $v(t) = s'(t) = \frac{ds}{dt}$
  * Aceleración instantánea: $a(t) = v'(t) = s''(t) = \frac{d^2 s}{dt^2}$
  * Rapidez: $|v(t)|$
  * *(Para examinar las gráficas de posición, velocidad y aceleración en función del tiempo, véase la pág. 132)*
* **2.6 Derivada como tasa de variación** (pág. 145)
  * Tasa de variación promedio en $[x_1, x_2]$: $\frac{\Delta y}{\Delta x} = \frac{f(x_2) - f(x_1)}{x_2 - x_1}$
  * Tasa de variación instantánea: $\frac{dy}{dx} = \lim_{\Delta x \to 0} \frac{\Delta y}{\Delta x}$
* **2.7 Derivadas de las funciones trigonométricas** (pág. 152)
  * $\frac{d}{dx}(\sin x) = \cos x$
  * $\frac{d}{dx}(\cos x) = -\sin x$
  * $\frac{d}{dx}(\tan x) = \sec^2 x$
  * $\frac{d}{dx}(\cot x) = -\csc^2 x$
  * $\frac{d}{dx}(\sec x) = \sec x \tan x$
  * $\frac{d}{dx}(\csc x) = -\csc x \cot x$
* **2.8 Derivada de una función compuesta y regla de la cadena** (pág. 162)
  * Si $y = f(u)$ y $u = g(x)$:
    $$\frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx}$$
  * En notación de funciones: $(f \circ g)'(x) = f'(g(x)) \cdot g'(x)$
* **2.9 Derivada de la función potencia para exponentes racionales y diferenciación implícita** (pág. 172)
  * Para $r \in \mathbb{Q}$: $\frac{d}{dx}(x^r) = r x^{r-1}$
  * Diferenciación implícita para $F(x, y) = 0$: tomar $\frac{d}{dx}$ en ambos lados considerando $y = y(x)$.
* **2.10 Tasas de variación relacionadas** (pág. 182)
  * Relación de variables dinámicas $f(x, y, t) = 0$ y derivación con respecto al tiempo $t$.
  * *(Para apreciar la representación geométrica de problemas con tasas relacionadas, véase la pág. 182)*
* **Revisión del capítulo 2** (pág. 190)

---

## 3. Comportamiento de las funciones y de sus gráficas, valores extremos y aproximaciones (pág. 197)

* **3.1 Valores máximos y mínimos de funciones** (pág. 198)
  * Número crítico $c$: $f'(c) = 0$ o $f'(c)$ no existe.
  * Extremos absolutos y relativos en un dominio.
  * *(Para observar la ubicación gráfica de máximos y mínimos locales o absolutos, véase la pág. 198)*
* **3.2 Aplicaciones que involucran un extremo absoluto en un intervalo cerrado** (pág. 207)
  * Teorema del valor extremo: Si $f$ es continua en $[a, b]$, alcanza un máximo absoluto y un mínimo absoluto en $[a, b]$.
* **3.3 Teorema de Rolle y teorema del valor medio** (pág. 215)
  * **Teorema de Rolle:** Si $f$ es continua en $[a, b]$, diferenciable en $(a, b)$ y $f(a) = f(b)$, existe $c \in (a, b)$ tal que $f'(c) = 0$.
  * **Teorema del Valor Medio (TVM):** Si $f$ es continua en $[a, b]$ y diferenciable en $(a, b)$, existe $c \in (a, b)$ tal que:
    $$f'(c) = \frac{f(b) - f(a)}{b - a}$$
  * *(Para interpretar geométrica y gráficamente las tangentes paralelas a la secante, véase la pág. 215)*
* **3.4 Funciones crecientes y decrecientes, y criterio de la primera derivada** (pág. 223)
  * Si $f'(x) > 0 \implies f$ es creciente.
  * Si $f'(x) < 0 \implies f$ es decreciente.
  * Criterio de la 1.ª derivada para extremos relativos en un punto crítico $c$.
  * *(Para observar la relación gráfica entre la monotonicidad y el signo de la primera derivada, véase la pág. 223)*
* **3.5 Concavidad, puntos de inflexión y criterio de la segunda derivada** (pág. 231)
  * Concavidad hacia arriba: $f''(x) > 0$. Concavidad hacia abajo: $f''(x) < 0$.
  * Punto de inflexión: cambio de concavidad donde la función es continua.
  * Criterio de la 2.ª derivada:
    * $f'(c) = 0$ y $f''(c) < 0 \implies$ Máximo relativo en $c$.
    * $f'(c) = 0$ y $f''(c) > 0 \implies$ Mínimo relativo en $c$.
  * *(Para visualizar gráficamente la concavidad y los puntos de inflexión, véase la pág. 231)*
* **3.6 Trazo de las gráficas de funciones y de sus derivadas** (pág. 242)
  * *(Para comparar la gráfica de una función $f(x)$ con la de sus derivadas $f'(x)$ y $f''(x)$, véase la pág. 242)*
* **3.7 Límites al infinito** (pág. 249)
  * Definición: $\lim_{x \to \pm\infty} f(x) = L$
  * Asíntota horizontal: $y = L$.
  * *(Para apreciar el comportamiento asintótico horizontal en la gráfica, véase la pág. 249)*
* **3.8 Resumen para el trazo de las gráficas de funciones** (pág. 260)
  * Pasos guía: dominio, intersecciones, simetría, asíntotas, intervalos de incremento/decrecimiento, extremos relativos, concavidad, puntos de inflexión y bosquejo.
  * *(Para ver la guía gráfica completa del trazado de curvas, véase la pág. 260)*
* **3.9 Aplicaciones adicionales sobre extremos absolutos** (pág. 266)
  * Problemas de optimización en física, geometría y economía.
* **3.10 Aproximaciones mediante el método de Newton, de la recta tangente y de diferenciales** (pág. 275)
  * Aproximación lineal (recta tangente): $L(x) = f(a) + f'(a)(x - a)$
  * Diferenciales: $dy = f'(x) dx$
  * Método de Newton-Raphson:
    $$x_{n+1} = x_n - \frac{f(x_n)}{f'(x_n)}$$
  * *(Para estudiar la interpretación gráfica de la convergencia del método de Newton, véase la pág. 275)*
* **Revisión del capítulo 3** (pág. 287)

---

## 4. Integral definida e integración (pág. 296)

* **4.1 Antiderivación** (pág. 297)
  * Antiderivada o integral indefinida:
    $$\int f(x) \, dx = F(x) + C \quad \text{donde } F'(x) = f(x)$$
  * Formulario básico:
    $$\int x^n \, dx = \frac{x^{n+1}}{n+1} + C \quad (n \neq -1)$$
* **4.2 Algunas técnicas de antiderivación** (pág. 310)
  * Integración por cambio de variable (sustitución):
    $$\int f(g(x)) g'(x) \, dx = \int f(u) \, du \quad (u = g(x))$$
* **4.3 Ecuaciones diferenciales y movimiento rectilíneo** (pág. 319)
  * Ecuaciones diferenciales de primer orden separables: $\frac{dy}{dx} = f(x)g(y)$
  * Recuperación de $v(t)$ y $s(t)$ mediante integración de $a(t)$.
* **4.4 Área** (pág. 328)
  * Sumas de Riemann:
    $$\sum_{i=1}^n f(w_i) \Delta x_i$$
  * Aproximación del área mediante polígonos inscritos y circunscritos.
  * *(Para observar la representación gráfica de las sumas por la izquierda, derecha y punto medio, véase la pág. 328)*
* **4.5 Integral definida** (pág. 338)
  * Definición de la integral de Riemann:
    $$\int_a^b f(x) \, dx = \lim_{\|P\| \to 0} \sum_{i=1}^n f(w_i) \Delta x_i$$
* **4.6 Teorema del valor medio para integrales** (pág. 352)
  * Valor medio de $f$ en $[a, b]$:
    $$f(c) = \frac{1}{b - a} \int_a^b f(x) \, dx$$
  * *(Para apreciar la interpretación gráfica del rectángulo equivalente de igual área, véase la pág. 352)*
* **4.7 Teoremas fundamentales del Cálculo** (pág. 360)
  * **Primer Teorema Fundamental del Cálculo:**
    $$\frac{d}{dx} \left( \int_a^x f(t) \, dt \right) = f(x)$$
  * **Segundo Teorema Fundamental del Cálculo:**
    $$\int_a^b f(x) \, dx = F(b) - F(a) = \Big[ F(x) \Big]_a^b \quad \text{donde } F'(x) = f(x)$$
* **4.8 Área de una región plana** (pág. 372)
  * Área entre curvas $y = f(x)$ y $y = g(x)$ para $f(x) \ge g(x)$:
    $$A = \int_a^b [f(x) - g(x)] \, dx$$
  * *(Para apreciar las gráficas del área encerrada entre dos o más curvas, véase la pág. 372)*
* **4.9 Volúmenes de sólidos mediante los métodos de rebanado, de discos y de arandelas** (pág. 381)
  * Método de discos (rotación alrededor del eje $x$):
    $$V = \pi \int_a^b [f(x)]^2 \, dx$$
  * Método de arandelas:
    $$V = \pi \int_a^b \left( [f(x)]^2 - [g(x)]^2 \right) \, dx$$
  * *(Para visualizar el sólido de revolución generado y las rebanadas, véase la pág. 381)*
* **4.10 Volúmenes de sólidos mediante el método de capas cilíndricas** (pág. 391)
  * Rotación alrededor del eje $y$:
    $$V = 2\pi \int_a^b x f(x) \, dx$$
  * *(Para estudiar la estructura gráfica del elemento de volumen en capas cilíndricas, véase la pág. 391)*
* **Revisión del capítulo 4** (pág. 397)

---

## 5. Funciones logarítmicas, exponenciales, trigonométricas inversas e hiperbólicas (pág. 403)

* **5.1 Inversa de una función** (pág. 404)
  * Criterio de la recta horizontal (función inyectiva / uno a uno).
  * Propiedad: $f(f^{-1}(x)) = x$ y $f^{-1}(f(x)) = x$.
  * Derivada de la función inversa:
    $$(f^{-1})'(x) = \frac{1}{f'(f^{-1}(x))}$$
  * *(Para observar la simetría gráfica respecto a la recta $y = x$, véase la pág. 404)*
* **5.2 Función logarítmica natural** (pág. 418)
  * Definición:
    $$\ln x = \int_1^x \frac{1}{t} \, dt, \quad x > 0$$
  * Propiedades de los logaritmos:
    * $\ln(ab) = \ln a + \ln b$
    * $\ln\left(\frac{a}{b}\right) = \ln a - \ln b$
    * $\ln(a^r) = r \ln a$
  * Derivada: $\frac{d}{dx}(\ln x) = \frac{1}{x}$
  * *(Para mirar la gráfica de la función logaritmo natural y sus propiedades, véase la pág. 418)*
* **5.3 Diferenciación logarítmica e integrales que producen funciones logarítmicas naturales** (pág. 430)
  * Formulas de integración:
    $$\int \frac{1}{u} \, du = \ln |u| + C$$
    $$\int \tan u \, du = \ln |\sec u| + C, \quad \int \cot u \, du = \ln |\sin u| + C$$
* **5.4 Función exponencial natural** (pág. 437)
  * Definición: $y = e^x \iff x = \ln y$
  * Derivada e integral:
    $$\frac{d}{dx}(e^x) = e^x, \quad \int e^x \, dx = e^x + C$$
  * *(Para revisar la gráfica del crecimiento exponencial, véase la pág. 437)*
* **5.5 Otras funciones exponenciales y logarítmicas** (pág. 448)
  * Base $a > 0, a \neq 1$:
    * $a^x = e^{x \ln a}$
    * $\frac{d}{dx}(a^x) = a^x \ln a$
    * $\frac{d}{dx}(\log_a x) = \frac{1}{x \ln a}$
    * $\int a^x \, dx = \frac{a^x}{\ln a} + C$
* **5.6 Aplicaciones de la función exponencial natural** (pág. 456)
  * Crecimiento y decaimiento exponencial: $\frac{dy}{dt} = k y \implies y(t) = y_0 e^{kt}$
  * Ley de enfriamiento de Newton, interés compuesto continuo, etc.
* **5.7 Funciones trigonométricas inversas** (pág. 469)
  * Dominio y rango de $\arcsin x$, $\arccos x$, $\arctan x$, $\text{arcsec } x$.
  * Derivadas principales:
    $$\frac{d}{dx}(\arcsin x) = \frac{1}{\sqrt{1 - x^2}}$$
    $$\frac{d}{dx}(\arccos x) = -\frac{1}{\sqrt{1 - x^2}}$$
    $$\frac{d}{dx}(\arctan x) = \frac{1}{1 + x^2}$$
    $$\frac{d}{dx}(\text{arcsec } x) = \frac{1}{|x|\sqrt{x^2 - 1}}$$
  * *(Para contemplar las gráficas de las funciones trigonométricas inversas con sus dominios restringidos, véase la pág. 469)*
* **5.8 Integrales que producen funciones trigonométricas inversas** (pág. 485)
  * Integrales fundamentales:
    $$\int \frac{du}{\sqrt{a^2 - u^2}} = \arcsin\left(\frac{u}{a}\right) + C$$
    $$\int \frac{du}{a^2 + u^2} = \frac{1}{a} \arctan\left(\frac{u}{a}\right) + C$$
    $$\int \frac{du}{u\sqrt{u^2 - a^2}} = \frac{1}{a} \text{arcsec}\left(\frac{|u|}{a}\right) + C$$
* **5.9 Funciones hiperbólicas** (pág. 490)
  * Definiciones:
    $$\sinh x = \frac{e^x - e^{-x}}{2}, \quad \cosh x = \frac{e^x + e^{-x}}{2}$$
    $$\tanh x = \frac{\sinh x}{\cosh x} = \frac{e^x - e^{-x}}{e^x + e^{-x}}$$
  * Identidad fundamental: $\cosh^2 x - \sinh^2 x = 1$
  * Derivadas:
    $$\frac{d}{dx}(\sinh x) = \cosh x, \quad \frac{d}{dx}(\cosh x) = \sinh x, \quad \frac{d}{dx}(\tanh x) = \text{sech}^2 x$$
  * *(Para apreciar la forma gráfica de la catenaria $y = a \cosh(x/a)$ y de las demás curvas hiperbólicas, véase la pág. 490)*
* **Revisión del capítulo 5** (pág. 503)

---

## 6. Aplicaciones adicionales de la integral definida (pág. 508)

* **6.1 Longitud de arco de la gráfica de una función** (pág. 509)
  * Fórmula de la longitud de arco:
    $$L = \int_a^b \sqrt{1 + \left( \frac{dy}{dx} \right)^2} \, dx = \int_c^d \sqrt{1 + \left( \frac{dx}{dy} \right)^2} \, dy$$
  * *(Para estudiar la aproximación poligonal en la gráfica, véase la pág. 509)*
* **6.2 Centro de masa de una barra** (pág. 516)
  * Densidad lineal $\rho(x)$:
    $$\text{Masa } M = \int_a^b \rho(x) \, dx, \quad \text{Momento } M_0 = \int_a^b x \rho(x) \, dx, \quad \bar{x} = \frac{M_0}{M}$$
* **6.3 Centro de masa de una lámina y centroide de una región plana** (pág. 522)
  * Centroide $(\bar{x}, \bar{y})$ para la región delimitada por $f(x)$ y $g(x)$ con $f(x) \ge g(x)$:
    $$\bar{x} = \frac{1}{A} \int_a^b x [f(x) - g(x)] \, dx, \quad \bar{y} = \frac{1}{2A} \int_a^b \left( [f(x)]^2 - [g(x)]^2 \right) \, dx$$
  * *(Para ubicar la posición gráfica del centroide de una lámina plana, véase la pág. 522)*
* **6.4 Trabajo** (pág. 530)
  * Fuerza variable $F(x)$:
    $$W = \int_a^b F(x) \, dx$$
  * Ejemplos: Ley de Hooke para resortes ($F(x) = kx$), bombeo de líquidos en tanques.
* **6.5 Fuerza ejercida por la presión de un líquido** (pág. 536)
  * Presión $P = w h$ y fuerza hidrostática:
    $$F = \int_c^d w \cdot h(y) \cdot L(y) \, dy$$
  * *(Para ver la representación gráfica del perfil de una superficie sumergida, véase la pág. 536)*
* **Revisión del capítulo 6** (pág. 542)

---

## 7. Técnicas de integración, formas indeterminadas e integrales impropias (pág. 544)

* **7.1 Integración por partes** (pág. 545)
  * Fórmula de integración por partes:
    $$\int u \, dv = u v - \int v \, du$$
* **7.2 Integrales trigonométricas** (pág. 555)
  * Evaluaciones de $\int \sin^m x \cos^n x \, dx$, $\int \tan^m x \sec^n x \, dx$, utilizando identidades como $\sin^2 x + \cos^2 x = 1$, $\sin^2 x = \frac{1 - \cos(2x)}{2}$, $\cos^2 x = \frac{1 + \cos(2x)}{2}$.
* **7.3 Integración de funciones algebraicas mediante sustitución trigonométrica** (pág. 565)
  * Para $\sqrt{a^2 - x^2} \implies$ usar $x = a \sin \theta$
  * Para $\sqrt{a^2 + x^2} \implies$ usar $x = a \tan \theta$
  * Para $\sqrt{x^2 - a^2} \implies$ usar $x = a \sec \theta$
  * *(Para la interpretación geométrica de los triángulos de sustitución, véase la pág. 565)*
* **7.4 Integración de funciones racionales y crecimiento logístico** (pág. 572)
  * Descomposición en fracciones parciales de $\frac{P(x)}{Q(x)}$: factores lineales y cuadráticos.
  * Modelo de crecimiento logístico:
    $$\frac{dP}{dt} = k P \left(1 - \frac{P}{K}\right) \implies P(t) = \frac{K}{1 + A e^{-kt}}$$
  * *(Para apreciar la curva sigmoide logística en su gráfica, véase la pág. 572)*
* **7.5 Integración mediante otras técnicas de sustitución y tablas** (pág. 584)
  * Sustitución de Weierstrass para expresiones trigonométricas: $t = \tan\left(\frac{x}{2}\right)$.
* **7.6 Integración numérica** (pág. 591)
  * **Regla del trapecio:**
    $$T_n = \frac{\Delta x}{2} \left[ f(x_0) + 2 f(x_1) + 2 f(x_2) + \dots + 2 f(x_{n-1}) + f(x_n) \right]$$
  * **Regla de Simpson ($n$ par):**
    $$S_n = \frac{\Delta x}{3} \left[ f(x_0) + 4 f(x_1) + 2 f(x_2) + 4 f(x_3) + \dots + 4 f(x_{n-1}) + f(x_n) \right]$$
  * *(Para ver la aproximación gráfica por trapecios y parábolas, véase la pág. 591)*
* **7.7 Forma indeterminada $0/0$ y teorema del valor medio de Cauchy** (pág. 604)
  * **Regla de L'Hôpital:** Si $\lim_{x \to a} \frac{f(x)}{g(x)}$ produce $\frac{0}{0}$ o $\frac{\pm\infty}{\pm\infty}$, entonces:
    $$\lim_{x \to a} \frac{f(x)}{g(x)} = \lim_{x \to a} \frac{f'(x)}{g'(x)}$$
  * Teorema del Valor Medio de Cauchy: $\frac{f'(c)}{g'(c)} = \frac{f(b) - f(a)}{g(b) - g(a)}$
* **7.8 Otras formas indeterminadas** (pág. 612)
  * Transformación de formas $0 \cdot \infty$, $\infty - \infty$, $0^0$, $1^\infty$, $\infty^0$ a la forma $\frac{0}{0}$ o $\frac{\infty}{\infty}$ mediante el uso de logaritmos o arreglos algebraicos.
* **7.9 Integrales impropias con límites de integración infinitos** (pág. 618)
  * Definicón:
    $$\int_a^{\infty} f(x) \, dx = \lim_{t \to \infty} \int_a^t f(x) \, dx$$
  * Criterios de convergencia y divergencia.
  * *(Para examinar el área no acotada en la gráfica de una integral impropia, véase la pág. 618)*
* **7.10 Otras integrales impropias** (pág. 627)
  * Integrandos con discontinuidades infinitas en el intervalo de integración.
* **Revisión del capítulo 7** (pág. 632)

---

## 8. Aproximaciones polinomiales, sucesiones y series infinitas (pág. 638)

* **8.1 Aproximaciones polinomiales mediante la fórmula de Taylor** (pág. 639)
  * Polinomio de Taylor de grado $n$ centrado en $a$:
    $$P_n(x) = \sum_{k=0}^n \frac{f^{(k)}(a)}{k!} (x - a)^k = f(a) + f'(a)(x-a) + \frac{f''(a)}{2!}(x-a)^2 + \dots + \frac{f^{(n)}(a)}{n!}(x-a)^n$$
  * Residuo de Lagrange: $R_n(x) = \frac{f^{(n+1)}(c)}{(n+1)!} (x - a)^{n+1}$
  * *(Para apreciar la aproximación gráfica progresiva de los polinomios de Taylor a la función, véase la pág. 639)*
* **8.2 Sucesiones** (pág. 647)
  * Convergencia de sucesiones: $\lim_{n \to \infty} a_n = L$
* **8.3 Series infinitas de términos constantes** (pág. 659)
  * Sumas parciales: $S_N = \sum_{n=1}^N a_n$
  * Serie geométrica:
    $$\sum_{n=0}^{\infty} a r^n = \frac{a}{1 - r} \quad \text{si } |r| < 1$$
  * Prueba de divergencia del término $n$-ésimo: Si $\lim_{n \to \infty} a_n \neq 0 \implies \sum a_n$ diverge.
* **8.4 Series infinitas de términos positivos** (pág. 671)
  * Prueba de la integral: $\sum a_n$ y $\int_1^{\infty} f(x)dx$ tienen el mismo comportamiento.
  * $p$-series:
    $$\sum_{n=1}^{\infty} \frac{1}{n^p} \quad \text{converge si } p > 1, \text{ diverge si } p \le 1$$
  * Pruebas de comparación directa y comparación en el límite.
* **8.5 Series infinitas de términos positivos y negativos** (pág. 684)
  * Series alternadas: $\sum (-1)^{n+1} a_n$ (Criterio de Leibniz).
  * Convergencia absoluta vs. convergencia condicional.
* **8.6 Resumen de criterios sobre la convergencia y divergencia de series infinitas** (pág. 695)
  * Criterios de la Razón (D'Alembert) y de la Raíz (Cauchy):
    $$L = \lim_{n \to \infty} \left| \frac{a_{n+1}}{a_n} \right| \quad \text{o} \quad L = \lim_{n \to \infty} \sqrt[n]{|a_n|}$$
    * $L < 1 \implies$ Converge absolutamente.
    * $L > 1 \implies$ Diverge.
    * $L = 1 \implies$ Criterio no concluyente.
* **8.7 Series de potencias** (pág. 698)
  * Forma general: $\sum_{n=0}^{\infty} c_n (x - a)^n$
  * Radio de convergencia $R$ e intervalo de convergencia.
* **8.8 Diferenciación e integración de series de potencias** (pág. 707)
  * Derivación término a término: $\frac{d}{dx}\left( \sum c_n (x-a)^n \right) = \sum n c_n (x-a)^{n-1}$
  * Integración término a término: $\int \left( \sum c_n (x-a)^n \right) dx = C + \sum \frac{c_n}{n+1} (x-a)^{n+1}$
* **8.9 Series de Taylor** (pág. 718)
  * Serie de Taylor en $a$:
    $$f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!} (x - a)^n$$
  * Series de Maclaurin notables ($a=0$):
    $$e^x = \sum_{n=0}^{\infty} \frac{x^n}{n!}, \quad \sin x = \sum_{n=0}^{\infty} \frac{(-1)^n x^{2n+1}}{(2n+1)!}, \quad \cos x = \sum_{n=0}^{\infty} \frac{(-1)^n x^{2n}}{(2n)!}$$
* **8.10 Series de potencias para logaritmos naturales y serie binomial** (pág. 727)
  * Serie binomial para $(1 + x)^k$:
    $$(1 + x)^k = \sum_{n=0}^{\infty} \binom{k}{n} x^n = 1 + kx + \frac{k(k-1)}{2!} x^2 + \dots$$
* **Revisión del capítulo 8** (pág. 735)

---

## 9. Ecuaciones paramétricas, curvas planas y gráficas polares (pág. 739)

* **9.1 Ecuaciones paramétricas y curvas planas** (pág. 740)
  * Definición: $x = f(t), y = g(t)$ para $t \in I$.
  * Derivadas:
    $$\frac{dy}{dx} = \frac{g'(t)}{f'(t)}, \quad \frac{d^2y}{dx^2} = \frac{\frac{d}{dt}\left(\frac{dy}{dx}\right)}{\frac{dx}{dt}}$$
  * *(Para apreciar la trayectoria y orientación de la curva paramétrica, véase la pág. 740)*
* **9.2 Longitud de arco de una curva plana** (pág. 747)
  * Longitud en forma paramétrica:
    $$L = \int_{t_1}^{t_2} \sqrt{\left(\frac{dx}{dt}\right)^2 + \left(\frac{dy}{dt}\right)^2} \, dt$$
* **9.3 Coordenadas polares y gráficas polares** (pág. 752)
  * Relación con coordenadas cartesianas:
    $$x = r \cos \theta, \quad y = r \sin \theta, \quad r^2 = x^2 + y^2, \quad \tan \theta = \frac{y}{x}$$
  * *(Para examinar las gráficas polares como cardioides, rosas, caracoles y lemniscatas, véase la pág. 752)*
* **9.4 Longitud de arco y área de una región para gráficas polares** (pág. 765)
  * Área de una región polar:
    $$A = \frac{1}{2} \int_{\alpha}^{\beta} r^2 \, d\theta$$
  * Longitud de arco polar:
    $$L = \int_{\alpha}^{\beta} \sqrt{r^2 + \left( \frac{dr}{d\theta} \right)^2} \, d\theta$$
  * *(Para visualizar el área barrida por los rayos polares en la gráfica, véase la pág. 765)*
* **9.5 Tratamiento unificado de las secciones cónicas y ecuaciones polares de las cónicas** (pág. 774)
  * Ecuación polar unificada: $r = \frac{e d}{1 \pm e \cos \theta}$ o $r = \frac{e d}{1 \pm e \sin \theta}$
    * Excentricidad $e < 1$: Elipse.
    * Excentricidad $e = 1$: Parábola.
    * Excentricidad $e > 1$: Hipérbola.
  * *(Para observar las posiciones de los focos y directrices en las gráficas polares, véase la pág. 774)*
* **Revisión del capítulo 9** (pág. 782)

---

## 10. Vectores, rectas, planos y superficies en el espacio (pág. 786)

* **10.1 Vectores en el plano** (pág. 787)
  * Componentes: $\mathbf{v} = \langle v_1, v_2 \rangle = v_1 \mathbf{i} + v_2 \mathbf{j}$
  * Magnitud: $\|\mathbf{v}\| = \sqrt{v_1^2 + v_2^2}$
  * Vector unitario: $\mathbf{u} = \frac{\mathbf{v}}{\|\mathbf{v}\|}$
  * *(Para apreciar la representación geométrica de los vectores y la regla del paralelogramo, véase la pág. 787)*
* **10.2 Vectores en el espacio tridimensional** (pág. 799)
  * Componentes: $\mathbf{v} = \langle v_1, v_2, v_3 \rangle = v_1 \mathbf{i} + v_2 \mathbf{j} + v_3 \mathbf{k}$
  * Distancia entre dos puntos: $d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2 + (z_2 - z_1)^2}$
  * *(Para visualizar ejes tridimensionales y vectores en $\mathbb{R}^3$, véase la pág. 799)*
* **10.3 Producto punto** (pág. 811)
  * Definición: $\mathbf{u} \cdot \mathbf{v} = u_1 v_1 + u_2 v_2 + u_3 v_3 = \|\mathbf{u}\| \|\mathbf{v}\| \cos \theta$
  * Criterio de ortogonalidad: $\mathbf{u} \cdot \mathbf{v} = 0 \iff \mathbf{u} \perp \mathbf{v}$
  * Proyección vectorial: $\text{proj}_{\mathbf{v}} \mathbf{u} = \left( \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{v}\|^2} \right) \mathbf{v}$
* **10.4 Planos y rectas en $\mathbb{R}^3$** (pág. 822)
  * Recta que pasa por $P_0(x_0, y_0, z_0)$ con dirección $\mathbf{v} = \langle a, b, c \rangle$:
    $$\mathbf{r}(t) = \mathbf{r}_0 + t \mathbf{v} \implies x = x_0 + at, \, y = y_0 + bt, \, z = z_0 + ct$$
  * Plano que pasa por $P_0$ con vector normal $\mathbf{n} = \langle a, b, c \rangle$:
    $$a(x - x_0) + b(y - y_0) + c(z - z_0) = 0$$
  * *(Para estudiar la posición de rectas y planos en el espacio tridimensional, véase la pág. 822)*
* **10.5 Producto cruz** (pág. 833)
  * Definición determinante:
    $$\mathbf{u} \times \mathbf{v} = \begin{vmatrix} \mathbf{i} & \mathbf{j} & \mathbf{k} \\ u_1 & u_2 & u_3 \\ v_1 & v_2 & v_3 \end{vmatrix}$$
  * Magnitud: $\|\mathbf{u} \times \mathbf{v}\| = \|\mathbf{u}\| \|\mathbf{v}\| \sin \theta$ (Área del paralelogramo).
* **10.6 Superficies** (pág. 846)
  * Cuádricas principales: elipsoides, paraboloides, hiperboloides, conos, cilindros.
  * *(Para apreciar la representación gráfica tridimensional de las superficies cuádricas, véase la pág. 846)*
* **Revisión del capítulo 10** (pág. 860)

---

## 11. Funciones vectoriales (pág. 864)

* **11.1 Funciones vectoriales y curvas en $\mathbb{R}^3$** (pág. 865)
  * Definición: $\mathbf{r}(t) = f(t)\mathbf{i} + g(t)\mathbf{j} + h(t)\mathbf{k}$
  * *(Para examinar las trayectorias de curvas en el espacio, véase la pág. 865)*
* **11.2 Cálculo de las funciones vectoriales** (pág. 872)
  * Derivada de $\mathbf{r}(t)$:
    $$\mathbf{r}'(t) = \lim_{\Delta t \to 0} \frac{\mathbf{r}(t + \Delta t) - \mathbf{r}(t)}{\Delta t} = \langle f'(t), g'(t), h'(t) \rangle$$
  * Integral: $\int \mathbf{r}(t) \, dt = \left\langle \int f(t)dt, \int g(t)dt, \int h(t)dt \right\rangle$
* **11.3 Vectores tangente unitario y normal unitario, y longitud de arco como parámetro** (pág. 882)
  * Vector tangente unitario: $\mathbf{T}(t) = \frac{\mathbf{r}'(t)}{\|\mathbf{r}'(t)\|}$
  * Vector normal unitario: $\mathbf{N}(t) = \frac{\mathbf{T}'(t)}{\|\mathbf{T}'(t)\|}$
  * Parámetro de longitud de arco $s(t) = \int_{t_0}^t \|\mathbf{r}'(u)\| \, du$
* **11.4 Curvatura** (pág. 888)
  * Curvatura $\kappa$:
    $$\kappa = \left\| \frac{d\mathbf{T}}{ds} \right\| = \frac{\|\mathbf{T}'(t)\|}{\|\mathbf{r}'(t)\|} = \frac{\|\mathbf{r}'(t) \times \mathbf{r}''(t)\|}{\|\mathbf{r}'(t)\|^3}$$
  * Radio de curvatura: $\rho = \frac{1}{\kappa}$
  * *(Para observar la representación gráfica del círculo osculador y la curvatura, véase la pág. 888)*
* **11.5 Movimiento curvilíneo** (pág. 897)
  * Velocidad: $\mathbf{v}(t) = \mathbf{r}'(t)$
  * Aceleración: $\mathbf{a}(t) = \mathbf{r}''(t) = a_T \mathbf{T} + a_N \mathbf{N}$
    * Componente tangencial: $a_T = \frac{d v}{dt} = \frac{\mathbf{r}'(t) \cdot \mathbf{r}''(t)}{\|\mathbf{r}'(t)\|}$
    * Componente normal: $a_N = \kappa v^2 = \frac{\|\mathbf{r}'(t) \times \mathbf{r}''(t)\|}{\|\mathbf{r}'(t)\|}$
* **Revisión del capítulo 11** (pág. 909)

---

## 12. Cálculo diferencial de funciones de más de una variable (pág. 913)

* **12.1 Funciones de más de una variable** (pág. 914)
  * $z = f(x, y)$, curvas y superficies de nivel $f(x, y) = c$.
  * *(Para apreciar las superficies de nivel y los mapas de contorno gráficos, véase la pág. 914)*
* **12.2 Límites y continuidad de funciones de más de una variable** (pág. 926)
  * $\lim_{(x,y) \to (x_0, y_0)} f(x, y) = L$
  * Análisis de trayectoria para demostrar la no existencia de límites.
* **12.3 Derivadas parciales** (pág. 942)
  * Derivadas parciales de primer orden:
    $$\frac{\partial f}{\partial x} = \lim_{\Delta x \to 0} \frac{f(x + \Delta x, y) - f(x, y)}{\Delta x}$$
    $$\frac{\partial f}{\partial y} = \lim_{\Delta y \to 0} \frac{f(x, y + \Delta y) - f(x, y)}{\Delta y}$$
  * Teorema de Clairaut (igualdad de derivadas mixtas): $f_{xy} = f_{yx}$ si son continuas.
* **12.4 Diferenciabilidad y diferencial total** (pág. 955)
  * Diferencial total $dz$:
    $$dz = \frac{\partial f}{\partial x} dx + \frac{\partial f}{\partial y} dy$$
* **12.5 Regla de la cadena para funciones de más de una variable** (pág. 965)
  * Si $z = f(x, y)$ con $x = x(t), y = y(t)$:
    $$\frac{dz}{dt} = \frac{\partial z}{\partial x} \frac{dx}{dt} + \frac{\partial z}{\partial y} \frac{dy}{dt}$$
* **12.6 Derivadas direccionales y gradientes** (pág. 975)
  * Vector gradiente: $\nabla f(x, y) = \left\langle \frac{\partial f}{\partial x}, \frac{\partial f}{\partial y} \right\rangle$
  * Derivada direccional en la dirección del unitario $\mathbf{u} = \langle a, b \rangle$:
    $$D_{\mathbf{u}} f(x, y) = \nabla f(x, y) \cdot \mathbf{u}$$
  * Dirección de máximo crecimiento: $\nabla f(x, y)$, con magnitud $\|\nabla f(x, y)\|$.
  * *(Para interpretar la relación gráfica del gradiente con las curvas de nivel, véase la pág. 975)*
* **12.7 Planos tangentes y rectas normales a superficies** (pág. 985)
  * Para la superficie $F(x, y, z) = 0$, el plano tangente en $P_0(x_0, y_0, z_0)$ es:
    $$F_x(P_0)(x - x_0) + F_y(P_0)(y - y_0) + F_z(P_0)(z - z_0) = 0$$
  * *(Para visualizar el plano tangente y la normal a la superficie en el espacio, véase la pág. 985)*
* **12.8 Extremos de funciones de dos variables** (pág. 990)
  * Puntos críticos: $\nabla f(x_0, y_0) = \mathbf{0}$ o indefinido.
  * Criterio de la segunda derivada (Hessiano): $D = f_{xx} f_{yy} - (f_{xy})^2$
    * $D > 0$ y $f_{xx} > 0 \implies$ Mínimo relativo.
    * $D > 0$ y $f_{xx} < 0 \implies$ Máximo relativo.
    * $D < 0 \implies$ Punto de silla.
    * $D = 0 \implies$ Criterio no concluyente.
  * *(Para examinar los puntos de silla y máximos/mínimos en gráficos tridimensionales, véase la pág. 990)*
* **12.9 Multiplicadores de Lagrange** (pág. 1004)
  * Optimización con restricción $g(x, y) = k$:
    $$\nabla f(x, y) = \lambda \nabla g(x, y), \quad g(x, y) = k$$
* **Revisión del capítulo 12** (pág. 1014)

---

## 13. Integración múltiple (pág. 1021)

* **13.1 Coordenadas cilíndricas y esféricas** (pág. 1022)
  * Cilíndricas: $(r, \theta, z)$ con $x = r \cos \theta, y = r \sin \theta, z = z$
  * Esféricas: $(\rho, \theta, \phi)$ con $x = \rho \sin \phi \cos \theta, y = \rho \sin \phi \sin \theta, z = \rho \cos \phi$
  * *(Para visualizar la geometría espacial de los sistemas de coordenadas cilíndricas y esféricas, véase la pág. 1022)*
* **13.2 Integrales dobles** (pág. 1028)
  * Definición y Teorema de Fubini para integrales reiteradas:
    $$\iint_R f(x, y) \, dA = \int_a^b \int_{g_1(x)}^{g_2(x)} f(x, y) \, dy \, dx$$
* **13.3 Aplicaciones de las integrales dobles** (pág. 1041)
  * Área de una región plana $R$: $A = \iint_R dA$
  * Masa de una lámina con densidad $\rho(x, y)$: $M = \iint_R \rho(x, y) \, dA$
  * Centro de masa $(\bar{x}, \bar{y})$:
    $$\bar{x} = \frac{1}{M} \iint_R x \rho(x, y) \, dA, \quad \bar{y} = \frac{1}{M} \iint_R y \rho(x, y) \, dA$$
  * Momentos de inercia $I_x, I_y, I_0$.
* **13.4 Integrales dobles en coordenadas polares** (pág. 1052)
  * Cambio de variables con Jacobiano $r$:
    $$\iint_R f(x, y) \, dA = \int_{\alpha}^{\beta} \int_{r_1(\theta)}^{r_2(\theta)} f(r \cos \theta, r \sin \theta) \, r \, dr \, d\theta$$
  * *(Para apreciar las regiones del plano descritas en coordenadas polares, véase la pág. 1052)*
* **13.5 Integrales triples** (pág. 1061)
  * Integrales reiteradas tridimensionales sobre sólidos $E$:
    $$V = \iiint_E dV = \int_a^b \int_{g_1(x)}^{g_2(x)} \int_{h_1(x, y)}^{h_2(x, y)} f(x, y, z) \, dz \, dy \, dx$$
* **13.6 Integrales triples en coordenadas cilíndricas y esféricas** (pág. 1067)
  * Cilíndricas: $dV = r \, dz \, dr \, d\theta$
  * Esféricas: $dV = \rho^2 \sin \phi \, d\rho \, d\phi \, d\theta$
  * *(Para observar la subdivisión geométrica del elemento de volumen tridimensional, véase la pág. 1067)*
* **Revisión del capítulo 13** (pág. 1074)

---

## 14. Introducción al Cálculo de campos vectoriales (pág. 1077)

* **14.1 Campos vectoriales** (pág. 1078)
  * Campos en $\mathbb{R}^2$ y $\mathbb{R}^3$: $\mathbf{F}(x, y, z) = P \mathbf{i} + Q \mathbf{j} + R \mathbf{k}$
  * Divergencia: $\text{div } \mathbf{F} = \nabla \cdot \mathbf{F} = \frac{\partial P}{\partial x} + \frac{\partial Q}{\partial y} + \frac{\partial R}{\partial z}$
  * Rotacional: $\text{rot } \mathbf{F} = \nabla \times \mathbf{F}$
  * *(Para examinar las representaciones gráficas de campos vectoriales de velocidades o fuerzas, véase la pág. 1078)*
* **14.2 Integrales de línea** (pág. 1089)
  * Integral sobre la curva $C$:
    $$\int_C f(x, y) \, ds = \int_a^b f(r(t)) \|\mathbf{r}'(t)\| \, dt$$
  * Trabajo realizado por un campo de fuerzas $\mathbf{F}$:
    $$W = \int_C \mathbf{F} \cdot d\mathbf{r} = \int_C P \, dx + Q \, dy + R \, dz$$
* **14.3 Integrales de línea independientes de la trayectoria** (pág. 1098)
  * Campos conservativos $\mathbf{F} = \nabla f$ (donde $f$ es una función potencial).
  * Teorema fundamental para integrales de línea:
    $$\int_C \nabla f \cdot d\mathbf{r} = f(\mathbf{r}(b)) - f(\mathbf{r}(a))$$
* **14.4 Teorema de Green** (pág. 1108)
  * Para una curva simple, cerrada y orientada positivamente $C$ que encierra la región $D$:
    $$\oint_C P \, dx + Q \, dy = \iint_D \left( \frac{\partial Q}{\partial x} - \frac{\partial P}{\partial y} \right) dA$$
  * *(Para apreciar la orientación y frontera de la región $D$ en el plano, véase la pág. 1108)*
* **14.5 Integrales de superficie** (pág. 1121)
  * Superficie orientada $S$:
    $$\iint_S f(x, y, z) \, dS = \iint_D f(x, y, g(x, y)) \sqrt{1 + \left(\frac{\partial g}{\partial x}\right)^2 + \left(\frac{\partial g}{\partial y}\right)^2} \, dA$$
  * Flujo de un campo vectorial $\mathbf{F}$ a través de $S$: $\iint_S \mathbf{F} \cdot \mathbf{n} \, dS$
* **14.6 Teorema de la divergencia de Gauss y teorema de Stokes** (pág. 1128)
  * **Teorema de la Divergencia (Gauss):**
    $$\iint_{S} \mathbf{F} \cdot \mathbf{n} \, dS = \iiint_E (\nabla \cdot \mathbf{F}) \, dV$$
  * **Teorema de Stokes:**
    $$\oint_{C} \mathbf{F} \cdot d\mathbf{r} = \iint_S (\nabla \times \mathbf{F}) \cdot \mathbf{n} \, dS$$
  * *(Para estudiar gráficamente la relación entre el borde $C$ y la superficie orientada $S$, véase la pág. 1128)*
* **Revisión del capítulo 14** (pág. 1135)

---

## Apéndice: Temas de matemáticas previas al Cálculo (pág. 1138)

* **A.1 Números reales y desigualdades** (pág. 1139)
* **A.2 Coordenadas y gráficas de ecuaciones** (pág. 1150)
* **A.3 Rectas** (pág. 1158)
* **A.4 Parábolas** (pág. 1168)
* **A.5 Circunferencias** (pág. 1173)
* **A.6 Traslación de ejes** (pág. 1178)
* **A.7 Elipses** (pág. 1183)
* **A.8 Hipérbolas** (pág. 1192)
* **A.9 Funciones trigonométricas** (pág. 1201)
* **A.10 Ecuación general de segundo grado en dos variables y rotación de ejes** (pág. 1209)
* **A.11 Fracciones parciales** (pág. 1216)

---

## Secciones suplementarias (pág. 1223)

* **Suplemento 1.5** (pág. 1224)
* **Suplemento 1.7** (pág. 1231)
* **Suplemento 1.10** (pág. 1232)
* **Suplemento 2.8** (pág. 1233)
* **Suplemento 4.5** (pág. 1235)
* **Suplemento 5.1** (pág. 1237)
* **Suplemento 8.2** (pág. 1241)
* **Suplemento 8.5** (pág. 1242)
* **Suplemento 8.8** (pág. 1243)
* **Suplemento 12.3** (pág. 1247)
* **Suplemento 12.4** (pág. 1249)
* **Suplemento 12.8** (pág. 1250)

---

## Tablas y formularios (pág. 1253)

* **Tabla de derivadas** (pág. 1253)
* **Tabla de integrales** (pág. 1253)
* **Fórmulas de álgebra** (pág. 1259)
* **Fórmulas de geometría** (pág. 1260)
* **Fórmulas de trigonometría** (pág. 1261)
* **Fórmulas de trigonometría hiperbólica** (pág. 1263)
* **Fórmulas de geometría analítica** (pág. 1264)
* **Alfabeto griego** (pág. 1274)

---

## Respuestas de los ejercicios impares (pág. 1275)

## Índice (pág. 1345)
