import streamlit as st
import pandas as pd
import zipfile
import io

# Función para cargar el archivo de referencia
def cargar_archivo_referencia():
    uploaded_file = st.file_uploader("Carga el archivo de referencia (df_referencia)", type=["xlsx", "xls"])
    if uploaded_file:
        df_referencia = pd.read_excel(uploaded_file)
        return df_referencia
    return None

# Función para cargar el archivo del cliente
def cargar_archivo_cliente():
    uploaded_file = st.file_uploader("Carga el archivo del cliente (df_cliente)", type=["xlsx", "xls"])
    if uploaded_file:
        df_cliente = pd.read_excel(uploaded_file)
        return df_cliente
    return None

# Función para realizar el cruce y filtros
def realizar_cruce_filtros(df_referencia, df_cliente):
    # Cruce de datos por NIF
    df_recuento = pd.merge(df_cliente, df_referencia, how="left", left_on="NIF", right_on="NIF")

    # Agregar la columna de conteo de matriculaciones
    df_recuento["conteo de matriculaciones"] = df_recuento.groupby("NIF")["CURSO1"].transform("count")

    # Filtrar alumnos no aptos
    df_alumnos_no_matriculados = df_recuento[
        (df_recuento["conteo de matriculaciones"] > 3) |
        (df_recuento["CURSO"] == 1) |
        (~df_recuento["E-MAIL"].str.contains("@", na=False)) |
        (df_recuento["APELLIDO 1º"].isna()) |
        (df_recuento["TELÉFONO"].isna()) |
        (~df_recuento["CIF"].isin([
            "B62504105", "B96740659", "F20032553", "B48419378", "B01277268",
            "A78538774", "B43642222", "B55531495", "B20627196", "B09065236",
            "B81958134"
        ]))
    ]

    # Agregar columna de motivo de no matriculación
    condiciones = [
        df_recuento["conteo de matriculaciones"] > 3,
        df_recuento["CURSO"] == 1,
        ~df_recuento["E-MAIL"].str.contains("@", na=False),
        df_recuento["APELLIDO 1º"].isna(),
        df_recuento["TELÉFONO"].isna(),
        ~df_recuento["CIF"].isin([
            "B62504105", "B96740659", "F20032553", "B48419378", "B01277268",
            "A78538774", "B43642222", "B55531495", "B20627196", "B09065236",
            "B81958134"
        ])
    ]
    motivos = [
        "alumno matriculado más de 3 veces",
        "alumno apto",
        "correo incorrecto",
        "usuario debe tener por lo menos un apellido",
        "usuario debe tener por lo menos un teléfono",
        "CIF incorrecto"
    ]
    df_alumnos_no_matriculados["motivo"] = pd.Series(motivos).where(pd.Series(condiciones).any())

    # Filtrar los aptos
    df_alumnos_para_matricular = df_recuento[~df_recuento.index.isin(df_alumnos_no_matriculados.index)]

    # Copiar valores en columnas duplicadas de Teléfono y Email
    for columna in ["TELÉFONO", "E-MAIL"]:
        if df_alumnos_para_matricular[f"{columna} 1"].isna().any():
            df_alumnos_para_matricular[f"{columna} 1"].fillna(df_alumnos_para_matricular[columna], inplace=True)
        if df_alumnos_para_matricular[columna].isna().any():
            df_alumnos_para_matricular[columna].fillna(df_alumnos_para_matricular[f"{columna} 1"], inplace=True)

    return df_alumnos_para_matricular, df_alumnos_no_matriculados

# Función para dividir el dataframe en partes
def dividir_y_guardar(df, nombre_base, tamanio):
    buffers = []
    for i in range(0, len(df), tamanio):
        df_part = df.iloc[i:i + tamanio]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_part.to_excel(writer, index=False)
        buffers.append(buffer)
    return buffers

# Interfaz principal de la app
def main():
    st.title("App de Procesamiento de Datos")

    # Paso 1: Cargar archivos
    df_referencia = cargar_archivo_referencia()
    df_cliente = cargar_archivo_cliente()

    # Si se han cargado ambos archivos
    if df_referencia is not None and df_cliente is not None:
        # Realizar el cruce de datos y filtros
        df_para_matricular, df_no_matriculados = realizar_cruce_filtros(df_referencia, df_cliente)

        # Selección de tipo de formación
        tipo_formacion = st.selectbox("¿La formación es bonificada o privada?", ["Bonificada", "Privada"])

        # Tamaño por lote
        tamanio = 80 if tipo_formacion == "Bonificada" else 300

        # Dividir el dataframe para matricular
        buffers_para_matricular = dividir_y_guardar(df_para_matricular, "df_limpio", tamanio)
        buffers_no_matriculados = dividir_y_guardar(df_no_matriculados, "df_alumnos_no_matriculados", tamanio)

        # Crear archivo zip
        with io.BytesIO() as zip_buffer:
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for idx, buffer in enumerate(buffers_para_matricular):
                    zf.writestr(f"df_limpio_parte_{idx+1}.xlsx", buffer.getvalue())
                for idx, buffer in enumerate(buffers_no_matriculados):
                    zf.writestr(f"df_alumnos_no_matriculados_parte_{idx+1}.xlsx", buffer.getvalue())

            # Descargar archivo zip
            st.download_button(
                "Descargar archivos",
                zip_buffer.getvalue(),
                "resultados.zip",
                "application/zip"
            )

if __name__ == "__main__":
    main()
