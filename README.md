# Biomedical Research AI - Motor de Hipótesis Terapéuticas

Sistema de inteligencia artificial para análisis de patógenos, identificación de dianas moleculares y generación de hipótesis de tratamiento terapéutico.

## Características (v2)

- **Cerebro de razonamiento simbólico** (`brain/`): grafo de conocimiento, motor de inferencia, puntuación de confianza, crítico (autoevaluación) y memoria de aprendizaje persistente.
- Análisis de patógenos y enfermedades (VIH, dengue, malaria, tuberculosis, COVID-19, influenza, hepatitis C, chikungunya, zika, MRSA, E. coli resistente)
- Identificación de dianas moleculares y proteínas objetivo
- Base de datos farmacológica con fármacos aprobados, en investigación y en reposicionamiento
- Motor de hipótesis híbrido: el cerebro simbólico razona sobre la base estructurada y la IA local (Ollama / LM Studio / OpenAI-compatible) amplía y redacta
- Interfaz web interactiva con tarjetas de hipótesis, barras de confianza, feedback y memoria
- Configuración vía variables de entorno (`.env.example`)
- Modo fallback sin IA local (razonamiento simbólico + base de conocimiento)

## Requisitos

- Python 3.10 o superior
- Ollama o LM Studio (para el motor de IA local)
- Navegador web moderno

## Instalación

1. Clona o descarga el proyecto.
2. Instala las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```
3. (Opcional) Instala Ollama desde [ollama.ai](https://ollama.ai) y descarga un modelo:
   ```bash
   ollama pull llama3
   ```

## Ejecución

### Opción A: Script automático (Windows)
Doble clic en `backend/run.bat`.

### Opción B: Manual
```bash
cd backend
python main.py
```

Luego abre `frontend/index.html` en tu navegador.

## Uso

1. **Analizar**: Escribe una consulta general (ej. "Analiza el virus del dengue serotipo 2 y sugiere posibles antivirales").
2. **Evaluar**: Evalúa un fármaco contra una diana específica (ej. fármaco "Lenacapavir", diana "Capsid_CA").
3. **Combinar**: Analiza combinaciones de fármacos (ej. "Lenacapavir, Dolutegravir" para "HIV").
4. **Comparar**: Compara alternativas terapéuticas por eficacia/seguridad/evidencia.

## API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/status` | GET | Estado del servicio, modelo activo y estadísticas del grafo/memoria |
| `/api/analyze` | POST | Análisis general (cerebro + IA) |
| `/api/evaluate` | POST | Evaluar fármaco vs diana |
| `/api/combinations` | POST | Combinaciones de fármacos |
| `/api/compare` | POST | Comparar alternativas |
| `/api/feedback` | POST | Registrar feedback (aprendizaje del cerebro) |
| `/api/memory` | GET | Estado de la memoria de aprendizaje |
| `/api/graph` | GET | Grafo de conocimiento (nodos y aristas) |
| `/api/pathogen/{key}/candidates` | GET | Candidatos del cerebro para un patógeno |
| `/api/knowledge/pathogens` | GET | Lista de patógenos |
| `/api/knowledge/targets` | GET | Lista de dianas |
| `/api/knowledge/drugs` | GET | Lista de fármacos |

## Estructura del proyecto

```
backend/
  main.py                 # API FastAPI (v2)
  config.py               # Configuración por entorno
  logging_config.py       # Logging estructurado
  utils.py                # Utilidades
  requirements.txt
  run.bat
  llm/
    base.py               # Interfaz de proveedor LLM
    ollama.py             # Proveedor Ollama
    openai_compat.py      # Proveedor OpenAI-compatible (LM Studio, etc.)
    manager.py            # Gestor con modelos de respaldo
  brain/                  # El "cerebro" de razonamiento
    knowledge_graph.py    # Grafo de conocimiento (patógeno-diana-fármaco)
    reasoning.py          # Motor de inferencia y generación de hipótesis
    scoring.py            # Puntuación de evidencia/confianza
    critic.py             # Autoevaluación y detección de contradicciones
    memory.py             # Memoria de aprendizaje persistente
    agent.py              # Orquestador del cerebro
  engine/
    analyzer.py           # Análisis de entidades sobre el grafo
    hypothesis.py         # Motor híbrido (cerebro + IA)
  knowledge/
    pathogens.json        # Base de datos de patógenos
    targets.json          # Base de datos de dianas moleculares
    drugs.json            # Base de datos farmacológica
  tests/
    test_brain.py         # Pruebas del cerebro
frontend/
  index.html
  styles.css
  app.js
```

## Limitaciones

- Las hipótesis generadas requieren validación experimental.
- No reemplaza criterio clínico ni aprobación regulatoria.
- La precisión depende de la calidad del modelo local y la base de conocimiento.

## Licencia

Uso investigativo y educativo.
