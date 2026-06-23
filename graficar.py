import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os 

# Obtiene la ruta absoluta de la carpeta donde se encuentra graficar.py
directorio_actual = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# 1. CARGA DE DATOS (Tus 4 escenarios)
# =========================================================
# 3. Une esa ruta raíz con 'resultados' y el nombre del archivo
archivos = {
    "Escenario Base\n(1 Esc, 1 Dis)": os.path.join(directorio_actual, "resultados", "base.csv"),
    "Alternativa A\n(1 Esc, 2 Dis)": os.path.join(directorio_actual, "resultados", "2 d 1 e.csv"),
    "Alternativa B\n(2 Esc, 1 Dis)": os.path.join(directorio_actual, "resultados", "1 d 2 e.csv"),
    "Alternativa C\n(2 Esc, 2 Dis)": os.path.join(directorio_actual, "resultados", "2 d 2 e.csv")
}

dataframes = {}
for nombre, ruta in archivos.items():
    try:
        dataframes[nombre] = pd.read_csv(ruta)
    except FileNotFoundError:
        print(f"No se encontró el archivo: {ruta}")

if len(dataframes) == 4:
    # =========================================================
    # PLOT 1: Evolución de los Cuellos de Botella (Tiempos de Espera)
    # =========================================================
    # Extraemos los promedios globales de espera para cada área
    esperas_escaneo = [df['Espera Media Escaneo (min)'].mean() for df in dataframes.values()]
    esperas_diseno = [df['Espera Media Diseño (min)'].mean() for df in dataframes.values()]
    esperas_fresado = [df['Espera Media Fresado (min)'].mean() for df in dataframes.values()]
    
    nombres_escenarios = list(dataframes.keys())
    x = np.arange(len(nombres_escenarios))
    width = 0.25

    plt.style.use('ggplot')
    fig1, ax1 = plt.subplots(figsize=(12, 6))

    # Barras agrupadas
    rects1 = ax1.bar(x - width, esperas_escaneo, width, label='Espera Escaneo', color='purple')
    rects2 = ax1.bar(x, esperas_diseno, width, label='Espera Diseño CAD', color='blue')
    rects3 = ax1.bar(x + width, esperas_fresado, width, label='Espera Fresado CAM', color='orange')

    ax1.set_ylabel('Tiempo Medio de Espera (minutos)', fontweight='bold')
    ax1.set_title('Desplazamiento del Cuello de Botella según Inversión en Recursos', fontweight='bold', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(nombres_escenarios, fontweight='bold')
    ax1.legend(loc='upper right')

    # Agregar los valores numéricos arriba de las barras
    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            height = rect.get_height()
            if height > 0.1: # Solo mostrar si es mayor a 0.1 para no amontonar
                ax1.annotate(f'{height:.1f}',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3 puntos de offset vertical
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

    fig1.tight_layout()
    plt.savefig('grafico_cuellos_botella.png', dpi=300)

    # =========================================================
    # PLOT 2: Boxplot de Estabilidad de Producción Mensual
    # =========================================================
    # Preparamos los datos para el boxplot (las 10 semillas de cada escenario)
    datos_produccion = [df['Trabajos Terminados'] for df in dataframes.values()]

    fig2, ax2 = plt.subplots(figsize=(10, 6))
    
    # Propiedades visuales del boxplot
    box = ax2.boxplot(datos_produccion, patch_artist=True, labels=nombres_escenarios,
                      medianprops=dict(color="black", linewidth=2))
    
    colores = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    for patch, color in zip(box['boxes'], colores):
        patch.set_facecolor(color)

    ax2.set_ylabel('Cantidad de Coronas Terminadas por Mes', fontweight='bold')
    ax2.set_title('Distribución de la Producción Mensual (Simulación Monte Carlo)', fontweight='bold', fontsize=14)
    ax2.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.25)

    fig2.tight_layout()
    plt.savefig('grafico_produccion_boxplot.png', dpi=300)

    plt.show()