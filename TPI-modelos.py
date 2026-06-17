import simpy
import random
import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# 1. PARÁMETROS DEL MODELO
# ==========================================
TIEMPO_SIMULACION = 480  # 8 horas
LLEGADA_PROMEDIO = 24    # 1 trabajo cada 24 mins

# ==========================================
# 2. PROCESO DE LA CORONA 
# ==========================================
def proceso_corona(env, id_corona, disenadores, fresadoras, registros):
    tiempo_llegada = env.now
    
    # 1. Creamos la "ficha" ni bien entra y la guardamos en la lista
    # Los tiempos que aún no sucedieron arrancan en None
    ficha_trabajo = {
        'Trabajo': id_corona,
        'Minuto_Llegada': tiempo_llegada,
        'Espera_CAD': None,
        'Tiempo_Neto_CAD': None,
        'Espera_CAM': None,
        'Tiempo_Neto_CAM': None,
        'Tiempo_Total': None
    }
    registros.append(ficha_trabajo) # Se agrega a la base de datos de inmediato
    
    # --- ETAPA 1: PREPARACIÓN ---
    with disenadores.request() as peticion_diseno:
        yield peticion_diseno 
        inicio_diseno = env.now
        
        # Actualizamos la ficha (como es un diccionario mutable, se actualiza en la lista)
        ficha_trabajo['Espera_CAD'] = inicio_diseno - tiempo_llegada
        
        tiempo_prep = random.uniform(15, 50)
        yield env.timeout(tiempo_prep)
        fin_diseno = env.now
        ficha_trabajo['Tiempo_Neto_CAD'] = fin_diseno - inicio_diseno

    # --- ETAPA 2: FRESADO ---
    with fresadoras.request() as peticion_fresado:
        yield peticion_fresado 
        inicio_fresado = env.now
        
        ficha_trabajo['Espera_CAM'] = inicio_fresado - fin_diseno
        
        if random.random() < 0.10: # Penalización por color
            yield env.timeout(5) 
            
        tiempo_tallado = random.uniform(8, 20)
        yield env.timeout(tiempo_tallado)
        fin_fresado = env.now
        
        ficha_trabajo['Tiempo_Neto_CAM'] = fin_fresado - inicio_fresado
        ficha_trabajo['Tiempo_Total'] = fin_fresado - tiempo_llegada

# ==========================================
# 3. GENERADOR DE LLEGADAS
# ==========================================
def generador_llegadas(env, disenadores, fresadoras, registros):
    contador = 1
    while True:
        env.process(proceso_corona(env, f'C-{contador:02d}', disenadores, fresadoras, registros))
        contador += 1
        yield env.timeout(random.expovariate(1.0 / LLEGADA_PROMEDIO))

# ==========================================
# 4. MONITOR DEL SISTEMA (Reemplaza el ploteo continuo de Modelica)
# ==========================================
def monitor_sistema(env, disenadores, fresadoras, historial_estado):
    """Saca una foto del sistema cada 1 minuto de reloj"""
    while True:
        historial_estado.append({
            'Minuto': env.now,
            'Cola_CAD': len(disenadores.queue),
            'Cola_CAM': len(fresadoras.queue),
            'Disenadores_Ocupados': disenadores.count,
            'Fresadoras_Ocupadas': fresadoras.count
        })
        yield env.timeout(1)

# ==========================================
# 5. MOTOR DE SIMULACIÓN Y VISUALIZACIÓN (CORREGIDO)
# ==========================================
def ejecutar_simulacion(cant_disenadores, cant_fresadoras, nombre_escenario):
    env = simpy.Environment()
    disenadores = simpy.Resource(env, capacity=cant_disenadores)
    fresadoras = simpy.Resource(env, capacity=cant_fresadoras)
    
    registros = []
    historial_estado = []

    env.process(generador_llegadas(env, disenadores, fresadoras, registros))
    env.process(monitor_sistema(env, disenadores, fresadoras, historial_estado))
    
    env.run(until=TIEMPO_SIMULACION)

    df_trabajos = pd.DataFrame(registros)
    df_estado = pd.DataFrame(historial_estado)

    # --- ANÁLISIS DE DATOS ---
    print(f"\n{'='*40}")
    print(f" RESULTADOS: {nombre_escenario.upper()}")
    print(f"{'='*40}")
    
    # Ahora len() sí nos da el total de llegadas reales
    trabajos_ingresados = len(df_trabajos)
    
    # Contamos como terminados solo los que tienen un valor en 'Tiempo_Total' (no son NaN)
    df_terminados = df_trabajos.dropna(subset=['Tiempo_Total'])
    trabajos_terminados = len(df_terminados)
    
    print(f"📦 Flujo de Trabajos:")
    print(f"  - Trabajos que ingresaron: {trabajos_ingresados}")
    print(f"  - Coronas terminadas: {trabajos_terminados}")
    print(f"  - Trabajos atascados al cierre: {trabajos_ingresados - trabajos_terminados}")
    
    print(f"\n⏱️  Tiempos de Espera (Cuellos de Botella):")
    # Usamos skipna=True para que Pandas ignore los trabajos que nunca llegaron a estas etapas
    print(f"  - Espera PROMEDIO para Diseño: {df_trabajos['Espera_CAD'].mean(skipna=True):.2f} min")
    print(f"  - Espera MÁXIMA para Diseño:   {df_trabajos['Espera_CAD'].max(skipna=True):.2f} min")
    print(f"  - Espera PROMEDIO para Máquina: {df_trabajos['Espera_CAM'].mean(skipna=True):.2f} min")
    print(f"  - Espera MÁXIMA para Máquina:   {df_trabajos['Espera_CAM'].max(skipna=True):.2f} min")
    
    print(f"\n⚙️  Métricas del Sistema:")
    print(f"  - Tiempo Total Promedio por Corona: {df_terminados['Tiempo_Total'].mean():.2f} min")
    
    uso_disenadores = (df_estado['Disenadores_Ocupados'].sum() / (TIEMPO_SIMULACION * cant_disenadores)) * 100
    uso_fresadoras = (df_estado['Fresadoras_Ocupadas'].sum() / (TIEMPO_SIMULACION * cant_fresadoras)) * 100
    print(f"  - Ocupación del área CAD: {uso_disenadores:.1f}%")
    print(f"  - Ocupación del área CAM: {uso_fresadoras:.1f}%")

    # --- GENERACIÓN DE GRÁFICOS ---
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    fig.canvas.manager.set_window_title(f'Simulación: {nombre_escenario}')

    ax1.plot(df_estado['Minuto'], df_estado['Cola_CAD'], label='Cola Diseño (Físico)', color='blue', linewidth=2)
    ax1.plot(df_estado['Minuto'], df_estado['Cola_CAM'], label='Cola Fresado (Digital)', color='orange', linewidth=2)
    ax1.set_title('Dinámica de las Colas de Espera a lo largo del día', fontweight='bold')
    ax1.set_xlabel('Minutos de la jornada laboral')
    ax1.set_ylabel('Cantidad de trabajos esperando')
    ax1.legend()
    ax1.grid(True)

    ax2.bar(df_terminados['Trabajo'], df_terminados['Tiempo_Total'], color='seagreen')
    ax2.set_title('Lead Time: Tiempo total de permanencia por trabajo (Solo completados)', fontweight='bold')
    ax2.set_xlabel('Identificador del Trabajo')
    ax2.set_ylabel('Minutos')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.show()

    return df_trabajos, df_estado

# --- EJECUTAR ---
if __name__ == '__main__':
    df_base, df_estado_base = ejecutar_simulacion(cant_disenadores=1, cant_fresadoras=2, nombre_escenario="Escenario Base")