import pyodbc
import warnings
warnings.filterwarnings('ignore')


def guardar_log_sql(cursor, proceso, estado, mensaje):
    """Función auxiliar para registrar el estado en la tabla de logs."""
    try:
        query = """
            INSERT INTO [dbo].[LOG_EJECUCION_SCRIPTS] (nombre_script, proceso, estado, mensaje)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(query, ("procedure_ricardo.py", proceso, estado, mensaje))
        cursor.commit()
    except Exception as e:
        print(f"Error al guardar log en DB: {e}")

def ejecutar_procedimientos():
    """Función principal para conectar a SQL Server y ejecutar SPs."""
    
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=SBDBFPR15;"
        "DATABASE=BFPMARKETING;"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    conn = None
    try:
        print("Conectando al servidor SBDBFPR15...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Ejecutar el primer SP
        print("Ejecutando: CRM_CNA_API_01...")
        cursor.execute("EXEC [dbo].[CRM_CNA_API_01]")
        
        # Ejecutar el segundo SP
        print("Ejecutando: CRM_LEVANTAMIENTO_GARANTIA_API_02...")
        cursor.execute("EXEC [dbo].[CRM_LEVANTAMIENTO_GARANTIA_API_02]")
        
        # Confirmar transacciones de los SPs
        conn.commit()
        
        # Registrar éxito en la tabla de logs
        guardar_log_sql(cursor, "Ejecución de SPs", "EXITO", "Procesos completados correctamente.")
        print("¡Todos los procesos se completaron con éxito!")

    except pyodbc.Error as e:
        error_msg = f"Error SQL: {str(e)}"
        print(error_msg)
        # Si la conexión vive, intentamos registrar el error
        if conn:
            guardar_log_sql(conn.cursor(), "Ejecución de SPs", "ERROR", error_msg)
            
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        print(error_msg)
        if conn:
            guardar_log_sql(conn.cursor(), "Ejecución de SPs", "ERROR", error_msg)
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    ejecutar_procedimientos()