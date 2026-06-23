# Análisis de Cuellos de Botella en un Flujo CAD/CAM Dental

Este repositorio contiene el código fuente y la documentación del **Trabajo Práctico Integrador** de la materia **Modelos y Simulaciones (2026)**.

El proyecto implementa un modelo de **Simulación de Eventos Discretos (Discrete Event Simulation - DES)** utilizando **Python** y la biblioteca **SimPy** para analizar el flujo de trabajo de un laboratorio dental. El objetivo es identificar cuellos de botella y evaluar mejoras en las etapas de **preparación** (escaneo y diseño CAD) y **fabricación** (fresado CAM) de coronas de zirconia.

---

# Requisitos

Antes de ejecutar la simulación, asegurate de tener instalado:

* **Python 3.x**
* Las siguientes librerías:

  * `simpy`
  * `pandas`
  * `matplotlib`

---

# Instalación

## 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_REPOSITORIO>
```

## 2. Crear un entorno virtual (opcional, pero recomendado)

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Instalar las dependencias

```bash
pip install simpy pandas matplotlib
```

---

# Ejecución de la simulación

Para ejecutar el modelo base, corré el siguiente comando desde la carpeta del proyecto:

```bash
python TPI-modelos.py
```
