import streamlit as st
import tempfile
import json
import os
from PyPDF2 import PdfReader
import time
import requests
import fitz
import io
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# Función para inicializar claves en st.session_state
def initialize_votes_state(analysis_idx, paragraph_idx):
    key_vote = f"vote_{analysis_idx}_{paragraph_idx}"

    if key_vote not in st.session_state:
        st.session_state[key_vote] = None  # Ningún voto inicialmente

    return key_vote

# Transformar JSON
def transform_json(input_json, annotator_name):
    transformed_data = {
        "paper_title": input_json.get("paper_title", "Not available"),
        "DOI": input_json.get("DOI", "Not available"),
        "annotator_name": annotator_name,  # Registrar el nombre del votante solo una vez
        "generation_model": input_json.get("generation_model", "Not available"),
        "similarity_model": input_json.get("similarity_model", "Not available"),
        "similarity_metric": input_json.get("similarity_metric", "Not available"),
        "rag_type":input_json.get("rag_type", "Not available"),
        #"analysis": []
        "result": []
    }

    # Recorrer los resultados del análisis
    for result in input_json.get("result", []):
        question_category = result.get("question_category", "Unknown Category")
        query = result.get("query", "Not available")
        generation = result.get("generation", "Not available")
        RAG_source = result.get("RAG_source", "Not available")
        ground_truth = result.get("ground_truth", "Not available")
        selected_answer_dict = result.get("selected_answer", {})
        
        #Manejo de claves en `selected_answer` para buscar la respuesta
        selected_answer = "Not available"
        for key, value in selected_answer_dict.items():
            if question_category.replace(" ", "_").lower() in key.lower():
                selected_answer = f"{key}: {value.strip()}"
                break

        evidences = result.get("evidences", [])

        # Añadir la información procesada
        analysis_entry = {
            "question_category": question_category,
            "query": query,
            "generation": generation,
            "RAG_source": RAG_source,
            "ground_truth": ground_truth,
            "selected_answer": selected_answer,
            "evidences": []
        }

        for evidence_idx, evidence in enumerate(evidences):
            pdf_reference = evidence.get("pdf_reference", "Not available")
            generated_facts = evidence.get("generated_facts", "Not available")
            similarity_score = evidence.get("similarity_score", None)
            
            # Añadir evidencia al análisis con espacio para votos
            evidence_entry = {
                "pdf_reference": pdf_reference,
                "generated_facts": generated_facts,
                "similarity_score": similarity_score,
            }

            analysis_entry["evidences"].append(evidence_entry)

        #transformed_data["analysis"].append(analysis_entry)
        transformed_data["result"].append(analysis_entry)
        

    return transformed_data

# Página JSON
def json_page():
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 13, 1])
    with col2:
        #st.image("/Users/alexandrafaje/Desktop/Solar/solar_chem/logo_pg.png", width=600)
        st.image("images/logo_pg.png", width=600)

    # Agregar espacio antes del pie de página
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)   

    st.markdown("<h4 style='text-align: center;'>View the answers and evaluate them using our voting system.</h4>", unsafe_allow_html=True)

    # Agregar espacio antes del pie de página
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)   

    uploaded_json = st.file_uploader("Upload your JSON file please.", type="json")

    if uploaded_json is not None:
        try:
            json_content = json.load(uploaded_json)

            # Solicitar nombre del usuario
            st.markdown("### Please enter your name to continue:")
            annotator_name = st.text_input("Enter your name:")

            if annotator_name:
                st.success(f"Welcome, {annotator_name}! You can now cast your votes.")

                transformed_json = transform_json(json_content, annotator_name)

                # Información general del documento
                with st.expander("Paper Information"):
                    st.markdown(f"""
                        <h4 style='color:#333;'>TITLE:</h4>
                        <p style='font-size:16px; color:#555;'>{transformed_json['paper_title']}</p>
                        <h4 style='color:#333;'>DOI:</h4>
                        <p style='font-size:16px; color:#555;'>{transformed_json['DOI']}</p>
                        """, unsafe_allow_html=True)

                #if "analysis" in transformed_json:
                if "result" in transformed_json:    

                    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)  
                    st.subheader("Answers found in the PDF")
                    st.write("Below are the answers our system found in the input PDF. You will see the answers divided in 5 tables: catalyst, co-catalyst, light_source, lamp, reaction_medium, reactor_type and operation_mode. Each answer has the five most relevant paragraphs the system found in the paper. Please vote for each paragraph (up or down) whether the target text has the right answer for the corresponding category.")
                    #st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)  

                    for analysis_idx, analysis in enumerate(transformed_json["result"]):
                        # Mostrar categoría y tipo directamente con formato
                        category = analysis.get('question_category', 'Unknown Category').capitalize()
                        selected_answer = analysis.get('selected_answer', 'Not available')

                        st.markdown(
                            f"<p style='font-size:14px;'><strong>{category}:</strong> <span style='font-weight:normal;'>{selected_answer}</span></p>",
                            unsafe_allow_html=True
                        )

                        # Función de callback para actualizar el voto
                        def update_vote(key_vote, value):
                            st.session_state[key_vote] = value
                            
                        with st.expander("View Evidence Details"):
                            for evidence_idx, evidence in enumerate(analysis.get("evidences", [])):
                                pdf_reference = evidence.get("pdf_reference", "Not available")

                                key_vote = f"vote_{analysis_idx}_{evidence_idx}"
                                if key_vote not in st.session_state:
                                    st.session_state[key_vote] = None

                                col_pdf, col_votes = st.columns([3, 1])

                                with col_pdf:
                                    # Mostrar el contenido del PDF
                                    st.markdown(
                                        f"<div style='border: 1px solid #ddd; padding: 10px; margin-bottom: 15px; border-radius: 5px;'>"
                                        f"<p style='font-size:14px; line-height:1.6;'><strong>PDF Reference:</strong> {pdf_reference}</p>"
                                        f"</div>",
                                        unsafe_allow_html=True
                                    )

                                with col_votes:
                                    # Estado actual
                                    current_vote = st.session_state[key_vote]

                                    # Botón UPVOTE: callback con actualización inmediata
                                    if current_vote != "1":
                                        st.button("↑", key=f"upvote_{key_vote}", on_click=update_vote, args=(key_vote, "1"))
                                    else:
                                        st.success("↑")

                                    # Botón DOWNVOTE: callback con actualización inmediata
                                    if current_vote != "0":
                                        st.button("↓", key=f"downvote_{key_vote}", on_click=update_vote, args=(key_vote, "0"))
                                    else:
                                        st.error("↓")

                                # Guardar el voto
                                current_vote = st.session_state[key_vote]

                                # Asegurar que el voto es una cadena (0 o 1)
                                if current_vote is not None:
                                    current_vote = str(current_vote)  # Convertir a cadena para comparación

                                if current_vote in ["0", "1"]:  # Solo añadir si es 0 o 1
                                    evidence["vote"] = current_vote
                                elif "vote" in evidence:  # Eliminar campo 'vote' si existe pero no es válido
                                    del evidence["vote"]

                    # Descargar JSON actualizado
                    st.markdown("### Download Updated JSON")
                    updated_json_data = json.dumps(transformed_json, indent=4)
                    st.download_button(
                        label="Download JSON",
                        data=updated_json_data,
                        file_name=f"{annotator_name}_updated.json",
                        mime="application/json"
                    )
            else:
                st.warning("Please enter your name to enable voting.")
        except Exception as e:
            st.error(f"Error loading JSON file: {e}")


            
    # Agregar espacio antes del pie de página
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)    

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center;'>
        <a href="https://github.com/oeg-upm/solar-qa-ui" style="text-decoration: none;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg" alt="GitHub Logo" width="18" style="vertical-align: middle;"/>
        https://github.com/oeg-upm/solar-qa-ui
        </a> | CLI Version: 1 | © 2024 SolarChem
    </div>
    """, unsafe_allow_html=True)

    # Crear una columna para centrar la imagen
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    with col2:
        #st.image("/Users/alexandrafaje/Desktop/Solar/solar_chem/logo_uni.png", width=150)
        st.image("images/logo_uni.png", width=150)
        
        
        

# Cargamos el JSON automaticamente
def load_json_automatically(json_path):
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            query_data = json.load(f)
        #st.write("Archivo JSON cargado automáticamente.")
        return query_data
    else:
        st.error(f"JSON file not found in path: {json_path}")
        return None

# Pagina principal
def main_page():

    # Agregar espacio
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 13, 1])
    with col2:
        #st.image("/Users/alexandrafaje/Desktop/Solar/solar_chem/logo_pg.png", width=600)
        # st.image("images/logo_uni.png", width=150)
        st.image("images/logo_pg.png", width=600)

    # Agregar espacio
    st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)

    # Cargar archivo JSON de configuración
    json_path = "prompts.json"
    query_data = load_json_automatically(json_path)

    # Subir archivo PDF
    uploaded_pdf = st.file_uploader("Upload your scientific paper please", type=["pdf"])
    doi = st.text_input("DOI (Optional):")

    # Botón para enviar el archivo
    if uploaded_pdf and st.button("Submit"):
        with st.spinner("Analyzing your paper. Please be patient..."):
            try:
                args_dict = {
                    "llm_id": "llama3.1",
                    "embedding_id": "nomic-embed-text",
                    "input_file_path": uploaded_pdf.name,
                    "input_file_path": "/Users/alexandrafaje/Desktop/Solar/solar_chem/new_paper_1.pdf",
                    "prompt_file": "prompts.json",
                    "context_file_path": "context.json",
                    "rag_type": "fact"
                }

                # Llamada al backend
                response = requests.post("http://127.0.0.1:8000/analysis/", json=args_dict)

                # Validar respuesta
                if response.status_code == 200:
                    temp = response.json()

                    if doi:
                        temp["DOI"] = doi

                    result = temp.get("result", [])
                    generation_model = temp.get("generation_model", "Not available")

                    # Información general del documento
                    with st.expander("Paper Information"):
                        st.markdown(f"""
                            <h4 style='color:#333;'>TITLE:</h4>
                            <p style='font-size:16px; color:#555;'>{temp.get("paper_title", "No disponible")}</p>
                            <h4 style='color:#333;'>DOI:</h4>
                            <p style='font-size:16px; color:#555;'>{temp.get("DOI", "No disponible")}</p>
                            """, unsafe_allow_html=True)

                    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
                    st.subheader("Answers found in the PDF")
                    st.write("Below are the answers our system found in the input PDF. You will see the answers divided in 5 tables: catalyst, co-catalyst, light_source, lamp, reaction_medium, reactor_type and operation_mode. Each answer has the five most relevant paragraphs the system found in the paper. Please vote for each paragraph (up or down) whether the target text has the right answer for the corresponding category.")
                    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

                    # Mostrar resultados por categoría con evidencia y votación
                    for analysis_idx, analysis in enumerate(result):
                        category = analysis.get('question_category', 'Unknown Category')
                        selected_answer = analysis.get('selected_answer', {}).get(category, 'Not available')


                        st.markdown(
                            f"<p style='font-size:14px;'><strong>{category}:</strong> "
                            f"<span style='font-weight:normal;'>{selected_answer}</span></p>",
                            unsafe_allow_html=True
                        )

                        with st.expander("View Evidence Details"):
                            for evidence_idx, evidence in enumerate(analysis.get("evidences", [])):
                                pdf_reference = evidence.get("pdf_reference", "Not available")

                                st.markdown(
                                    f"<div style='border: 1px solid #ddd; padding: 10px; margin-bottom: 15px; "
                                    f"border-radius: 5px;'>"
                                    f"<p style='font-size:14px; line-height:1.6;'>"
                                    f"<strong>PDF Reference:</strong> {pdf_reference}</p>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                 )

                    # Descargar JSON actualizado
                    st.markdown("### Download Updated JSON")
                    updated_json_data = json.dumps(temp, indent=4)
                    st.download_button(
                        label="Download JSON",
                        data=updated_json_data,
                        file_name=f"analysis_updated.json",
                        mime="application/json"
                    )

                else:
                    st.error(f"Error en el servidor: {response.status_code}")
                    if response.text:
                        st.error(f"Detalles: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("Error: No se pudo conectar al servidor. Verifica que el backend está activo.")
            except json.JSONDecodeError:
                st.error("Error: El servidor devolvió una respuesta no válida.")
            except Exception as e:
                st.error(f"Error inesperado: {e}")




    # Agregar espacio antes del pie de página
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center;'>
        <a href="https://github.com/oeg-upm/solar-qa-ui" style="text-decoration: none;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg" alt="GitHub Logo" width="18" style="vertical-align: middle;"/>
        https://github.com/oeg-upm/solar-qa-ui
        </a> | CLI Version: 1 | © 2024 SolarChem
    </div>
    """, unsafe_allow_html=True)

    # Crear una columna para centrar la imagen
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    with col2:
        #st.image("/Users/alexandrafaje/Desktop/Solar/solar_chem/logo_uni.png", width=150)
        st.image("images/logo_uni.png", width=150)

# About page
def about_page():

    # Agregar espacio
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 13, 1])
    with col2:
        #st.image("/Users/alexandrafaje/Desktop/Solar/solar_chem/logo_pg.png", width=600)
        st.image("images/logo_pg.png", width=600)
    
    st.markdown("<h2 style='text-align: center;'>ABOUT</h2>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        """
        <div style="max-width: 800px; margin: 0 auto; padding: 50px 20px;">
            <p style="font-size: 1.2em; text-align: justify; line-height: 1.6;">
                Solarchem is an innovative platform designed to leverage artificial intelligence for the analysis of scientific papers in chemistry. 
                Our mission is to provide researchers, students, and professionals with an efficient way to extract key insights from academic documents 
                by automating the process of answering questions and highlighting relevant information.
            </p>
            <p style="font-size: 1.2em; text-align: justify; line-height: 1.6;">
                We use two advanced AI models based on Retrieval-Augmented Generation (RAG): a generation model and a similarity model. 
                These models process scientific PDFs, answering key questions about methodologies, findings, and more. 
                Each answer is linked to the specific paragraph in the document, ensuring accuracy and transparency. 
                Additionally, we provide a highlighted version of the PDF, marking relevant sections. Users can download this annotated PDF for future reference.
            </p>
            <h2 style="text-align: center; font-size: 2em; font-family: 'Arial', sans-serif; font-weight: bold;">How It Works</h2>
            <p style="font-size: 1.2em; text-align: justify; line-height: 1.6;">
                On our website, you first upload a PDF, which is processed using AI to generate key answers. 
                You will then receive evidence for these answers, with the option to download the PDF with the relevant sections highlighted or a JSON file containing the extracted data.
            </p>
            <p style="font-size: 1em; font-weight: bold;">
                Developed by: This website was carefully crafted by Alexandra Faje.
            </p>
            <p style="font-size: 1em; font-weight: bold;">
                Powered by: The platform is hosted and maintained by Clark Wang, Erick Cedeño, Ana Iglesias and Daniel Garijo, ensuring top-tier performance, security, and reliability.
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.markdown("---")

    st.markdown("""
    <div style='text-align: center;'>
        <a href="https://github.com/oeg-upm/solar-qa-ui" style="text-decoration: none;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg" alt="GitHub Logo" width="18" style="vertical-align: middle;"/>
        https://github.com/oeg-upm/solar-qa-ui
        </a> | CLI Version: 1 | © 2024 SolarChem
    </div>
    """, unsafe_allow_html=True)

    # Crear una columna para centrar la imagen
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    with col2:
        #st.image("/Users/alexandrafaje/Desktop/Solar/solar_chem/logo_uni.png", width=150)
        st.image("images/logo_uni.png", width=150)


# Función principal para gestionar las páginas
def main():
    if "page" not in st.session_state:
        st.session_state.page = "Home"

    # Barra de navegación con botones en línea
    col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
    with col2:
        if st.button("Home", key="home_button"):
            st.session_state.page = "Home"
    with col3:
        if st.button("JSON", key="json_button"):
            st.session_state.page = "Json"
    with col4:
        if st.button("About", key="about_button"):
            st.session_state.page = "About"

    # Cargar la página seleccionada
    if st.session_state.page == "Home":
        main_page()
    elif st.session_state.page == "About":
        about_page()
    elif st.session_state.page == "Json":
        json_page()

if __name__ == "__main__":
    main()
