import os
import urllib
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings("ignore")

# 1. Cargar variables de entorno
load_dotenv()

# Configuración de Conexión
params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SBDBFPR15;"
    "DATABASE=BFPMARKETING;"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


def procesar_archivo_saldos(ruta_archivo):
    # VALIDACIÓN: Verificar si el archivo existe físicamente
    if not os.path.exists(ruta_archivo):
        print(f"ERROR: El archivo no existe en la ruta: {ruta_archivo}")
        return None

    try:
        df = pd.read_excel(ruta_archivo)
        ts_creacion = os.path.getctime(ruta_archivo)
        fecha_creacion = datetime.fromtimestamp(ts_creacion).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        df["status"] = 1
        df["file_name"] = os.path.basename(ruta_archivo)
        df["created_on"] = fecha_creacion
        df["updated_on"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return df
    except Exception as e:
        print(f"Error al procesar archivo: {e}")
        return None


def actualizar_tabla_saldos(df, periodo_objetivo):
    nombre_tabla = "pla_variacion_pasivos_details"
    try:
        with engine.begin() as connection:
            # A. Borrar periodo existente
            print(f"Borrando registros del periodo {periodo_objetivo}...")
            query_delete = text(
                f"DELETE FROM dbo.{nombre_tabla} WHERE periodo = :per"
            )
            connection.execute(query_delete, {"per": periodo_objetivo})

            # B. Subir nueva data
            print(
                f"Subiendo {len(df)} filas para el periodo {periodo_objetivo}..."
            )
            df.to_sql(
                name=nombre_tabla,
                con=connection,
                schema="dbo",
                if_exists="append",
                index=False,
                chunksize=1000,
            )
        print("¡ÉXITO! Transacción completada.")
    except Exception as e:
        print(f"Error en la base de datos: {e}")


# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    ahora = datetime.now()

    # Si es el primer día del mes, retrocedemos al mes anterior
    if ahora.day == 1:
        from datetime import timedelta

        fecha_periodo = ahora.replace(day=1) - timedelta(days=1)
    else:
        fecha_periodo = ahora

    # Generamos el periodo en formato YYYYMM
    periodo = fecha_periodo.strftime("%Y%m")

    # 2. Leer la ruta desde el archivo .env usando la nueva variable
    ruta_base = os.getenv("OUTPUT_DIR_CATEGORIAS")

    if not ruta_base:
        print(
            "ERROR: La variable OUTPUT_DIR_CATEGORIAS no está definida en el archivo .env"
        )
        exit(1)

    nombre_archivo = f"archivoSaldos_{periodo}.xlsx"
    url_completa = os.path.join(ruta_base, nombre_archivo)

    print(
        f"Iniciando proceso para el periodo: {periodo} (Fecha actual: {ahora.strftime('%Y-%m-%d')})"
    )

    # 3. Validar archivo y procesar
    df_resultado = procesar_archivo_saldos(url_completa)

    if df_resultado is not None:
        actualizar_tabla_saldos(df_resultado, periodo)